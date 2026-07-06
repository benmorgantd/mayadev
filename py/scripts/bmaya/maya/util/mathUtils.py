"""Purpose:
Utility functions for working with math in maya. These are used by various components to perform common
tasks that involve math, such as finding the pole vector position for an ik handle, etc.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds


def find_pole_vector(joints, scaleFactor=1):
    if len(joints) < 3:
        raise ValueError("Pass at least 3 joints to this function.")

    obj = om.MSelectionList()
    jointDags = om.MDagPathArray()

    for i in range(len(joints)):
        obj.add(joints[i])
        jointDag = om.MDagPath()
        obj.getDagPath(i, jointDag)
        jointDags.append(jointDag)

    start_jointFnTrans = om.MFnTransform(jointDags[0])
    secondJointFnTrans = om.MFnTransform(jointDags[1])
    endJointFnTrans = om.MFnTransform(jointDags[2])

    start_jointVec = start_jointFnTrans.getTranslation(om.MSpace.kWorld)
    secondJointVec = secondJointFnTrans.getTranslation(om.MSpace.kWorld)
    endJointVec = endJointFnTrans.getTranslation(om.MSpace.kWorld)

    # A - B gives us the vector from B to A
    startEndVec = endJointVec - start_jointVec
    startSecondVec = secondJointVec - start_jointVec

    # project the startSecondVec onto the line made by startEndVec
    projection = startEndVec * (
        (startSecondVec * startEndVec) / (startEndVec * startEndVec)
    )
    affineProjection = projection + start_jointVec

    projectionThroughMidJoint = secondJointVec - affineProjection
    # multiply by ((up_to_mid_vec.length() / projectionThroughMidJoint)
    scaleProjectionThroughMidJoint = (
        projectionThroughMidJoint
        * (startSecondVec.length() / projectionThroughMidJoint.length())
        * scaleFactor
    )

    poleVectorLocation = affineProjection + scaleProjectionThroughMidJoint

    return [poleVectorLocation.x, poleVectorLocation.y, poleVectorLocation.z]


def setup_ik_twist(
    twist_joint=None,
    ik_start_joint=None,
    ik_handle_parent=None,
    twist_joint_parent=None,
    name=None,
):
    """
    start_joint (str): Required for the scik method. This joint will be the base of or single chain IK system.
    ikParent (str): Required for the scik method. The resulting IK handle will eventually be the child of this joint.
    * It's recommended that you don't use a "bind" joint for this. Try to keep your bind hierarchy clean :)

    twistJointParent (str): Required for the scik method. The parent joint of the base of the IK chain.

    mathUtils.setupIkTwist(twistJoint='leg_00_L_JNT', start_joint='leg_01_L_JNT', ikParent='pelvis_00_M_JNT', twistJointParent='leg_00_L_JNT', name='legTwist_L'
    """

    ik_twist_start = cmds.duplicate(
        twist_joint_parent, parentOnly=True, name=name + "_twist"
    )[0]
    ik_twist_end = cmds.duplicate(
        twist_joint_parent, parentOnly=True, name=name + "_twistEnd"
    )[0]

    match_transforms(ik_start_joint, ik_twist_start)
    cmds.parent(ik_twist_end, ik_twist_start)

    ik = cmds.ikHandle(
        sj=ik_twist_start,
        ee=ik_twist_end,
        solver="ikSCsolver",
        name=name + "_scikHandle",
    )

    cmds.parent(ik_twist_start, twist_joint)

    ikGrp = cmds.group(empty=True, name=name + "_scikGrp")
    cmds.delete(cmds.pointConstraint(ik[0], ikGrp, mo=0))
    cmds.parent(ik[0], ikGrp)

    cmds.parentConstraint(ik_handle_parent, ikGrp, mo=1)

    cmds.hide(ik_twist_start)

    return ik_twist_start, ikGrp


def setup_quat_twist(obj=None, twistAxis="X"):
    # quat twistExtractor
    if not obj:
        try:
            obj = cmds.ls(sl=1)[0]
        except IndexError:
            raise IndexError("No object objected.")

    twistAxis = twistAxis.upper()

    if twistAxis not in ["X", "Y", "Z"]:
        raise ValueError("Given twist axis is invalid")

    mm = cmds.createNode("multMatrix", n=obj.rstrip("_jj") + "_multMatrix")
    cmds.connectAttr(obj + ".worldMatrix[0]", mm + ".matrixIn[0]")
    cmds.connectAttr(obj + ".parentInverseMatrix[0]", mm + ".matrixIn[1]")

    decomp = cmds.createNode("decomposeMatrix", n=obj.rstrip("_jj") + "_decompMatrix")
    cmds.connectAttr(mm + ".matrixSum", decomp + ".inputMatrix")

    quatToEuler = cmds.createNode("quatToEuler", n=obj.rstrip("_jj") + "_quatToEuler")
    cmds.connectAttr(
        "{0}.outputQuat{1}".format(decomp, twistAxis),
        "{0}.inputQuat{1}".format(quatToEuler, twistAxis),
    )
    cmds.connectAttr(decomp + ".outputQuatW", quatToEuler + ".inputQuatW")
    cmds.connectAttr(obj + ".rotateOrder", quatToEuler + ".inputRotateOrder")

    return quatToEuler


def fit_curve_to_points(points, name="fitCurve"):
    """[cmds.xform(jnt, q=1, t=1, ws=1) for jnt in joints]"""

    linearCurve = cmds.curve(degree=1, point=points)
    fitCurve = cmds.fitBspline(
        linearCurve, constructionHistory=False, tolerance=0.001, name=name
    )[0]

    cmds.delete(linearCurve)

    return fitCurve


def get_matrix_along_curve(curve, parameter, downAxis="X"):
    curveShape = cmds.listRelatives(curve, shapes=True)[0]
    curveInfo = cmds.createNode("pointOnCurveInfo")
    cmds.connectAttr(curveShape + ".worldSpace[0]", curveInfo + ".inputCurve")
    cmds.setAttr(curveInfo + ".turnOnPercentage", True)

    # build a matrix from the curve into node
    temp4x4 = cmds.createNode("fourByFourMatrix")
    cmds.connectAttr(curveInfo + ".position.positionX", temp4x4 + ".in30")
    cmds.connectAttr(curveInfo + ".position.positionY", temp4x4 + ".in31")
    cmds.connectAttr(curveInfo + ".position.positionZ", temp4x4 + ".in32")

    # align the down axis (x) to the tangent of the curve
    cmds.connectAttr(
        curveInfo + ".normalizedTangent.normalizedTangentX", temp4x4 + ".in00"
    )
    cmds.connectAttr(
        curveInfo + ".normalizedTangent.normalizedTangentY", temp4x4 + ".in01"
    )
    cmds.connectAttr(
        curveInfo + ".normalizedTangent.normalizedTangentZ", temp4x4 + ".in02"
    )

    cmds.setAttr(curveInfo + ".parameter", parameter)

    forwardVector = om.MVector(0, 0, 1)

    U = om.MVector(*cmds.getAttr(curveInfo + ".normalizedTangent")[0])
    W = (U ^ forwardVector).normal()

    # like an up vector in an aim, the forward vector may not always be
    # orthogonal to U (if the spline has any sort of curve to it)
    forwardVector = (W ^ U).normal()

    cmds.setAttr(temp4x4 + ".in10", forwardVector.x)
    cmds.setAttr(temp4x4 + ".in11", forwardVector.y)
    cmds.setAttr(temp4x4 + ".in12", forwardVector.z)

    cmds.setAttr(temp4x4 + ".in20", W.x)
    cmds.setAttr(temp4x4 + ".in21", W.y)
    cmds.setAttr(temp4x4 + ".in22", W.z)

    matrix = cmds.getAttr(temp4x4 + ".output")

    cmds.delete(temp4x4, curveInfo)

    if downAxis == "Y":
        matrix = reorder_matrix(get_mmatrix_from_list(matrix), downAxis=1, upAxis=2)
        matrix = list_from_matrix(matrix)

    return matrix


def match_transforms(source, targets, translate=True, rotate=True, scale=True):
    if isinstance(targets, str):
        targets = [targets]

    for target in targets:
        cmds.delete(cmds.parentConstraint(source, target, maintainOffset=False))


def get_mmatrix_from_list(matrixList):
    return om.MMatrix(matrixList)


def reorder_matrix(matrix, downAxis=0, upAxis=0):
    baseMatrix = matrix

    # for negative down axis, rotate 180y before reordering rows
    if downAxis in [3, 4, 5]:
        downAxis -= 3
        r180y = [-1.0, 0.0, 0.0, 0.0, 
                  0.0, 1.0, 0.0, 0.0, 
                  0.0, 0.0, -1.0, 0.0, 
                  0.0, 0.0, 0.0, 1.0]
        baseMatrix = om.MMatrix(r180y) * baseMatrix

    # for negative up axis, rotate 180x before reordering rows
    if upAxis in [3, 4, 5]:
        upAxis -= 3
        r180x = [1.0, 0.0, 0.0, 0.0, 
                 0.0, -1.0, 0.0, 0.0, 
                 0.0, 0.0, -1.0, 0.0, 
                 0.0, 0.0, 0.0, 1.0]
        baseMatrix = om.MMatrix(r180x) * baseMatrix

    # make a matrix R so that R*M is a reordering of the rows of M
    if downAxis == 0 and upAxis == 1:
        # x down y up
        R = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    elif downAxis == 0 and upAxis == 2:
        # x down z up
        R = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    elif downAxis == 1 and upAxis == 0:
        # y down x up
        R = [0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    elif downAxis == 1 and upAxis == 2:
        # y down z up
        R = [0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    elif downAxis == 2 and upAxis == 0:
        # z down x up
        R = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    elif downAxis == 2 and upAxis == 1:
        # z down y up
        R = [0.0, 0.0, -1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    else:
        # for when axis get set to the same value
        R = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]

    # reorder the initial matrix to use the desired down and up axis
    return om.MMatrix(R) * baseMatrix


def list_from_matrix(matrix):
    return list(matrix)


def get_matrix(transform, worldSpace=True):
    if worldSpace:
        return cmds.xform(transform, q=1, matrix=1, ws=1)
    else:
        return cmds.xform(transform, q=1, matrix=1, os=1)


def get_world_matrix(transform):
    return get_matrix(transform, worldSpace=True)


def get_local_matrix(transform):
    return get_matrix(transform, worldSpace=False)


def create_axis_visualizer(name="axisVisualizer"):
    """Generates a single-mesh RGB XYZ axis with tapered ends."""
    
    # Component dimensions
    cyl_radius = 0.1
    cyl_height = 5.0
    cone_radius = 0.3
    cone_height = 1.0
    sphere_radius = 0.5

    # Define colors and generate surface shaders inline
    color_data = {
        'X': ('red', (1.0, 0.0, 0.0)),
        'Y': ('green', (0.0, 1.0, 0.0)),
        'Z': ('blue', (0.0, 0.0, 1.0)),
        'Center': ('gray', (0.5, 0.5, 0.5))
    }
    
    shading_groups = {}
    
    for key, (color_name, rgb) in color_data.items():
        shader = cmds.shadingNode('surfaceShader', asShader=True, name=f"axis_{color_name}_SHD")
        cmds.setAttr(f"{shader}.outColor", rgb[0], rgb[1], rgb[2], type='double3')
        
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"axis_{color_name}_SG")
        cmds.connectAttr(f"{shader}.outColor", f"{sg}.surfaceShader", force=True)
        shading_groups[key] = sg

    # List to collect all geometry nodes for combining
    geo_components = []

    # Build Center Sphere
    center_sphere = cmds.polySphere(r=sphere_radius, name='axis_center_GEO')[0]
    cmds.sets(center_sphere, edit=True, forceElement=shading_groups['Center'])
    geo_components.append(center_sphere)

    # Axis vectors mapped to their corresponding string keys
    axis_vectors = {
        'X': (1, 0, 0),
        'Y': (0, 1, 0),
        'Z': (0, 0, 1)
    }

    # Build cylinders and cones for each axis
    for axis_name, axis_vec in axis_vectors.items():
        
        # Build Cylinder
        cyl = cmds.polyCylinder(r=cyl_radius, h=cyl_height, ax=axis_vec, name=f'{axis_name}_axis_GEO')[0]
        cmds.sets(cyl, edit=True, forceElement=shading_groups[axis_name])
        
        # Offset cylinder
        cyl_offset = [cyl_height / 2.0 * v for v in axis_vec]
        cmds.move(cyl_offset[0], cyl_offset[1], cyl_offset[2], cyl)
        
        # Build Tapered End (Cone)
        cone = cmds.polyCone(r=cone_radius, h=cone_height, ax=axis_vec, name=f'{axis_name}_arrow_GEO')[0]
        cmds.sets(cone, edit=True, forceElement=shading_groups[axis_name])
        
        # Offset cone
        cone_offset = [(cyl_height + (cone_height / 2.0)) * v for v in axis_vec]
        cmds.move(cone_offset[0], cone_offset[1], cone_offset[2], cone)
        
        # Add both to our list of components to unite
        geo_components.extend([cyl, cone])

    # Combine all collected geometry into a single mesh and bake it down (delete history)
    combined_mesh = cmds.polyUnite(geo_components, ch=False, name=name)[0]

    # Clear selection to leave the scene clean
    cmds.select(clear=True)
    return combined_mesh