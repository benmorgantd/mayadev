import maya.OpenMaya as om
import math
import maya.cmds as cmds

# simple soft IK structure
def softIK():
    sel = om.MSelectionList()
    sel.add("joint1")
    sel.add("joint2")
    sel.add("joint3")
    sel.add("locator1")
    sel.add("locator2")

    j1Dag = om.MDagPath()
    j2Dag = om.MDagPath()
    j3Dag = om.MDagPath()
    locDag = om.MDagPath()
    loc2Dag = om.MDagPath()

    sel.getDagPath(0, j1Dag)
    sel.getDagPath(1, j2Dag)
    sel.getDagPath(2, j3Dag)
    sel.getDagPath(3, locDag)
    sel.getDagPath(4, loc2Dag)

    j1FnTrans = om.MFnTransform(j1Dag)
    j2FnTrans = om.MFnTransform(j2Dag)
    j3FnTrans = om.MFnTransform(j3Dag)
    locFnTrans = om.MFnTransform(locDag)
    loc2FnTrans = om.MFnTransform(loc2Dag)

    # first get our joint vectors
    v1 = j1FnTrans.getTranslation(om.MSpace.kWorld)
    v2 = j2FnTrans.getTranslation(om.MSpace.kWorld)
    v3 = j3FnTrans.getTranslation(om.MSpace.kWorld)
    l1 = locFnTrans.getTranslation(om.MSpace.kWorld)

    ab = (v2 - v1).length()
    bc = (v3 - v2).length()
    ac = (v3 - v1).length()
    al = (l1 - v1).length()

    maxDist = ab + bc
    softDist = .2
    softStart = ab + bc - softDist
    softEndFactor = 2.5
    softEnd = maxDist + softDist * softEndFactor

    if al < maxDist - softDist:
        # use law of cosines to find our two angles
        A = math.degrees(math.acos(((ab * ab) - (bc * bc) + (al * al)) / (-2 * (bc * al))))

        B = math.degrees(math.acos(((bc * bc) + (ab * ab) - (al * al)) / (-2 * (ab * bc))))

        # now choose our elbow side
        cmds.setAttr("joint1.ry", A + 180)
        cmds.setAttr("joint2.ry", B)



    elif al < softEnd:
        softFactor = al / softEnd
        al = softStart + softDist * softFactor
        A = math.degrees(math.acos(((ab * ab) - (bc * bc) + (al * al)) / (-2 * (bc * al))))

        B = math.degrees(math.acos(((bc * bc) + (ab * ab) - (al * al)) / (-2 * (ab * bc))))

        # now choose our elbow side
        cmds.setAttr("joint1.ry", A + 180)
        cmds.setAttr("joint2.ry", B)
    else:
        cmds.setAttr("joint1.ry", 0)
        cmds.setAttr("joint2.ry", 0)







