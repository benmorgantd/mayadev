# bm_pruneSkinWeights
import maya.OpenMaya as om
import maya.OpenMayaAnim as omAnim
import maya.OpenMayaMPx as omMPx
import maya.cmds as cmds

kPluginCmdName = "pruneWeights"


class PruneWeights(omMPx.MPxCommand):
    def __init__(self):
        omMPx.MPxCommand.__init__(self)

        self.maxInfluence = 4

        self.undo_data = None

    def isUndoable(self):
        """To make this command undoable, we need to override this function to return True"""

        return True

    def doIt(self, args):
        self.undo_data = self.redoIt()

    def redoIt(self):
        undo_data = self.pruneSkinWeights(maxInfluence=self.maxInfluence)
        return undo_data

    def undoIt(self):
        # use the data from undo_data to set the old weights
        self.undo_data[0].setWeights(*self.undo_data[1:6])

    def pruneWeightList(self, weights, maxInfluence=4):
        """Prunes the given list to have only four non-zero values"""

        inf_count = len(weights)
        sorted_weights = list(weights)
        sorted_weights.sort(reverse=True)
        weight_index_pair = []

        pruned_weights = [0.0] * inf_count

        for i in range(inf_count):
            if i > (maxInfluence - 1):
                pruned_weights[weights.index(sorted_weights[i])] = 0.0
            else:
                pruned_weights[weights.index(
                    sorted_weights[i])] = sorted_weights[i]

        # normalize the list
        pruned_weights_sum = sum(pruned_weights)
        normalized_weights = [
            value / pruned_weights_sum for value in pruned_weights]

        return normalized_weights

    def getSkinCluster(self, dag):
        """A convenience function for finding the skinCluster deforming a mesh.

        params:
          dag (MDagPath): A MDagPath for the mesh we want to investigate.
        """

        # useful one-liner for finding a skinCluster on a mesh
        skin_cluster = cmds.ls(
            cmds.listHistory(
                dag.fullPathName()),
            type="skinCluster")

        if len(skin_cluster) > 0:
            # get the MObject for that skinCluster node if there is one
            sel = om.MSelectionList()
            sel.add(skin_cluster[0])
            skin_cluster_obj = om.MObject()
            sel.getDependNode(0, skin_cluster_obj)

            return skin_cluster[0], skin_cluster_obj

        else:
            raise RuntimeError("Selected mesh has no skinCluster")

    def pruneSkinWeights(self, maxInfluence=4):
        """Sets the weights for each vertex to the average of its neighbors."""

        original_sel = om.MSelectionList()
        om.MGlobal.getActiveSelectionList(original_sel)

        cmds.select(cmds.polyListComponentConversion(toVertex=True))

        # get the selected mesh and components
        sel = om.MSelectionList()
        om.MGlobal.getActiveSelectionList(sel)

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
        skin_cluster, skin_cluster_obj = self.getSkinCluster(dag)

        cmds.skinPercent(skin_cluster, pruneWeights=0.005)

        mFnSkinCluster = omAnim.MFnSkinCluster(skin_cluster_obj)
        inf_objects = om.MDagPathArray()
        # returns a list of the DagPaths of the joints affecting the mesh
        mFnSkinCluster.influenceObjects(inf_objects)
        inf_count_util = om.MScriptUtil(inf_objects.length())
        # c++ utility needed for the get/set weights functions
        inf_count_ptr = inf_count_util.asUintPtr()
        inf_count = inf_count_util.asInt()
        influence_indices = om.MIntArray()
        # create an MIntArray that just counts from 0 to inf_count
        for i in range(0, inf_count):
            influence_indices.append(i)

        old_weights = om.MDoubleArray()
        # don't use the verts MObject we made since we want to get the weights for each vertex
        # on this mesh, not just the selected one
        empty_object = om.MObject()
        mFnSkinCluster.getWeights(
            dag, empty_object, old_weights, inf_count_ptr)

        # new_weights just starts as a copy of old_weights
        new_weights = om.MDoubleArray(old_weights)

        # iterate over the selected verts
        itVerts = om.MItMeshVertex(dag, verts)

        while not itVerts.isDone():
            this_vert_weight_index = itVerts.index() * inf_count
            vert_weights = list(
                new_weights[this_vert_weight_index: this_vert_weight_index + inf_count])

            # makes the weights for the closest vertex equal to the outer
            # vertex
            new_weights[this_vert_weight_index: this_vert_weight_index +
                        inf_count] = self.pruneWeightList(vert_weights, maxInfluence)

            itVerts.next()

        # set weights all at once
        mFnSkinCluster.setWeights(
            dag,
            empty_object,
            influence_indices,
            new_weights,
            True,
            old_weights)

        om.MGlobal.setActiveSelectionList(original_sel)

        return [
            mFnSkinCluster,
            dag,
            empty_object,
            influence_indices,
            old_weights,
            False,
            old_weights]


##########################################################
# Plug-in initialization.
##########################################################

def cmdCreator():
    return omMPx.asMPxPtr(PruneWeights())


def initializePlugin(mObject):
    fnPlugin = omMPx.MFnPlugin(mObject, "Ben Morgan", "1.0.0", "Any")
    try:
        fnPlugin.registerCommand(kPluginCmdName, cmdCreator)
    except BaseException:
        om.MGlobal.displayError(
            "Failed to register command {0}".format(kPluginCmdName))


def uninitializePlugin(mObject):
    fnPlugin = omMPx.MFnPlugin(mObject)
    try:
        fnPlugin.deregisterCommand(kPluginCmdName)
    except BaseException:
        om.MGlobal.displayError(
            "Failed to deregister command {0}".format(kPluginCmdName))
