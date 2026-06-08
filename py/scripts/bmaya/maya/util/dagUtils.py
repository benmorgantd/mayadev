"""Purpose:
Utility functions for working with the DAG in maya. These are used by various components to perform common
tasks on DAG nodes, such as getting children, parents, etc.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om


def get_children(dagNode, ofType=None, all_descendents=False):
    children = cmds.listRelatives(
        dagNode,
        children=True,
        allDescendents=all_descendents) or []
    if ofType:
        children = cmds.ls(children, type=ofType)
    return children


def get_all_children(dag_node, of_type=None):
    return get_children(dag_node, ofType=of_type, all_descendents=True)


def get_parent(dag_node, ofType=None):
    parent = cmds.listRelatives(dag_node, parent=True) or []
    if ofType and parent:
        parent = cmds.ls(parent, type=ofType)
    return parent[0] if parent else None


def get_dag_path(node):
    """Get the MDagPath for a given node.
    
    :return MDagPath: The MDagPath for the given node.
    """
    sel = om.MSelectionList()
    sel.add(node)
    # NOTE: this will raise a TypeError if the node is not a DAG node and a RuntimeError if the node doesn't exist
    return sel.getDagPath(0)