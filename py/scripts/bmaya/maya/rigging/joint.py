"""Purpose:
Utility functions for working with joints in maya.
"""

import math

import maya.cmds as cmds
import maya.OpenMaya as om
from bmaya3.core.util import constants
from bmaya3.maya.util import nameUtils


def getSelectionCenter():
    cmds.select(cmds.polyListComponentConversion(toVertex=True))

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    dag = om.MDagPath()
    components = om.MObject()

    sel.getDagPath(0, dag, components)

    itVerts = om.MItMeshVertex(dag, components)

    vectors = om.MVectorArray()
    vectorSum = om.MVector(0.0, 0.0, 0.0)

    while not itVerts.isDone():
        # get world space position of each selected vertex
        currentPoint = itVerts.position(om.MSpace.kWorld)

        currentVector = om.MVector(currentPoint.x, currentPoint.y, currentPoint.z)
        vectorSum += currentVector
        vectors.append(currentVector)

        itVerts.next()    

    centroid = vectorSum / float(vectors.length())

    return centroid

def bestFitPlane():
    centroid = getSelectionCenter()
    loc = cmds.spaceLocator()[0]
    cmds.xform(loc, t=[centroid.x, centroid.y, centroid.z], ws=1)

    # # calculate a covariance matrix
    xx = 0.0
    xy = 0.0
    xz = 0.0

    yx = 0.0
    yy = 0.0
    yz = 0.0

    zx = 0.0
    zy = 0.0
    zz = 0.0

    # A = []

    for i in range(0, int(numVectors)):
        r = vectors[i] - centroid

        xx += r.x * r.x
        xy += r.x * r.y
        xz += r.x * r.z

        yx += r.y * r.x
        yy += r.y * r.y
        yz += r.y * r.z

        zx += r.z * r.x
        zy += r.z * r.y
        zz += r.z * r.z

    xx /= numVectors
    xy /= numVectors
    xz /= numVectors

    yx /= numVectors
    yy /= numVectors
    yz /= numVectors

    zx /= numVectors
    zy /= numVectors
    zz /= numVectors

    detX = yy*zz - yz*yz
    detY = xx*zz - xz*xz
    detZ = xx*yy - xy*xy

    detMax = max(detX, detY, detZ)

    if detMax <= 0.0:
        # points don't span a plane
        return None

    if detMax == detX:
        normal = om.MVector(detX, xz*yz - xy*zz, xy*yz - xz*yy)
    elif detMax == detY:
        normal = om.MVector(xz*yz - xy*zz, detY, xy*xz - yz*xx)
    elif detMax == detZ:
        normal = om.MVector(xy*yz - xz*yy, xy*xz - yz*xx, detZ)
    
    normal = normal.normal()

    aimVector = normal + centroid

    # create a second locator and aim at it
    aimLoc = cmds.spaceLocator()[0]
    cmds.xform(aimLoc, t=[aimVector.x, aimVector.y, aimVector.z], ws=True)

    # find the vector from the object to the aimObject
    aimVector = (aimVector - centroid)
    # find the vector from the object to the upObject
    upVector = (om.MVector(0, 1, 0) + centroid).normal()

    aimVectorU = aimVector.normal()
    # just use the up vector for now
    aimVectorV = upVector
    # use vector cross product to give us a 3rd axis that's perpendicular to that space
    aimVectorW = (aimVectorU ^ aimVectorV).normal()

    # use vector corss product to give us an up vector that's orthogonal to U
    aimVectorV = aimVectorW ^ aimVectorU

    # get the quaternion for the movement from the given unit vector of the down axis to the aim vector
    quaternion = om.MQuaternion(om.MVector(1, 0, 0), aimVectorU)

    # rotate the up axis by that quaternion
    upAxisRotated = om.MVector(0,1,0).rotateBy(quaternion)
    # find the angle between that rotated up axis and the current up axis
    angle = upAxisRotated.angle(aimVectorV)
    # get that as a quaternion
    quaternionV = om.MQuaternion(angle, aimVectorU)

    # make sure the angles are within a tolerance
    if not aimVectorV.isEquivalent(upAxisRotated.rotateBy(quaternionV), 1.0e-5):
      angle = (2*math.pi) - angle
      quaternionV = om.MQuaternion(angle, aimVectorU)

    # adds that new movement to the quaternion
    quaternion *= quaternionV

    # make a fnTransform from our locator
    sel = om.MSelectionList()
    sel.add(loc)
    dag = om.MDagPath()
    sel.getDagPath(0, dag)
    fnTrans = om.MFnTransform(dag)
    fnTrans.rotateBy(quaternion, om.MSpace.kWorld)

    cmds.delete(aimLoc)

