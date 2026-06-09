import maya.api.OpenMaya as om
import maya.OpenMayaAnim as omAnim
import maya.OpenMayaMPx as omMPx
import maya.cmds as cmds
import time

kPluginCmdName = "extrudeWeights"


class ExtrudeWeights(omMPx.MPxCommand):
    def __init__(self):
        omMPx.MPxCommand.__init__(self)

        self.undo_data = None

    def isUndoable(self):
        """To make this command undoable, we need to override this function to return True"""

        return True

    def doIt(self, args):
        self.undo_data = self.redoIt()

    def redoIt(self):
        undo_data = self.extrude_weights()
        return undo_data

    def undoIt(self):
        # use the data from undo_data to set the old weights
        self.undo_data[0].setWeights(*self.undo_data[1:6])

    def find_skin_cluster(self, dag):
        """A convenience function for finding the skinCluster deforming a mesh.

        params:
          dag (MDagPath): A MDagPath for the mesh we want to investigate.
        """

        # gets the mesh's full name as a string
        mesh_name = dag.full_pathName()

        # useful one-liner for finding a skinCluster on a mesh
        skin_cluster = cmds.ls(cmds.listHistory(mesh_name), type="skinCluster")

        if len(skin_cluster) > 0:
            # get the MObject for that skinCluster node if there is one
            sel = om.MSelectionList()
            sel.add(skin_cluster[0])
            skin_cluster_obj = om.MObject()
            sel.getDependNode(0, skin_cluster_obj)

            return skin_cluster[0], skin_cluster_obj

        else:
            return None, None

    def extrude_weights(self):
        """
        Copies the weights for each selected vertex to the vertex closest in
        its inverse normal direction.

        Great for quickly fixing intersections on an thick mesh.

        """

        startTime = time.time()

        # get the selected mesh and components
        sel = om.MGlobal.getActiveSelectionList()

        verts = om.MObject()
        dag = om.MDagPath()
        sel.getDagPath(0, dag, verts)

        dag.extendToShape()

        if dag.apiType() != 296:
            om.MGlobal.displayError("Selection must be a polygon mesh.")
            return

        # get the skin cluster object
        skin_cluster, skin_cluster_obj = self.find_skin_cluster(dag)

        # make a mFnSkinCluster object
        if not skin_cluster_obj:
            om.MGlobal.displayError("Selected mesh has no skinCluster")
            return

        # normalizing the weights like this allows us to undo this function

        mFnSkinCluster = omAnim.MFnSkinCluster(skin_cluster_obj)
        inf_objects = om.MDagPathArray()
        # returns a list of the DagPaths of the joints affecting the mesh
        mFnSkinCluster.influenceObjects(inf_objects)
        inf_count = om.MScriptUtil(inf_objects.length())
        inf_count_int = inf_count.asInt()
        # c++ utility needed for the get/set weights functions
        inf_count_ptr = inf_count.asUintPtr()

        influence_indices = om.MIntArray()
        # create an MIntArray that just counts from 0 to inf_count
        for i in range(0, inf_count_int):
            influence_indices.append(i)

        old_weights = om.MDoubleArray()
        # don't use the verts MObject we made since we want to get the weights for each vertex
        # on this mesh, not just the selected one
        comps = om.MObject()
        mFnSkinCluster.getWeights(dag, comps, old_weights, inf_count_ptr)

        # new_weights just starts as a copy of old_weights
        new_weights = om.MDoubleArray(old_weights)

        # make a mFnMesh to allow us to use its intersect funtion
        fnMesh = om.MFnMesh(dag)
        # iterate over the selected verts
        itMesh = om.MItMeshVertex(dag, verts)

        while not itMesh.isDone():
            # get the normal for that vertex
            outer_vertex_normal = om.MVector()
            outer_vertex_index = itMesh.index()

            itMesh.getNormal(outer_vertex_normal, om.MSpace.kWorld)
            # get the closest vertex in the inverse normal direction
            # to do this we first need to cast a ray and find the closest face
            raySource = itMesh.position(om.MSpace.kWorld)
            # invert the vertex normal for our ray direction
            rayDirection = outer_vertex_normal * -1.0
            intersectionPoints = om.MPointArray()
            polygonIds = om.MIntArray()
            #  shoots a ray inwards  {<----}
            fnMesh.intersect(
                raySource,
                rayDirection,
                intersectionPoints,
                1.0e-10,
                om.MSpace.kWorld,
                polygonIds,
            )

            # get the verts on the intersected polygons and find the closest
            # one
            shortest_distance = float("inf")
            closest_vertex_id = 0
            # cast raySource (MPoint) as an MVector
            vert_vector = om.MVector(raySource)

            if polygonIds.length():
                for i in range(polygonIds.length()):
                    this_polygon_vert_ids = om.MIntArray()
                    # get the vertices on this polygon
                    fnMesh.getPolygonVertices(polygonIds[i], this_polygon_vert_ids)
                    # measure the distance
                    for j in range(this_polygon_vert_ids.length()):
                        if this_polygon_vert_ids[j] != outer_vertex_index:
                            vertex_point = om.MPoint()
                            # get this vert's position
                            fnMesh.getPoint(
                                this_polygon_vert_ids[j], vertex_point, om.MSpace.kWorld
                            )
                            # measure the distance between the parent vert and
                            # this vert
                            distance = (om.MVector(vertex_point) - vert_vector).length()

                            if distance < shortest_distance:
                                shortest_distance = distance
                                closest_vertex_id = this_polygon_vert_ids[j]

                # now that we have the closest vertex, we can transfer the weights for this vert
                # partition the weights for this vertex
                outer_vertex_weights = new_weights[
                    (outer_vertex_index * inf_count_int) : (
                        outer_vertex_index * inf_count_int
                    )
                    + inf_count_int
                ]
                # makes the weights for the closest vertex equal to the outer
                # vertex
                new_weights[
                    (closest_vertex_id * inf_count_int) : (
                        closest_vertex_id * inf_count_int
                    )
                    + inf_count_int
                ] = outer_vertex_weights

            itMesh.next()

        # set weights all at once
        mFnSkinCluster.setWeights(
            dag, comps, influence_indices, new_weights, False, old_weights
        )

        om.MGlobal.displayInfo(
            "Finished extruding skin weights in {0} milliseconds.".format(
                (time.time() - startTime) * 1000
            )
        )

        return [
            mFnSkinCluster,
            dag,
            comps,
            influence_indices,
            old_weights,
            False,
            old_weights,
        ]


##########################################################
# Plug-in initialization.
##########################################################


def cmdCreator():
    return omMPx.asMPxPtr(ExtrudeWeights())


def initializePlugin(mObject):
    fnPlugin = omMPx.MFnPlugin(mObject, "Ben Morgan", "1.0.0", "Any")
    try:
        fnPlugin.registerCommand(kPluginCmdName, cmdCreator)
    except BaseException:
        om.MGlobal.displayError("Failed to register command {0}".format(kPluginCmdName))


def uninitializePlugin(mObject):
    fnPlugin = omMPx.MFnPlugin(mObject)
    try:
        fnPlugin.deregisterCommand(kPluginCmdName)
    except BaseException:
        om.MGlobal.displayError(
            "Failed to deregister command {0}".format(kPluginCmdName)
        )
