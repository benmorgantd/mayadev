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

def setupIkTwist(twistJoint=None, ikStartJoint=None, ikHandleParent=None, twistJointParent=None, name=None):
    """
    startJoint (str): Required for the scik method. This joint will be the base of or single chain IK system. 
    ikParent (str): Required for the scik method. The resulting IK handle will eventually be the child of this joint.
    * It's recommended that you don't use a "bind" joint for this. Try to keep your bind hierarchy clean :)

    twistJointParent (str): Required for the scik method. The parent joint of the base of the IK chain.

    mathUtils.setupIkTwist(twistJoint='leg_00_L_JNT', startJoint='leg_01_L_JNT', ikParent='pelvis_00_M_JNT', twistJointParent='leg_00_L_JNT', name='legTwist_L'
    """

    ikTwistStart = cmds.duplicate(twistJointParent, parentOnly=True, name=name + "_twist")[0]
    ikTwistEnd = cmds.duplicate(twistJointParent, parentOnly=True, name=name + "_twistEnd")[0]

    cmds.delete(cmds.parentConstraint(ikStartJoint, ikTwistStart, mo=0))
    cmds.parent(ikTwistEnd, ikTwistStart)

    ik = cmds.ikHandle(sj=ikTwistStart, ee=ikTwistEnd, solver="ikSCsolver", name=name + "_scikHandle")

    cmds.parent(ikTwistStart, twistJoint)

    ikGrp = cmds.group(empty=True, name=name + '_scikGrp')
    cmds.delete(cmds.pointConstraint(ik[0], ikGrp, mo=0))
    cmds.parent(ik[0], ikGrp)
    
    cmds.parentConstraint(ikHandleParent, ikGrp, mo=1)

    cmds.hide(ikTwistStart)

    return ikTwistStart, ikGrp

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


def fitCurveToPoints(points, name='fitCurve'):
    """[cmds.xform(jnt, q=1, t=1, ws=1) for jnt in joints]"""

    linearCurve = cmds.curve(degree=1, point=points)
    fitCurve = cmds.fitBspline(linearCurve, constructionHistory=False, tolerance=0.001,
                               name=name)[0]

    cmds.delete(linearCurve)

    return fitCurve

def getMatrixAlongCurve(curve, parameter, forwardVector=[0,0,1]):

    curveShape = cmds.listRelatives(curve, shapes=True)[0]
    curveInfo = cmds.createNode("pointOnCurveInfo")
    cmds.connectAttr(curveShape + ".worldSpace[0]", curveInfo + ".inputCurve")
    cmds.setAttr(curveInfo + ".turnOnPercentage", True)

    # build a matrix from the curve into node
    temp4x4 = cmds.createNode('fourByFourMatrix')
    cmds.connectAttr(curveInfo + '.position.positionX', temp4x4 + '.in30')
    cmds.connectAttr(curveInfo + '.position.positionY', temp4x4 + '.in31')
    cmds.connectAttr(curveInfo + '.position.positionZ', temp4x4 + '.in32')

    # align the down axis (x) to the tangent of the curve
    cmds.connectAttr(curveInfo + '.normalizedTangent.normalizedTangentX', temp4x4 + '.in00')
    cmds.connectAttr(curveInfo + '.normalizedTangent.normalizedTangentY', temp4x4 + '.in01')
    cmds.connectAttr(curveInfo + '.normalizedTangent.normalizedTangentZ', temp4x4 + '.in02')
    
    cmds.setAttr(curveInfo + ".parameter", parameter)

    forwardVector = om.MVector(forwardVector[0], forwardVector[1], forwardVector[2])

    U = om.MVector(*cmds.getAttr(curveInfo + '.normalizedTangent')[0])
    W = (U ^ forwardVector).normal()

    # like an up vector in an aim, the forward vector may not always be 
    # orthogonal to U (if the spline has any sort of curve to it)
    forwardVector = (W ^ U).normal()

    cmds.setAttr(temp4x4 + '.in10', forwardVector.x)
    cmds.setAttr(temp4x4 + '.in11', forwardVector.y)
    cmds.setAttr(temp4x4 + '.in12', forwardVector.z)

    cmds.setAttr(temp4x4 + '.in20', W.x)
    cmds.setAttr(temp4x4 + '.in21', W.y)
    cmds.setAttr(temp4x4 + '.in22', W.z)

    matrix = cmds.getAttr(temp4x4 + '.output')

    cmds.delete(temp4x4, curveInfo)

    return matrix
