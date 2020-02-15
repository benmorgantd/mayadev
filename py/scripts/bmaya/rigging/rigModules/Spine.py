# a spine is a ribbon that has attachments at both ends to other joints
# (the pelvis drives the parent of the start, the chest drives the parent of the end)
# it just takes a start and end joint

import maya.cmds as cmds

from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import mathUtils

import Ribbon


class Spine(Ribbon.Ribbon):
    def __init__(self, startJoint=None, endJoint=None, controlAmount=3, jointAmount=4, 
                 name='Spine1', character=None, parent=None, startParent=None, endParent=None):
        Ribbon.Ribbon.__init__(self, name=name, character=character, mirror=False, side='M',
                                    startJoint=startJoint, endJoint=endJoint, controlAmount=controlAmount, 
                                    jointAmount=jointAmount)

        self.startParent = startParent
        self.endParent = endParent

        self.modType = "Spine"

        self.contract = [self.startJoint, self.endJoint, self.startParent, self.endParent]

    @wrapBuild
    def build(self):
        spineRibbon = self.buildRibbon(self.startJoint, self.endJoint, self.name, twist=True, sine=False)

        self.bindJoints = spineRibbon['bindJoints']

        self.driveControls = spineRibbon['driveControls']
        self.followControls = spineRibbon['followControls']

        cmds.parentConstraint(self.startParent, self.driveControls[0].spaceGrp, mo=1)
        cmds.parentConstraint(self.driveControls[-1].ctrl, self.endParent, mo=1)


