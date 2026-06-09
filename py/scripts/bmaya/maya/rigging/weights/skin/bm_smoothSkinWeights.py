# bm_smoothSkinWeights
import maya.api.OpenMaya as om
import maya.OpenMayaAnim as omAnim
import maya.cmds as cmds


def getSkinCluster(dag):
    """A convenience function for finding the skinCluster deforming a mesh.

    params:
      dag (MDagPath): A MDagPath for the mesh we want to investigate.
    """

    # useful one-liner for finding a skinCluster on a mesh
    skin_cluster = cmds.ls(cmds.listHistory(dag.full_pathName()), type="skinCluster")

    if len(skin_cluster) > 0:
        # get the MObject for that skinCluster node if there is one
        sel = om.MSelectionList()
        sel.add(skin_cluster[0])
        skin_cluster_obj = om.MObject()
        sel.getDependNode(0, skin_cluster_obj)

        return skin_cluster[0], skin_cluster_obj

    else:
        raise RuntimeError("Selected mesh has no skinCluster")


def smoothSkinWeights():
    """
    Sets the weights for each vertex to the average of its neighbors.

    """

    original_sel = om.MGlobal.getActiveSelectionList()

    cmds.select(cmds.polyListComponentConversion(toVertex=True))

    # get the selected mesh and components
    sel = om.MGlobal.getActiveSelectionList()

    if not sel.length():
        return

    verts = om.MObject()
    dag = om.MDagPath()
    sel.getDagPath(0, dag, verts)

    dag.extendToShape()

    if dag.apiType() != 296:
        om.MGlobal.displayError("Selection must be a polygon mesh.")
        return

    # get the skin cluster object
    skin_cluster, skin_cluster_obj = getSkinCluster(dag)

    mFnSkinCluster = omAnim.MFnSkinCluster(skin_cluster_obj)
    inf_objects = om.MDagPathArray()
    # returns a list of the DagPaths of the joints affecting the mesh
    inf_count = mFnSkinCluster.influenceObjects(inf_objects)
    # c++ utility needed for the get/set weights functions
    inf_count_ptr = om.MScriptUtil(inf_count).asUintPtr()
    influence_indices = om.MIntArray()
    # create an MIntArray that just counts from 0 to inf_count
    for i in range(0, inf_count):
        influence_indices.append(i)

    old_weights = om.MDoubleArray()
    # don't use the verts MObject we made since we want to get the weights for each vertex
    # on this mesh, not just the selected one
    empty_object = om.MObject()
    mFnSkinCluster.getWeights(dag, empty_object, old_weights, inf_count_ptr)

    # new_weights just starts as a copy of old_weights
    new_weights = om.MDoubleArray(old_weights)

    # iterate over the selected verts
    itVerts = om.MItMeshVertex(dag, verts)

    while not itVerts.isDone():
        this_vert_weight_index = itVerts.index() * inf_count
        vert_weights = new_weights[
            this_vert_weight_index : this_vert_weight_index + inf_count
        ]

        # get this vert's neighbors and their weights
        vert_neighbors = om.MIntArray()
        itVerts.getConnectedVertices(vert_neighbors)
        neighbor_weights = []

        for i in range(vert_neighbors.length()):
            neighbor_vert_weight_index = vert_neighbors[i] * inf_count
            neighbor_weights.append(
                new_weights[
                    neighbor_vert_weight_index : neighbor_vert_weight_index + inf_count
                ]
            )

        # average_weights =
        # makes the weights for the closest vertex equal to the outer vertex
        # new_weights[this_vert_weight_index: this_vert_weight_index + inf_count] = average_weights

        itVerts.next()

    # set weights all at once
    # make a new empty object
    empty_object = om.MObject()
    mFnSkinCluster.setWeights(
        dag, empty_object, influence_indices, new_weights, False, old_weights
    )

    om.MGlobal.setActiveSelectionList(original_sel)
