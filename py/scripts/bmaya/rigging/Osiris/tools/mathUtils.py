import maya.OpenMaya as om
import maya.cmds as cmds

import maya.OpenMaya as om


def findPoleVector(joints, scaleFactor=1):

    if len(joints) < 3:
        raise ValueError('Pass at least 3 joints to this function.')

    sel = om.MSelectionList()
    jointDags = om.MDagPathArray()

    for i in range(len(joints)):
        sel.add(joints[i])
        jointDag = om.MDagPath()
        sel.getDagPath(i, jointDag)
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
