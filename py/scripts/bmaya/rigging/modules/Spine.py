# a spine is a ribbon that has attachments at both ends to other joints
# (the pelvis drives the parent of the start, the chest drives the parent of the end)
# it just takes a start and end joint

import maya.cmds as cmds

from bmaya.rigging.rigBuilder.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

from bmaya.rigging.rigBuilder.base import module


class Spine(module.Module):
    def __init__(self, startJoint=None, endJoint=None, name='Spine1', character=None, parent=None):
        super(Spine, self).__init__(modType='Spine', name=name, character=character, mirror=False, side='M')
        
        self.startParent = startParent
        self.endParent = endParent

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        self.bindJoints = self.findHierarchyJoints(startJoint=self.startJoint,
                                                   endJoint=self.endJoint, 
                                                   shortestDistance=True)

