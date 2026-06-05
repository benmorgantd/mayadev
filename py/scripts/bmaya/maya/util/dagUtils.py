"""Purpose:
Utility functions for working with the DAG in maya. These are used by various components to perform common 
tasks on DAG nodes, such as getting children, parents, etc.
"""

import maya.cmds as cmds


def getChildren(dagNode, ofType=None, allDescendents=False):
    children = cmds.listRelatives(dagNode, children=True, allDescendents=allDescendents) or []
    if ofType:
        children = cmds.ls(children, type=ofType)
    return children

def getAllChildren(dagNode, ofType=None):
    return getChildren(dagNode, ofType=ofType, allDescendents=True)

def getParent(dagNode, ofType=None):
    parent = cmds.listRelatives(dagNode, parent=True) or []
    if ofType and parent:
        parent = cmds.ls(parent, type=ofType)
    return parent[0] if parent else None
