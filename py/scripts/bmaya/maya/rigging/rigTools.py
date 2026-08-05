"""Purpose:

Utility functions for working with rigs in maya. These are used by the rig components and postops to perform common tasks on rigs,

such as toggling skinning mode, matching ik to fk, etc.

"""

import json

from ast import literal_eval


import maya.cmds as cmds

from bmaya.core import log

from bmaya.core import constants

from bmaya.maya.util import mathUtils
from . import joint


def toggle_skin_mode():
    """Toggles skinning mode on the currently built rig."""

    characterNodes = cmds.ls("*.referenceMesh")

    for node in characterNodes:

        currentValue = cmds.getAttr(node)

        cmds.setAttr(node, not currentValue)

        cmds.setAttr("SKELETON.visibility", currentValue)

    joint.size_joints()


def get_module_node(ctrl):

    if "module" not in cmds.listAttr(ctrl):

        if any(attr in ["node", "modType"] for attr in cmds.listAttr(ctrl)):

            # ctrl is a module
            return ctrl

        else:

            raise ValueError(
                "Given control {0} is not connected to a module".format(ctrl)
            )

    mod = cmds.listConnections(ctrl + ".module")[0]

    return mod


def get_character_node(ctrl):

    mod = get_module_node(ctrl)

    character = cmds.listConnections(mod + ".character")[0]

    return character


def get_character_modules(characterNode):

    return cmds.listConnections(characterNode + ".modules")


def reset_control(ctrl):

    if "defaultValues" not in cmds.listAttr(ctrl):

        log.info("Control {0} has no default value attribute".format(ctrl))
        return

    defaultValues = cmds.getAttr(ctrl + ".defaultValues")

    defaultValues = json.loads(defaultValues)

    for attr, value in defaultValues.items():

        cmds.setAttr("{0}.{1}".format(ctrl, attr), value)


def reset_module(mod):

    components = cmds.listConnections(mod + ".components")

    for component in components:

        reset_control(component)

    if "defaultValues" not in cmds.listAttr(mod):

        log.info("Module {0} has no default value attribute".format(mod))
        return

    defaultValues = cmds.getAttr(mod + ".defaultValues")

    defaultValues = json.loads(defaultValues)

    for attr, value in defaultValues.items():

        cmds.setAttr("{0}.{1}".format(mod, attr), value)


def reset_character(ctrl):

    character = get_character_node(ctrl)

    modules = get_character_modules(character)

    for module in modules:

        reset_module(module)


def select_module(ctrl):

    mod = get_module_node(ctrl)

    components = cmds.listConnections(mod + ".components")

    for ctrl in components:

        cmds.select(ctrl, add=1)


# TODO: this should be on the Character class
def key_all(ctrl):

    character = get_character_node(ctrl)

    modules = get_character_modules(character)

    for mod in modules:

        keyableAttrs = cmds.listAttr(mod, k=1) or []

        for attr in keyableAttrs:

            # set a keyframe

            cmds.setKeyframe(mod + "." + attr)

        components = cmds.listConnections(mod + ".components")

        for ctrl in components:

            keyableAttrs = cmds.listAttr(ctrl, k=1) or []

            for attr in keyableAttrs:

                # set a keyframe

                cmds.setKeyframe(ctrl + "." + attr)


def key_ik(ctrl):

    mod = get_module_node(ctrl)

    ikControls = literal_eval(cmds.getAttr(mod + ".ikComponents"))

    for ikCtrl in ikControls:

        keyableAttrs = cmds.listAttr(ikCtrl, k=1) or []

        for attr in keyableAttrs:

            # set a keyframe

            cmds.setKeyframe(ikCtrl + "." + attr)


def key_fk(ctrl):

    mod = get_module_node(ctrl)

    ikControls = literal_eval(cmds.getAttr(mod + ".fkComponents"))

    for fkCtrl in ikControls:

        keyableAttrs = cmds.listAttr(fkCtrl, k=1) or []

        for attr in keyableAttrs:

            # set a keyframe

            cmds.setKeyframe(fkCtrl + "." + attr)


def match_ik_to_fk(ctrl):

    # get the module of the selection

    mod = get_module_node(ctrl)

    # get the position of the fk joints

    fkJoints = literal_eval(cmds.getAttr(mod + ".fkDriveJoints"))

    # get the ik controls

    ik_controls = literal_eval(cmds.getAttr(mod + ".ikComponents"))

    # this is a little more complicated if its a spline module

    if cmds.getAttr(mod + ".modType") == "Spline":

        # we can easily match the start and end controls.

        # This will give us start and end twist.

        mathUtils.match_transforms(fkJoints[0], ik_controls[0])

        mathUtils.match_transforms(fkJoints[-1], ik_controls[-1])

        # now we need to make an approximation for the middle controls

        # We'll do this by fitting a curve through the fk joints

        fitCurve = mathUtils.fit_curve_to_points(
            [cmds.xform(jnt, q=1, t=1, ws=1) for jnt in fkJoints]
        )

        numMiddleControls = len(ik_controls) - 2

        for i in range(1, numMiddleControls + 1):

            # move each middle ik component to the percentage position it should be

            # along the curve (assumes controls were created this way to begin)

            matrix = mathUtils.get_matrix_along_curve(
                fitCurve,
                i / float(numMiddleControls + 1),
                downAxis=constants.SPINE_UP_AXIS,
            )

            cmds.xform(ik_controls[i], matrix=matrix, worldSpace=True)

        cmds.delete(fitCurve)

    else:

        # match the ik start control to the first fk joint position
        cmds.delete(
            cmds.pointConstraint(fkJoints[0], ik_controls[0], maintainOffset=False)
        )

        # match the ik end control to the last fk joint position

        mathUtils.match_transforms(fkJoints[2], ik_controls[1])

        # find the pole vector position for the fk joints

        cmds.xform(
            ik_controls[2],
            translation=mathUtils.find_pole_vector(fkJoints, scaleFactor=1.5),
            worldSpace=True,
        )

    cmds.setAttr(mod + ".FKIK", 1)


def match_fk_to_ik(ctrl):

    # get the module of the selection

    mod = get_module_node(ctrl)

    # get the position of the fk joints

    ikJoints = literal_eval(cmds.getAttr(mod + ".ikDriveJoints"))

    # get the ik controls

    fkControls = literal_eval(cmds.getAttr(mod + ".fkComponents"))

    for i in range(len(ikJoints)):

        cmds.xform(
            fkControls[i],
            matrix=cmds.getAttr(ikJoints[i] + ".worldMatrix[0]"),
            worldSpace=True,
        )

    cmds.setAttr(mod + ".FKIK", 0)


def bake_fk_to_ik(ctrl, bakeRange=None):

    if bakeRange:

        bakeStart = bakeRange[0]

        bakeEnd = bakeRange[1]

    else:

        bakeStart = int(cmds.playbackOptions(query=True, minTime=True))

        bakeEnd = int(cmds.playbackOptions(query=True, maxTime=True))

    for i in range(bakeStart, bakeEnd):

        cmds.currentTime(i)

        match_fk_to_ik(ctrl)

        key_fk(ctrl)


def bake_ik_to_fk(ctrl, bakeRange=None):

    if bakeRange:
        bakeStart = bakeRange[0]
        bakeEnd = bakeRange[1]
    else:
        bakeStart = int(cmds.playbackOptions(query=True, minTime=True))
        bakeEnd = int(cmds.playbackOptions(query=True, maxTime=True))

    for i in range(bakeStart, bakeEnd):
        cmds.currentTime(i)
        match_ik_to_fk(ctrl)
        key_ik(ctrl)
