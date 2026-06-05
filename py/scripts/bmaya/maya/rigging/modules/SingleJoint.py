import maya.cmds as cmds

from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils


class SingleJoint(module.Module):

    def __init__(self, startJoint=None, name='singleJoint1', character=None,
                 parent=None, shapeType='cube',
                 mirror=False, side='L', alignWorld=None,
                 addOffsetControl=False, offsetShapeType='cube'):
        super(SingleJoint, self).__init__(modType='SingleJoint', name=name,
                                          character=character,
                                          shapeType=shapeType, mirror=mirror,
                                          side=side, alignWorld=alignWorld)

        self.parent = parent
        self.startJoint = startJoint

        self.addOffsetControl = addOffsetControl
        self.offsetShapeType = offsetShapeType

        self.contract = [self.startJoint]

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bindJoints.append(self.startJoint)

        self.driveJoints = self.createDriveJoints()

        self.startJointDriver = self.getDriver(self.startJoint)

        ctrl = shapelib.ControlCurve(name=nameUtils.findControlName(self.startJointDriver),
                                     shapeType=self.shapeType,
                                     jnt=self.startJointDriver)

        self.components.append(ctrl)

        if self.addOffsetControl:
            offsetCtrl = shapelib.ControlCurve(
                name=nameUtils.findControlName(self.startJointDriver,
                                          identifier='Offset'),
                shapeType=self.offsetShapeType,
                jnt=self.startJointDriver)
            cmds.parent(offsetCtrl.offsetGrp, ctrl.ctrl)
            self.parentConstrain(offsetCtrl.ctrl, self.startJointDriver,
                                 maintainOffset=True)
            self.components.append(offsetCtrl)
        else:
            self.parentConstrain(ctrl.ctrl, self.startJointDriver,
                                 maintainOffset=True)

        cmds.parent(ctrl.offsetGrp, self.componentsGrp)

        self.setupAlignWorld(ctrl, defaultValue=self.alignWorld)
