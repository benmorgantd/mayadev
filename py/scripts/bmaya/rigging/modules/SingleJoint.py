import maya.cmds as cmds

from bmaya.rigging.rigBuilder.base import module
from bmaya.rigging.rigBuilder.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

class SingleJoint(module.Module):

    def __init__(self, startJoint=None, name='singleJoint1', character=None, parent=None, 
                 shapeType='cube', mirror=False, side='L', alignWorld=None):
        super(SingleJoint, self).__init__(modType='SingleJoint', name=name, character=character, 
                                          shapeType=shapeType, mirror=mirror, side=side, alignWorld=alignWorld)

        self.parent = parent
        self.startJoint = startJoint

        self.contract = [self.startJoint]

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bindJoints.append(self.startJoint)

        self.driveJoints = self.createDriveJoints()

        self.startJointDriver = self.getDriver(self.startJoint)

        ctrl = shapelib.Shape(name=self.findControlName(self.startJointDriver), shapeType=self.shapeType,
                              jnt=self.startJointDriver)

        self.components.append(ctrl)

        self.parentConstrain(ctrl.ctrl, self.startJointDriver, maintainOffset=True)

        cmds.parent(ctrl.offsetGrp, self.componentsGrp)

        self.setupAlignWorld(ctrl, defaultValue=self.alignWorld)

