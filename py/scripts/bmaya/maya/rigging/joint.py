"""Purpose:
Utility functions for working with joints in maya.
"""

import math
import maya.cmds as cmds
import maya.api.OpenMaya as om
from bmaya.core import constants, log
from bmaya.maya.util import nameUtils


def create_joint_at_selection_center():
    # Create joint at center
    cmds.select(cmds.polyListComponentConversion(toVertex=True))
    sel = cmds.ls(sl=1, flatten=1)
    sum_x = 0
    sum_y = 0
    sum_z = 0

    for vtx in sel:
        pos = cmds.xform(vtx, t=1, q=1, ws=1)
        sum_x += pos[0]
        sum_y += pos[1]
        sum_z += pos[2]

    center_x = sum_x / float(len(sel))
    center_y = sum_y / float(len(sel))
    center_z = sum_z / float(len(sel))
    jnt = cmds.joint()
    cmds.xform(jnt, t=[center_x, center_y, center_z], worldSpace=True)
    cmds.select(jnt)

    return jnt

"""
def best_fit_plane():
    centroid = get_selection_center()
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

    detX = yy * zz - yz * yz
    detY = xx * zz - xz * xz
    detZ = xx * yy - xy * xy

    detMax = max(detX, detY, detZ)

    if detMax <= 0.0:
        # points don't span a plane
        return None

    if detMax == detX:
        normal = om.MVector(detX, xz * yz - xy * zz, xy * yz - xz * yy)
    elif detMax == detY:
        normal = om.MVector(xz * yz - xy * zz, detY, xy * xz - yz * xx)
    elif detMax == detZ:
        normal = om.MVector(xy * yz - xz * yy, xy * xz - yz * xx, detZ)

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
    # use vector cross product to give us a 3rd axis that's perpendicular to
    # that space
    aimVectorW = (aimVectorU ^ aimVectorV).normal()

    # use vector corss product to give us an up vector that's orthogonal to U
    aimVectorV = aimVectorW ^ aimVectorU

    # get the quaternion for the movement from the given unit vector of the
    # down axis to the aim vector
    quaternion = om.MQuaternion(om.MVector(1, 0, 0), aimVectorU)

    # rotate the up axis by that quaternion
    upAxisRotated = om.MVector(0, 1, 0).rotateBy(quaternion)
    # find the angle between that rotated up axis and the current up axis
    angle = upAxisRotated.angle(aimVectorV)
    # get that as a quaternion
    quaternionV = om.MQuaternion(angle, aimVectorU)

    # make sure the angles are within a tolerance
    if not aimVectorV.isEquivalent(
            upAxisRotated.rotateBy(quaternionV), 1.0e-5):
        angle = (2 * math.pi) - angle
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
"""

# TODO: I don't know if this is a working util given the hardcoded
def add_twist_joints(start_joint, end_joint, joint_count=3):
    """Add twist joints as a child of the given joint.
    The child of the given joint will be used as the end joint to determine length.

    Args:
        start_joint (str): The joint to use as the start point.
        end_joint (str): The joint to use as the end point.
        joint_count (int): The number of twist joints to add.
        count=3 (int): The amount of twist joints to add

    Returns:
        (list): An array of Joint classes

    """

    start_joint_vector = om.MVector(
        *cmds.xform(
            "skel:shoulder_00_L_JNT", query=True, translation=True, worldSpace=True
        )
    )
    end_joint_vector = om.MVector(
        *cmds.xform(
            "skel:elbow_00_L_JNT", query=True, translation=True, worldSpace=True
        )
    )

    joint_vector = om.MVector(end_joint_vector - start_joint_vector)

    twist_joints = []

    for i in range(joint_count):
        cmds.select(clear=True)
        j = cmds.joint(
            nameUtils.find_joint_name(
                start_joint.shortName,
                identifier="Twist",
                count=i,
                suffix=constants.JOINT_SUFFIX,
            )
        )
        newPosition = start_joint_vector + ((joint_vector * i) / float(joint_count - 1))
        cmds.xform(j, translation=newPosition)
        cmds.parent(j, start_joint)

        twist_joints.append(j)

    return twist_joints


def orient_to_world(joints):

    worldLoc = cmds.group(empty=True, name="worldSpace")

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


def orient_to_mesh(joints, mesh):
    for jnt in joints:
        cmds.delete(
            cmds.normalConstraint(mesh, jnt, aimVector=[0, 0, 1], worldUpType="scene")
        )
        cmds.setAttr(jnt + ".rx", 0)
        cmds.setAttr(jnt + ".rz", 0)
        cmds.makeIdentity(jnt, apply=True, rotate=True)


def zero_transforms_ui():
    """Freezes translate, rotate and scale on the selection."""
    cmds.makeIdentity(apply=True, translate=True, rotate=True, scale=True)


def orient_to_world_ui():
    """Orients the selected joints to the world."""
    orient_to_world(cmds.ls(selection=True, type="joint"))


def orient_to_mesh_ui():
    """Orients the selected joints to the surface of the last selected object, a mesh."""
    selection = cmds.ls(selection=True)
    if len(selection) < 2:
        raise RuntimeError("Select the joints, then the mesh.")
    orient_to_mesh(selection[:-1], selection[-1])


def mirror_face_joints(joints):

    for jnt in joints:
        jnt_children = cmds.listRelatives(jnt, children=True)
        if not jnt_children:
            mirror = cmds.mirrorJoint(
                jnt, mirrorYZ=True, mirrorBehavior=True, searchReplace=["_L_", "_R_"]
            )
            cmds.xform(mirror, rotation=[180, 180, 0], objectSpace=True)
            cmds.makeIdentity(mirror, apply=True, rotate=True)
        else:
            mirror = cmds.mirrorJoint(
                jnt, mirrorYZ=True, mirrorBehavior=True, searchReplace=["_L_", "_R_"]
            )
            for mirror_jnt in mirror:
                mirror_children = cmds.listRelatives(mirror_jnt, children=True)
                if mirror_children:
                    cmds.parent(mirror_children, world=True)
                cmds.xform(mirror_jnt, rotation=[180, 180, 0], objectSpace=True)
                cmds.makeIdentity(mirror_jnt, apply=True, rotate=True)
                if mirror_children:
                    cmds.parent(mirror_children, mirror_jnt)


def size_joints():
    skeletonJoints = cmds.listRelatives(
        "SKELETON", type="joint", allDescendents=True, full_path=True
    )

    bindJoints = cmds.sets("BIND_set", query=True)

    for jnt in skeletonJoints:
        if jnt in bindJoints:
            if "hand" in jnt:
                cmds.setAttr(jnt + ".radius", 1)
            else:
                cmds.setAttr(jnt + ".radius", 3)
        else:
            cmds.setAttr(jnt + ".drawStyle", 0)

def label_joints():
    for jnt in cmds.ls(type="joint"):
        jntSplit = jnt.split("_")

        if "_M_" in jnt:
            cmds.setAttr(jnt + ".side", 0)
        if "_L_" in jnt:
            cmds.setAttr(jnt + ".side", 1)
        if "_R_" in jnt:
            cmds.setAttr(jnt + ".side", 2)

        cmds.setAttr(jnt + ".type", 18)

        try:
            cmds.setAttr(jnt + ".otherType", f'{jntSplit[0]}_{jntSplit[1]}', type="string")
        except IndexError:
            log.info(jnt + " may be named incorrectly.")
