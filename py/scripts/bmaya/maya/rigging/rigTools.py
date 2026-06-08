"""Purpose:

Utility functions for working with rigs in maya. These are used by the rig components and postops to perform common tasks on rigs,

such as toggling skinning mode, matching ik to fk, etc.

"""

import json

from ast import literal_eval


import maya.cmds as cmds

from bmaya.core import log

from bmaya.core.util import constants

from bmaya.maya.util import mathUtils


def toggleSkinMode():
    """Toggles skinning mode on the currently built rig."""

    characterNodes = cmds.ls('*.referenceMesh')

    for node in characterNodes:

        currentValue = cmds.getAttr(node)

        cmds.setAttr(node, not currentValue)

        cmds.setAttr('SKELETON.visibility', currentValue)

    sizeJoints()


def sizeJoints():

    skeletonJoints = cmds.listRelatives(

        'SKELETON',

        type='joint',

        allDescendents=True,

        full_path=True)

    bindJoints = cmds.sets('BIND_set', query=True)

    for jnt in skeletonJoints:

        if jnt in bindJoints:

            if 'hand' in jnt:

                cmds.setAttr(jnt + '.radius', 1)

            else:

                cmds.setAttr(jnt + '.radius', 3)

        else:

            cmds.setAttr(jnt + '.drawStyle', 0)


def labelJoints():

    for jnt in cmds.ls(type='joint'):

        jntSplit = jnt.split('_')

        if '_M_' in jnt:

            cmds.setAttr(jnt + '.side', 0)

        if '_L_' in jnt:

            cmds.setAttr(jnt + '.side', 1)

        if '_R_' in jnt:

            cmds.setAttr(jnt + '.side', 2)

        cmds.setAttr(jnt + '.type', 18)

        try:

            cmds.setAttr(

                jnt + '.otherType',

                jntSplit[0] + jntSplit[1],

                type='string')

        except IndexError:

            log.info(jnt + ' may be named incorrectly.')


def getModuleNode(ctrl):

    if 'module' not in cmds.listAttr(ctrl):

        if any(attr in ['node', 'modType'] for attr in cmds.listAttr(ctrl)):

            # ctrl is a module
            return ctrl

        else:

            raise ValueError(

                'Given control {0} is not connected to a module'.format(ctrl))

    mod = cmds.listConnections(ctrl + '.module')[0]

    return mod


def getCharacterNode(ctrl):

    mod = getModuleNode(ctrl)

    character = cmds.listConnections(mod + '.character')[0]

    return character


def getCharacterModules(characterNode):

    return cmds.listConnections(characterNode + '.modules')


def resetControl(ctrl):

    if 'defaultValues' not in cmds.listAttr(ctrl):

        log.info('Control {0} has no default value attribute'.format(ctrl))
        return

    defaultValues = cmds.getAttr(ctrl + '.defaultValues')

    defaultValues = json.loads(defaultValues)

    for attr, value in defaultValues.items():

        cmds.setAttr('{0}.{1}'.format(ctrl, attr), value)


def resetModule(mod):

    components = cmds.listConnections(mod + '.components')

    for component in components:

        resetControl(component)

    if 'defaultValues' not in cmds.listAttr(mod):

        log.info('Module {0} has no default value attribute'.format(mod))
        return

    defaultValues = cmds.getAttr(mod + '.defaultValues')

    defaultValues = json.loads(defaultValues)

    for attr, value in defaultValues.items():

        cmds.setAttr('{0}.{1}'.format(mod, attr), value)


def resetCharacter(ctrl):

    character = getCharacterNode(ctrl)

    modules = getCharacterModules(character)

    for module in modules:

        resetModule(module)


def selectModule(ctrl):

    mod = getModuleNode(ctrl)

    components = cmds.listConnections(mod + '.components')

    for ctrl in components:

        cmds.select(ctrl, add=1)


def keyAll(ctrl):

    character = getCharacterNode(ctrl)

    modules = getCharacterModules(character)

    for mod in modules:

        keyableAttrs = cmds.listAttr(mod, k=1) or []

        for attr in keyableAttrs:

            # set a keyframe

            cmds.setKeyframe(mod + '.' + attr)

        components = cmds.listConnections(mod + '.components')

        for ctrl in components:

            keyableAttrs = cmds.listAttr(ctrl, k=1) or []

            for attr in keyableAttrs:

                # set a keyframe

                cmds.setKeyframe(ctrl + '.' + attr)


def keyIk(ctrl):

    mod = getModuleNode(ctrl)

    ikControls = literal_eval(cmds.getAttr(mod + '.ikComponents'))

    for ikCtrl in ikControls:

        keyableAttrs = cmds.listAttr(ikCtrl, k=1) or []

        for attr in keyableAttrs:

            # set a keyframe

            cmds.setKeyframe(ikCtrl + '.' + attr)


