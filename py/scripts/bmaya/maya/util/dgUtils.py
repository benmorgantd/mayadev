"""Purpose:
Utility functions for working with the DG in maya. These are used by various components to perform common
tasks on DG nodes, such as getting the nodes in the scene, listing attribute connections, getting and setting attributes, etc.
"""
import maya.cmds as cmds


def getNodesInScene(ofType=None):
    return cmds.ls(type=ofType) if ofType is not None else cmds.ls()

# TODO: attribute connections
