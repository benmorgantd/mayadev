"""Purpose:
Utility functions for working with the DG in maya. These are used by various components to perform common
tasks on DG nodes, such as getting the nodes in the scene, listing attribute connections, getting and setting attributes, etc.
"""

import json
import maya.cmds as cmds
import maya.api.OpenMaya as om

METADATA_ATTR_NAME = 'BMETADATA'
ALLOWED_METADATA_TYPES = (str, int, float)


def get_nodes_in_scene(ofType=None):
    """Returns full paths/names of all nodes matching the given MFn type."""
    # Default to kDependencyNode if no type is specified (matches all nodes)
    filter_type = getattr(om.MFn, ofType) if ofType else om.MFn.kDependencyNode
    
    nodes = []
    # Initialize the iterator with the specific MFn type filter
    it = om.MItDependencyNodes(filter_type)
    
    while not it.isDone():
        mobj = it.thisNode()
        
        # Check if it's a DAG node to get the full path, otherwise get the DG name
        if mobj.hasFn(om.MFn.kDagNode):
            dag_fn = om.MDagPath.getAPathTo(mobj)
            nodes.append(dag_fn.fullPathName())
        else:
            dg_fn = om.MFnDependencyNode(mobj)
            nodes.append(dg_fn.name())
            
        it.next()
        
    return nodes


def get_nodes_with_attribute(attribute_name, of_type=None):
    """Returns full paths/names of nodes that possess the specified attribute."""
    filter_type = getattr(om.MFn, of_type) if of_type else om.MFn.kDependencyNode
    
    nodes = []
    it = om.MItDependencyNodes(filter_type)
    
    while not it.isDone():
        mobj = it.thisNode()
        dg_fn = om.MFnDependencyNode(mobj)
        
        # OpenMaya attribute lookup is significantly faster than string checks
        if dg_fn.hasAttribute(attribute_name):
            if mobj.hasFn(om.MFn.kDagNode):
                dag_fn = om.MDagPath.getAPathTo(mobj)
                nodes.append(dag_fn.fullPathName())
            else:
                nodes.append(dg_fn.name())
                
        it.next()
        
    return nodes


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


def get_metadata_value(node, key):
    """Return the specific key from a node's json metadata"""
    metadata = get_metadata(node)
    # Intentionally allow ourselves to raise a KeyError
    return metadata[key]

def has_metadata_key(node, key):
    metadata = get_metadata(node)
    return key in metadata

def set_metadata_value(node, key, value):
    """Set the value of a particular key in the node's json metadata"""
    assert isinstance(key, str)
    assert isinstance(value, ALLOWED_METADATA_TYPES)

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

def get_nodes_with_metadata():
    return get_nodes_with_attribute(METADATA_ATTR_NAME)

def get_nodes_with_metadata_key(key):
    nodes = []

    for node in get_nodes_with_metadata():
        if has_metadata_key(node, key):
            nodes.append(node)

    return nodes

def get_nodes_with_metadata_value(key, value):
    """Returns the node in the scene with """

    nodes = []
    for node in get_nodes_with_metadata():
        # We don't ask for nodes with this key because that would require us to read the attribute twice.
        # Just querying for the attribute's existence is fast, and trying the value query and catching the KeyError is fast.
        try:
            result = get_metadata_value(node, key)
            if result == value:
                nodes.append(node)
        except KeyError:
            pass

    return nodes

def get_nodes_with_metadata_values(keyvalue_dict):
    """Returns nodes that contain all the provided key-value pairs."""
    nodes = []

    for node in get_nodes_with_metadata():
        for key, value in keyvalue_dict.items():
            try:
                # Query the value directly on the current node
                if get_metadata_value(node, key) != value:
                    break  # Value mismatch, skip to the next node
            except KeyError:
                break  # Key missing entirely, skip to the next node
        else:
            # The 'else' block only executes if the inner loop finishes without breaking.
            # This means all keys were present and all values matched.
            nodes.append(node)
            
    return nodes