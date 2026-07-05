"""Purpose:
Utility functions for working with the DG in maya. These are used by various components to perform common
tasks on DG nodes, such as getting the nodes in the scene, listing attribute connections, getting and setting attributes, etc.
"""

import json
import maya.cmds as cmds
import maya.api.OpenMaya as om

METADATA_ATTR_NAME = 'BMETADATA'

def get_nodes_in_scene(ofType=None):
    return cmds.ls(type=ofType) if ofType is not None else cmds.ls()


def get_nodes_with_attribute(attribute_name, of_type=None):
    if of_type:
        return cmds.ls(f"*.{attribute_name}", type=of_type, objectsOnly=True)
    else:
        return cmds.ls(f"*.{attribute_name}", objectsOnly=True)


def get_mobject(node):
    """Get the MOBject for a given node.

    :return MOBject: The MOBject for the given node.
    """
    if isinstance(node, om.MObject):
        return node

    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDependNode(0)


def has_attribute(node, attribute_name):
    mobject = get_mobject(node)
    mfn = om.MFnDependencyNode(mobject)
    return mfn.hasAttribute(attribute_name)


def get_attribute_plug(node, attribute_name):
    mobject = get_mobject(node)

    mfn = om.MFnDependencyNode(mobject)

    if not mfn.hasAttribute(attribute_name):
        raise AttributeError(f"{node} does not have attribute {attribute_name}")

    plug = mfn.findPlug(attribute_name, True)
    return plug


def get_string_attribute(node, attribute_name):
    plug = get_attribute_plug(node, attribute_name)
    return plug.asString()


# TODO: attribute connections


def set_attr_locked(node, attrName, locked):
    cmds.setAttr(f"{node}.{attrName}", lock=locked)


def safe_add_attr(node, longName, **kwargs):
    if not has_attribute(node, longName):
        cmds.addAttr(node, longName=longName, **kwargs)

def safe_add_and_lock_attr(node, longName, **kwargs):
    safe_add_attr(node, longName, **kwargs)
    set_attr_locked(node, longName, True)

# Node metadata functions
def get_metadata(node):
    """Return a node's mdetadata as parsed json"""
    # TODO: this could be open maya for getting a string attr fast

    try:
        return json.loads(get_string_attribute(node, METADATA_ATTR_NAME))
    except json.JSONDecodeError as e:
        return dict()


def get_metadata_key(node, key):
    """Return the specific key from a node's json metadata"""
    assert isinstance(key, str)
    metadata = get_metadata(node)
    # Intentionally allow ourselves to raise a KeyError
    return metadata[key]
    

def set_metadata_key(node, key, value):
    """Set the value of a particular key in the node's json metadata"""
    # TODO: verify "value" is a basic type (no dictionaries, complex data types)
    assert isinstance(key, str)

    if not has_attribute(node, METADATA_ATTR_NAME):
        cmds.addAttr(node, longName=METADATA_ATTR_NAME, dataType='string')
        # Set attr default to a dictionary
        cmds.setAttr(f'{node}.{METADATA_ATTR_NAME}', json.dumps(dict()), type='string')
        metadata = dict()
    else:
        metadata = get_metadata(node)
        set_attr_locked(node, METADATA_ATTR_NAME, False)
    
    metadata[key] = value

    # TODO: we could use OpenMaya to quickly set a string attr here
    cmds.setAttr(f'{node}.{METADATA_ATTR_NAME}', json.dumps(metadata), type='string')
    set_attr_locked(node, METADATA_ATTR_NAME, True)

