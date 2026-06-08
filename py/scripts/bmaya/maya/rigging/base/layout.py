"""Purpose:
The Layout module is the first module in the rig hierarchy. It is responsible for importing the skeleton and mesh,
and creating the main rig groups and sets. It also creates a stack of offset controls that can be used to position
the rig in the scene before building the rest of the rig.
"""
import maya.cmds as cmds

from . import module
from .decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.core import constants, log


class Layout(module.Module):
    """Every rig must have a Layout module"""

    def __init__(self, character=None):
        super(
            Layout,
            self).__init__(
            mod_type='Layout',
            shape_type='pointedCircle',
            name='Layout',
            character=character)

    @wrapBuild
    def build(self):

        # import only the data from the skeleton file's Layout namespace
        # to do this we'll first open the file and

        cmds.file(self.character.skeleton.full_path, i=True,
                  applyTo=':', loadReferenceDepth='none')
        log.info('>>> Imported skeleton component <<<<')

        # import the mesh
        cmds.file(self.character.mesh.full_path, i=True,
                  applyTo=':', loadReferenceDepth='none')
        log.info('>>> Imported mesh component <<<<')

        self.make_rig_sets()
        self.make_rig_groups()
        self.make_ctrls()

    def make_rig_sets(self):
        self.character.mesh_set = cmds.sets([cmds.listRelatives(shp, parent=True)[
            0] for shp in cmds.ls(type='mesh')], name='MESH_set')

    def make_rig_groups(self):
        self.character.rig_grp = cmds.group(empty=True, name='RIG')

        self.character.connect_to_character(self.character.rig_grp)

        try:
            self.character.mesh_grp = cmds.group(
                self.character.mesh_set, name='MESH')
        except RuntimeError:
            self.character.mesh_grp = cmds.group(empty=True, name='MESH')

        self.character.skeleton_grp = cmds.group(
            constants.ROOT_JOINT, name='SKELETON')
        cmds.setAttr(self.character.skeleton_grp + '.visibility', 0)

        self.character.modules_grp = cmds.group(empty=True, name='MODULES')

        cmds.parent(self.character.modules_grp, self.character.skeleton_grp,
                    self.character.mesh_grp, self.character.rig_grp)

        for grp in [
                self.character.modules_grp,
                self.character.skeleton_grp,
                self.character.mesh_grp,
                self.character.rig_grp]:
            for transform in ['translate', 'rotate', 'scale']:
                for axis in ['X', 'Y', 'Z']:
                    cmds.setAttr(
                        '{0}.{1}{2}'.format(
                            grp, transform, axis), lock=True)

    def make_ctrls(self):
        # make a stack of offset controls
        for i in range(
                constants.COUNT_START,
                constants.COUNT_START +
                constants.LAYOUT_CONTROL_COUNT):
            if i > constants.COUNT_START:
                shp = shapelib.ControlCurve(
                    name='layout_{0:02d}_{1}_{2}'.format(
                        i,
                        constants.SIDE_NAMES['middle'],
                        constants.CTRL_SUFFIX),
                    shapeType=self.shape_type,
                    scale=(
                        1 - (
                            (i - 1) * 0.15)))
                cmds.parent(shp.offset_grp, previous_ctrl.ctrl)
                previous_ctrl = shp
            else:
                shp = shapelib.ControlCurve(
                    name='layout_{0:02d}_{1}_{2}'.format(
                        i,
                        constants.SIDE_NAMES['middle'],
                        constants.CTRL_SUFFIX),
                    shapeType=self.shape_type,
                    scale=(
                        1 - (
                            (i - 1) * 0.15)))
                cmds.parent(shp.offset_grp, self.mod_grp)
                previous_ctrl = shp

            # TODO: add back in moveable pivot?
            # pivot = self.addMoveablePivot(shp)
            self.components.append(shp)
            # self.components.append(pivot)

        cmds.parent(self.components[0].offset_grp, self.components_grp)
