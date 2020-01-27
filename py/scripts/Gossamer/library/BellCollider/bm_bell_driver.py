import maya.cmds as cmds


def bell_driver_setup(vector_start=None,
                       vector_end=None,
                       target=None,
                       angle_min=0,
                       angle_max=45,
                       driven_node=None,
                       driven_vector=None,
                       rotate_vector=None):
    """Creates a 0-1 float value that is driven by the angle between two vectors. The interpolation
    of this can be altered by the user.

    :param vector end: The head of the vector for our Angle Driver setup.
    :param vector_end: The tail of the vector for our Angle Driver setup.
    :param target: An optional value to use a custom target. The script will automatically make one if not.
    :param angle_min: The minimum angle *between the two vectors* that will output 1
    :param angle_max: The maximum angle *between the two vectors* that will output 0
    :param driven_node: The desired node with attributes to drive.
    :param driven_vector: The vector to go out when the sdk is triggered.
    :param rotate_vector: The rotation vector to use when the sdk is triggered.
    :return: remap_value
    :rtype: remapValue node
    """

    # do nothing if we're not given a joint
    if not vector_start or not driven_node or not driven_vector:
        return

    # create a decomposeMatrix node that'll hold the world position of our joint
    joint_decomp = cmds.createNode("decomposeMatrix", name=vector_start + "_decomp#")
    cmds.connectAttr(vector_start + ".worldMatrix[0]", joint_decomp + ".inputMatrix")

    if not vector_end:
        try:
            # check if the joint has a child. If it doesn't raise a ValueError as we cannot continue
            vector_end = cmds.listRelatives(vector_start, children=1, type="joint")[0]
        except TypeError:
            raise ValueError("Cannot make angle driver setup because the joint has no child.")

    # create a decomposeMatrix node that'll hold the world position of our child joint
    joint_child_decomp = cmds.createNode("decomposeMatrix", name=vector_end + "_decomp#")
    cmds.connectAttr(vector_end + ".worldMatrix[0]", joint_child_decomp + ".inputMatrix")

    if not target:
        # if the user hasn't specified a custom target, create one at the location of the child joint
        target = cmds.spaceLocator(name=vector_start + "_angleDriver_target_loc#")[0]
        cmds.delete(cmds.pointConstraint(vector_end, target, mo=0))

    try:
        # try parenting the target locator to the joint parent if it has one.
        joint_parent = cmds.listRelatives(vector_start, parent=1)[0]
        cmds.parent(target, joint_parent, a=1)
    except TypeError:
        # we can pass since the user can manually parent this if she desires
        pass

    # create a decomposeMatrix node that'll hold the world position of our target locator
    target_decomp = cmds.createNode("decomposeMatrix", name=target + "_decomp#")
    cmds.connectAttr(target + ".worldMatrix[0]", target_decomp + ".inputMatrix")

    # determine the vector from the joint to the target by subtracting their world locs using a pma node
    target_vector = cmds.createNode("plusMinusAverage", name=target + "_vector_pma#")
    cmds.setAttr(target_vector + ".op", 2)
    cmds.connectAttr(target_decomp + ".outputTranslate", target_vector + ".input3D[0]")
    cmds.connectAttr(joint_decomp + ".outputTranslate", target_vector + ".input3D[1]")

    # determine the vector from the joint to its child by subtracting their world locs using a pma node
    joint_vector = cmds.createNode("plusMinusAverage", name=vector_start + "_vector_pma#")
    cmds.setAttr(joint_vector + ".op", 2)
    cmds.connectAttr(joint_child_decomp + ".outputTranslate", joint_vector + ".input3D[0]")
    cmds.connectAttr(joint_decomp + ".outputTranslate", joint_vector + ".input3D[1]")

    # create an angleBetween node to calculate the angle between those two vectors
    angle_between = cmds.createNode("angleBetween", name=target + "_angleBetween#")
    cmds.connectAttr(target_vector + ".output3D", angle_between + ".vector1")
    cmds.connectAttr(joint_vector + ".output3D", angle_between + ".vector2")

    # create a remap_value node to remap that angle between 0 and 1
    remap_value = cmds.createNode("remapValue", name=target + "_remapValue#")
    cmds.setAttr(remap_value + ".inputMin", angle_min)

    final_max = abs(angle_max)

    cmds.setAttr(remap_value + ".inputMax", final_max)
    # set smooth and descending value remapping
    cmds.setAttr(remap_value + ".value[0].value_Position", 0)
    cmds.setAttr(remap_value + ".value[0].value_FloatValue", 1.0)
    cmds.setAttr(remap_value + ".value[0].value_Interp", 2)
    cmds.setAttr(remap_value + ".value[1].value_Position", 1)
    cmds.setAttr(remap_value + ".value[1].value_FloatValue", 0.0)
    cmds.setAttr(remap_value + ".value[1].value_Interp", 2)

    cmds.connectAttr(angle_between + ".axisAngle.angle", remap_value + ".inputValue")

    cmds.setDrivenKeyframe(driven_node + ".tx", currentDriver=remap_value + ".outValue",
                           driverValue=0, value=cmds.getAttr(driven_node + ".tx"))
    cmds.setDrivenKeyframe(driven_node + ".ty", currentDriver=remap_value + ".outValue",
                           driverValue=0, value=cmds.getAttr(driven_node + ".ty"))
    cmds.setDrivenKeyframe(driven_node + ".tz", currentDriver=remap_value + ".outValue",
                           driverValue=0, value=cmds.getAttr(driven_node + ".tz"))

    # also set flat keyframes for rotation in case we need to mess with them later
    cmds.setDrivenKeyframe(driven_node + ".rx", currentDriver=remap_value + ".outValue",
                           driverValue=0, value=cmds.getAttr(driven_node + ".rx"))
    cmds.setDrivenKeyframe(driven_node + ".ry", currentDriver=remap_value + ".outValue",
                           driverValue=0, value=cmds.getAttr(driven_node + ".ry"))
    cmds.setDrivenKeyframe(driven_node + ".rz", currentDriver=remap_value + ".outValue",
                           driverValue=0, value=cmds.getAttr(driven_node + ".rz"))

    cmds.xform(driven_node, t=driven_vector, os=1, r=1)

    cmds.setDrivenKeyframe(driven_node + ".tx", currentDriver=remap_value + ".outValue",
                           driverValue=1, value=cmds.getAttr(driven_node + ".tx"))
    cmds.setDrivenKeyframe(driven_node + ".ty", currentDriver=remap_value + ".outValue",
                           driverValue=1, value=cmds.getAttr(driven_node + ".ty"))
    cmds.setDrivenKeyframe(driven_node + ".tz", currentDriver=remap_value + ".outValue",
                           driverValue=1, value=cmds.getAttr(driven_node + ".tz"))

    cmds.setDrivenKeyframe(driven_node + ".rx", currentDriver=remap_value + ".outValue",
                           driverValue=1, value=rotate_vector[0])
    cmds.setDrivenKeyframe(driven_node + ".ry", currentDriver=remap_value + ".outValue",
                           driverValue=1, value=rotate_vector[1])
    cmds.setDrivenKeyframe(driven_node + ".rz", currentDriver=remap_value + ".outValue",
                           driverValue=1, value=rotate_vector[2])

    return remap_value
