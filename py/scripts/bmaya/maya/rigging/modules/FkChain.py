import maya.cmds as cmds

from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils


class FkChain(module.Module):

    def __init__(self, start_joint=None, endJoint=None, exclude=[],
                 name='FkChain1',
                 character=None, parent=None, shapeType='cube', mirror=False,
                 side='L',
                 alignWorld=False):

        module.Module.__init__(self, name=name, modType='FkChain',
                               character=character,
                               shapeType=shapeType, mirror=mirror, side=side,
                               alignWorld=alignWorld)

        self.parent = parent
        self.start_joint = start_joint
        # If no endJoint is given, the chain will expand through the dag
        # and trim itself at joints in the exclude list
        self.endJoint = endJoint
        self.exclude = exclude

        self.contract = [self.start_joint]

    @wrapBuild
    def build(self):
        # finds the joints that should belong in the chain
        self.bindJoints = self.find_hierarchy_joints(exclude=self.exclude)
        self.driveJoints = self.create_drive_joints()

        self.components = self.build_fk_controls(self.driveJoints,
                                                 setup_align_world=True)
