import maya.cmds as cmds

from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils


class SingleJoint(module.Module):

    def __init__(self, start_joint=None, name='singleJoint1', character=None,
                 parent=None, shapeType='cube',
                 mirror=False, side='L', alignWorld=None,
                 addOffsetControl=False, offsetShapeType='cube'):
        super(SingleJoint, self).__init__(modType='SingleJoint', name=name,
                                          character=character,
                                          shapeType=shapeType, mirror=mirror,
                                          side=side, alignWorld=alignWorld)

        self.parent = parent
        self.start_joint = start_joint

        self.addOffsetControl = addOffsetControl
        self.offsetShapeType = offsetShapeType

        self.contract = [self.start_joint]

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bind_joints.append(self.start_joint)

        self.driveJoints = self.create_drive_joints()

        self.start_jointDriver = self.get_driver(self.start_joint)

        ctrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(
                self.start_jointDriver),
            shapeType=self.shape_type,
            jnt=self.start_jointDriver)

        self.components.append(ctrl)

        if self.addOffsetControl:
            offsetCtrl = shapelib.ControlCurve(
                name=nameUtils.find_control_name(self.start_jointDriver,
                                                 identifier='Offset'),
                shapeType=self.offsetShapeType,
                jnt=self.start_jointDriver)
            cmds.parent(offsetCtrl.offset_grp, ctrl.ctrl)
            self.parent_constrain(offsetCtrl.ctrl, self.start_jointDriver,
                                  maintainOffset=True)
            self.components.append(offsetCtrl)
        else:
            self.parent_constrain(ctrl.ctrl, self.start_jointDriver,
                                  maintainOffset=True)

        cmds.parent(ctrl.offset_grp, self.components_grp)

        self.setup_align_world(ctrl, defaultValue=self.align_world)
