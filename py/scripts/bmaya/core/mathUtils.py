import maya.OpenMaya as om

def getDistance(object1, object2):
    """Return the distance between two points"""

    sel = om.MSelectionList()
    sel.add(object1)
    sel.add(object2)
    
    dag1 = om.MDagPath()
    dag2 = om.MDagPath()
    
    sel.getDagPath(0, dag1)
    sel.getDagPath(1, dag2)
    
    fnTrans1 = om.MFnTransform(dag1)
    fnTrans2 = om.MFnTransform(dag2)
    
    position1 = fnTrans1.getTranslation(om.MSpace.kWorld)
    position2 = fnTrans2.getTranslation(om.MSpace.kWorld)
    
    distance = (position2 - position1).length()

    return distance

