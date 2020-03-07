# import numpy
import math

import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.core import name
from bmaya.core import mayanode



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
    
    startJoint = mayanode.Joint(startJoint)
    endJoint = mayanode.Joint(endJoint)
    
    jointVector = endJoint.vectorFromParent
    
    twistJoints = []
    
    for i in range(jointCount):
        cmds.select(clear=True)
        j = mayanode.Joint(name.findJointName(startJoint.shortName, identifier='Twist', count=i, suffix='JNT'))
        j.worldPosition = startJoint.worldPosition + ((jointVector * i) / float(jointCount - 1))
        j.parent = startJoint.name
        j.orient = [0,0,0]
        
        twistJoints.append(j)
    
    return twistJoints
