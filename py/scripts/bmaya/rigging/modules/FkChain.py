import maya.cmds as cmds

from bmaya.rigging.base import module
from bmaya.rigging.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import name


##reload(module)


class FkChain(module.Module):

    def __init__(self, startJoint=None, endJoint=None, exclude=[],
                 name='FkChain1',
                 character=None, parent=None, shapeType='cube', mirror=False,
                 side='L',
                 alignWorld=False):

        module.Module.__init__(self, name=name, modType='FkChain',
                               character=character,
                               shapeType=shapeType, mirror=mirror, side=side,
                               alignWorld=alignWorld)

        self.parent = parent
        self.startJoint = startJoint
        # If no endJoint is given, the chain will expand through the dag
        # and trim itself at joints in the exclude list
        self.endJoint = endJoint
        self.exclude = exclude

        self.contract = [self.startJoint]

    @wrapBuild
    def build(self):
        # finds the joints that should belong in the chain
        self.bindJoints = self.findHierarchyJoints(exclude=self.exclude)
        self.driveJoints = self.createDriveJoints()

        self.components = self.buildFkControls(self.driveJoints,
                                               setupAlignWorld=True)


