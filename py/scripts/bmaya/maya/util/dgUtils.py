"""Purpose:
Utility functions for working with the DG in maya. These are used by various components to perform common
tasks on DG nodes, such as getting the nodes in the scene, listing attribute connections, getting and setting attributes, etc.
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om


def get_nodes_in_scene(ofType=None):
    return cmds.ls(type=ofType) if ofType is not None else cmds.ls()

# TODO: attribute connections

def get_mobject(node):
    """Get the MOBject for a given node.
    
    :return MOBject: The MOBject for the given node.
    """
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDependNode(0)