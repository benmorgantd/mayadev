import maya.cmds as cmds

from bmaya.rigging.Osiris.base import module
from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

class SingleJoint(module.Module):

    def __init__(self, startJoint=None, name='singleJoint1', character=None, parent=None, 
                 shapeType='cube', mirror=False):
        super(SingleJoint, self).__init__(modType='SingleJoint', name=name, character=character, 
                                          shapeType=shapeType, mirror=mirror)

        self.parent = parent
        self.startJoint = startJoint

        self.contract = [self.startJoint]

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.checkContract()

        ctrl = shapelib.Shape(self.startJoint, self.shapeType,
                              jnt=self.startJoint)

        self.components.append(ctrl)

        self.bindJoints.append(self.startJoint)

        # binds the joint to the control
        self.parentConstrain(
            ctrl.ctrl, self.startJoint, maintainOffset=True)

        cmds.parent(ctrl.offsetGrp, self.componentsGrp)

        if self.parent:
            self.parentConstrain(self.parent, self.componentsGrp, maintainOffset=True)
