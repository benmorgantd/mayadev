"""Purpose:
Utility functions for working with names in maya. These are used by various components to perform common tasks
that involve naming, such as naming joints and controls based on a consistent naming convention.
"""

import maya.cmds as cmds
from bmaya.core import constants


def name_selection(selection, name="joint", side="L", suffix="JNT"):

    if not selection:
        return

    sel_len = len(selection)

    for i in range(sel_len - 1, -1, -1):
        new_name = "_".join([name, str(i).zfill(2), side, suffix])

        if cmds.objExists(new_name) and new_name not in selection:
            raise ValueError(f"An object with the name '{new_name}' already exists")

        cmds.rename(selection[i], new_name)

def name_new_node(name, index, side, suffix):
    new_name = "_".join([name, str(index).zfill(2), side, suffix])

    if cmds.objExists(new_name):
        raise ValueError(f"An object with the name '{new_name}' already exists")

    return new_name

def name_new_bind_joint(name, index, side):
    return name_new_node(name, index, side, constants.JOINT_SUFFIX)

def name_new_guide(name, index, side):
    return name_new_node(name, index, side, constants.GUIDE_SUFFIX)

def find_control_name(node, identifier=None):
    node_split = node.split("_")
    if identifier:
        node_split[0] += identifier

    ctrl_name = "_".join(node_split[0:-1])

    ctrl_name = "_".join([ctrl_name, constants.CTRL_SUFFIX])

    return ctrl_name


def find_joint_name(node, identifier=None, count=0, suffix="DRIVER"):
    node_split = node.split("_")

    if identifier:
        node_split[0] += identifier
    if isinstance(count, int):
        node_split[1] = str(count).zfill(2)

    jnt_name = "_".join(node_split[0:-1])

    suffix = suffix.replace("_", "")

    jnt_name = jnt_name + "_" + suffix

    return jnt_name
