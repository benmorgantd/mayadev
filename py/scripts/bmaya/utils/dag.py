import maya.cmds as cmds
import maya.OpenMaya as om

def fromString(obj):
    """Returns a dagPath to the given string representation of the object if it exists
    
    Args:
        obj (str): The object to return the dag path of
    Returns:
        (MDagPath)

    """

    assert isinstance(obj, basestring)

    if not cmds.objExists(obj):
        raise ValueError('Given object {} does not exist'.format(obj))

    # get the selected mesh and components
    sel = om.MSelectionList()
    sel.add(obj)
    dag = om.MDagPath()
    sel.getDagPath(0, dag)

    return dag