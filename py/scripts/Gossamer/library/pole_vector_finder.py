import maya.OpenMaya as om


def find_pole_vector(up_joint, mid_joint, low_joint, scale_factor=1):
    joints = om.MSelectionList()

    joints.add(up_joint)
    joints.add(mid_joint)
    joints.add(low_joint)

    up_joint_dag = om.MDagPath()
    mid_joint_dag = om.MDagPath()
    low_joint_dag = om.MDagPath()

    joints.getDagPath(0, up_joint_dag)
    joints.getDagPath(1, mid_joint_dag)
    joints.getDagPath(2, low_joint_dag)

    up_joint_fn_trans = om.MFnTransform(up_joint_dag)
    mid_joint_fn_trans = om.MFnTransform(mid_joint_dag)
    low_joint_fn_trans = om.MFnTransform(low_joint_dag)

    up_joint_vec = up_joint_fn_trans.getTranslation(om.MSpace.kWorld)
    mid_joint_vec = mid_joint_fn_trans.getTranslation(om.MSpace.kWorld)
    low_joint_vec = low_joint_fn_trans.getTranslation(om.MSpace.kWorld)

    # A - B gives us the vector from B to A
    up_low_vec = low_joint_vec - up_joint_vec
    up_mid_vec = mid_joint_vec - up_joint_vec

    # project the up_mid_vec onto the line made by up_low_vec
    projection = up_low_vec * ((up_mid_vec * up_low_vec) / (up_low_vec * up_low_vec))
    affine_projection = projection + up_joint_vec

    projection_through_mid_joint = (mid_joint_vec - affine_projection)
    # multiply by ((up_to_mid_vec.length() / projection_through_mid_joint)
    scaled_projection_through_mid_joint = projection_through_mid_joint * (
        up_mid_vec.length() / projection_through_mid_joint.length()) * scale_factor

    pole_vector_location = (affine_projection + scaled_projection_through_mid_joint)

    return [pole_vector_location.x, pole_vector_location.y, pole_vector_location.z]
