import maya.OpenMaya as om
import maya.cmds as cmds

import maya.OpenMaya as om


def findPoleVector(joints, scaleFactor=1):

    if len(joints) < 3:
        raise ValueError('Pass at least 3 joints to this function.')

    obj = om.MSelectionList()
    jointDags = om.MDagPathArray()

    for i in range(len(joints)):
        obj.add(joints[i])
        jointDag = om.MDagPath()
        obj.getDagPath(i, jointDag)
        jointDags.append(jointDag)

    startJointFnTrans = om.MFnTransform(jointDags[0])
    secondJointFnTrans = om.MFnTransform(jointDags[1])
    endJointFnTrans = om.MFnTransform(jointDags[2])

    startJointVec = startJointFnTrans.getTranslation(om.MSpace.kWorld)
    secondJointVec = secondJointFnTrans.getTranslation(om.MSpace.kWorld)
    endJointVec = endJointFnTrans.getTranslation(om.MSpace.kWorld)

    # A - B gives us the vector from B to A
    startEndVec = endJointVec - startJointVec
    startSecondVec = secondJointVec - startJointVec

    # project the startSecondVec onto the line made by startEndVec
    projection = startEndVec * ((startSecondVec * startEndVec) / (startEndVec * startEndVec))
    affineProjection = projection + startJointVec

    projectionThroughMidJoint = (secondJointVec - affineProjection)
    # multiply by ((up_to_mid_vec.length() / projectionThroughMidJoint)
    scaleProjectionThroughMidJoint = projectionThroughMidJoint * (
        startSecondVec.length() / projectionThroughMidJoint.length()) * scaleFactor

    poleVectorLocation = (affineProjection + scaleProjectionThroughMidJoint)

    return [poleVectorLocation.x, poleVectorLocation.y, poleVectorLocation.z]

def setupIkTwist(twistJoint=None, startJoint=None, ikParent=None, twistJointParent=None, name=None):
    dup1 = cmds.duplicate(twistJointParent, parentOnly=True, name=name + "_twist")[0]
    dup2 = cmds.duplicate(twistJointParent, parentOnly=True, name=name + "_twistEnd")[0]

    cmds.delete(cmds.parentConstraint(startJoint, dup1, mo=0))
    cmds.parent(dup2, dup1)

    ik = cmds.ikHandle(sj=dup1, ee=dup2, solver="ikSCsolver", name=name + "_scikHandle")

    cmds.parent(dup1, twistJoint)
    
    if ikParent:
        cmds.parent(ik[0], ikParent)

    cmds.hide(ik[0])
    cmds.hide(dup1)

    return [dup1, ik]

def setupQuatTwist(obj=None, twistAxis="X"):
    # quat twistExtractor
    if not obj:
        try:
            obj = cmds.ls(sl=1)[0]
        except IndexError:
            raise IndexError("No object objected.")

    twistAxis = twistAxis.upper()
    
    if twistAxis not in ['X', 'Y', 'Z']:
        raise ValueError('Given twist axis is invalid')
    
    mm = cmds.createNode("multMatrix", n=obj.rstrip("_jj") + "_multMatrix")
    cmds.connectAttr(obj + ".worldMatrix[0]", mm + ".matrixIn[0]")
    cmds.connectAttr(obj + ".parentInverseMatrix[0]", mm + ".matrixIn[1]")

    decomp = cmds.createNode("decomposeMatrix", n=obj.rstrip("_jj") + "_decompMatrix")
    cmds.connectAttr(mm + ".matrixSum", decomp + ".inputMatrix")

    quatToEuler = cmds.createNode("quatToEuler", n=obj.rstrip("_jj") + "_quatToEuler")
    cmds.connectAttr("{0}.outputQuat{1}".format(decomp, twistAxis), "{0}.inputQuat{1}".format(quatToEuler, twistAxis))
    cmds.connectAttr(decomp + ".outputQuatW", quatToEuler + ".inputQuatW")
    cmds.connectAttr(obj + ".rotateOrder", quatToEuler + ".inputRotateOrder")

    return quatToEuler