def addTwistJoints(startJoint, endJoint, jointCount=3):
    """Add twist joints as a child of the given joint.
    The child of the given joint will be used as the end joint to determine length.
    
    Args:
        jnt (str): The joint start joint to use.
        count=3 (int): The amount of twist joints to add
        
    Returns:
        (list): An array of Joint classes
        
    """

    startJointVector = om.MVector(*cmds.xform('skel:shoulder_00_L_JNT', query=True, translation=True, worldSpace=True))
    endJointVector = om.MVector(*cmds.xform('skel:elbow_00_L_JNT', query=True, translation=True, worldSpace=True))

    jointVector = om.MVector(endJointVector - startJointVector)

    twistJoints = []

    for i in range(jointCount):
        cmds.select(clear=True)
        j = cmds.joint(nameUtils.findJointName(startJoint.shortName, identifier='Twist', count=i, suffix=constants.JOINT_SUFFIX))
        newPosition = startJointVector + ((jointVector * i) / float(jointCount - 1))
        cmds.xform(j, translation=newPosition)
        cmds.parent(j, startJoint)

        twistJoints.append(j)
    
    return twistJoints

def orientToWorld(joints):

    worldLoc = cmds.group(empty=True, name='worldSpace')


    # orient joints to world
    for jnt in joints:
        children = cmds.listRelatives(jnt, children=True)

        if children:
            cmds.parent(children, world=True)

        cmds.delete(cmds.orientConstraint(worldLoc, jnt, maintainOffset=False))

        cmds.makeIdentity(jnt, apply=True, rotate=True)

        if children:
            cmds.parent(children, jnt, absolute=True)
        
    cmds.delete(worldLoc)


def orientToMesh(joints, mesh):
    for jnt in joints:
        cmds.delete(cmds.normalConstraint(mesh, jnt, aimVector=[0,0,1], worldUpType='scene'))
        cmds.setAttr(jnt + '.rx', 0)
        cmds.setAttr(jnt + '.rz', 0)
        cmds.makeIdentity(jnt, apply=True, rotate=True)


def mirrorFaceJoints(joints):

    for jnt in joints:
        jntChildren = cmds.listRelatives(jnt, children=True)
        if not jntChildren:
            mirror = cmds.mirrorJoint(jnt, mirrorYZ=True, mirrorBehavior=True,
                                       searchReplace=['_L_', '_R_'])
            cmds.xform(mirror, rotation=[180,180,0], objectSpace=True)
            cmds.makeIdentity(mirror, apply=True, rotate=True)
        else:
            mirror = cmds.mirrorJoint(jnt, mirrorYZ=True, mirrorBehavior=True,
                                      searchReplace=['_L_', '_R_'])
            for mirrorJnt in mirror:
                mirrorChildren = cmds.listRelatives(mirrorJnt, children=True)
                if mirrorChildren:
                    cmds.parent(mirrorChildren, world=True)
                cmds.xform(mirrorJnt, rotation=[180, 180, 0], objectSpace=True)
                cmds.makeIdentity(mirrorJnt, apply=True, rotate=True)
                if mirrorChildren:
                    cmds.parent(mirrorChildren, mirrorJnt)
