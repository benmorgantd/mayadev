# a spine is a ribbon that has attachments at both ends to other joints
# (the pelvis drives the parent of the start, the chest drives the parent of the end)
# it just takes a start and end joint

import maya.cmds as cmds

from bmaya.rigging.rigBuilder.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

import _Ribbon


class Spine(_Ribbon.Ribbon):
    def __init__(self, startJoint=None, endJoint=None, controlAmount=3, jointAmount=4, 
                 name='Spine1', character=None, parent=None, startParent=None, endParent=None):

        _Ribbon.Ribbon.__init__(self, name=name, character=character, mirror=False, side='M',
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

        cmds.pointConstraint(self.startParent, self.driveControls[0].spaceGrp, mo=1)
        cmds.parentConstraint(self.driveControls[-1].ctrl, self.endParent, mo=1)

        self.fkRibbonDriveControls = self.buildFkRibbonDriveControls(self.driveControls)

        self.components += self.fkRibbonDriveControls


    """
    The Spine module is the first module where we're creating most of the controls from outside the 
    input Skeleton file. This creates a number of difficulties, includeing:
    - how to name the controls/joints in a unique way
    - how to orient the drive controls
    - how to attach props to those drive controls
    - ** one of the input controls isn't used by the module at all, so we then have joints in our 
         bind skeleton that are not bind joints

    Solution:
    - our input skeleton file has locators in it that define where these joints are and will be oriented
    - there are locators in between the main locators (called minor locators)
        - the children of those locators can be modules.

    """