def keyFk(ctrl):

    mod = getModuleNode(ctrl)

    ikControls = literal_eval(cmds.getAttr(mod + '.fkComponents'))

    for fkCtrl in ikControls:

        keyableAttrs = cmds.listAttr(fkCtrl, k=1) or []

        for attr in keyableAttrs:

            # set a keyframe

            cmds.setKeyframe(fkCtrl + '.' + attr)


def matchIkToFk(ctrl):

    # get the module of the selection

    mod = getModuleNode(ctrl)

    # get the position of the fk joints

    fkJoints = literal_eval(cmds.getAttr(mod + '.fkDriveJoints'))

    # get the ik controls

    ikControls = literal_eval(cmds.getAttr(mod + '.ikComponents'))

    # this is a little more complicated if its a spline module

    if cmds.getAttr(mod + '.modType') == 'Spline':

        # we can easily match the start and end controls.

        # This will give us start and end twist.

        mathUtils.matchTransforms(fkJoints[0], ikControls[0])

        mathUtils.matchTransforms(fkJoints[-1], ikControls[-1])

        # now we need to make an approximation for the middle controls

        # We'll do this by fitting a curve through the fk joints

        fitCurve = mathUtils.fitCurveToPoints(

            [cmds.xform(jnt, q=1, t=1, ws=1) for jnt in fkJoints])

        numMiddleControls = len(ikControls) - 2

        for i in range(1, numMiddleControls + 1):

            # move each middle ik component to the percentage position it should be

            # along the curve (assumes controls were created this way to begin)

            matrix = mathUtils.getMatrixAlongCurve(

                fitCurve,

                i /
                float(

                    numMiddleControls +

                    1),

                downAxis=constants.SPINE_UP_AXIS)

            cmds.xform(ikControls[i], matrix=matrix, worldSpace=True)

        cmds.delete(fitCurve)

    else:

        # match the ik start control to the first fk joint position
        cmds.delete(

            cmds.pointConstraint(

                fkJoints[0],

                ikControls[0],

                maintainOffset=False))

        # match the ik end control to the last fk joint position

        mathUtils.matchTransforms(fkJoints[2], ikControls[1])

        # find the pole vector position for the fk joints

        cmds.xform(

            ikControls[2],

            translation=mathUtils.find_pole_vector(

                fkJoints,

                scaleFactor=1.5),

            worldSpace=True)

    cmds.setAttr(mod + '.FKIK', 1)


def matchFkToIk(ctrl):

    # get the module of the selection

    mod = getModuleNode(ctrl)

    # get the position of the fk joints

    ikJoints = literal_eval(cmds.getAttr(mod + '.ikDriveJoints'))

    # get the ik controls

    fkControls = literal_eval(cmds.getAttr(mod + '.fkComponents'))

    for i in range(len(ikJoints)):

        cmds.xform(

            fkControls[i],

            matrix=cmds.getAttr(

                ikJoints[i] +

                '.worldMatrix[0]'),

            worldSpace=True)

    cmds.setAttr(mod + '.FKIK', 0)


def bakeFkToIk(ctrl, bakeRange=None):

    if bakeRange:

        bakeStart = bakeRange[0]

        bakeEnd = bakeRange[1]

    else:

        bakeStart = int(cmds.playbackOptions(query=True, minTime=True))

        bakeEnd = int(cmds.playbackOptions(query=True, maxTime=True))

    mod = getModuleNode(ctrl)
    fk_controls = literal_eval(cmds.getAttr(mod + '.fkComponents'))

    for i in range(bakeStart, bakeEnd):

        cmds.currentTime(i)

        matchFkToIk(ctrl)

        keyFk(ctrl)


def bakeIkToFk(ctrl, bakeRange=None):

    if bakeRange:

        bakeStart = bakeRange[0]

        bakeEnd = bakeRange[1]

    else:

        bakeStart = int(cmds.playbackOptions(query=True, minTime=True))

        bakeEnd = int(cmds.playbackOptions(query=True, maxTime=True))

    mod = getModuleNode(ctrl)

    fkControls = literal_eval(cmds.getAttr(mod + '.ikComponents'))

    for i in range(bakeStart, bakeEnd):

        cmds.currentTime(i)

        matchIkToFk(ctrl)

        keyIk(ctrl)


def _getFirstSelection():

    selection = cmds.ls(selection=True) or []

    if not selection or 'module' not in cmds.listAttr(selection[0]):

        raise ValueError('Please select at least one control.')

    return selection[0]
