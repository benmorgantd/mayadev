import maya.cmds as cmds

from ..base import module
from ..base.decorators import wrapBuild
from bmaya.tools.shapes import shapelib

reload(module)
reload(shapelib)

class SingleJoint(module.Module):

    def __init__(self, startJoint=None, name='singleJoint1', character=None,
                parent=None, shapeType='cube'):
        super(SingleJoint, self).__init__(modType='SingleJoint',
                                          name=name, character=character, shapeType=shapeType)

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

        cmds.parent(ctrl.grp, self.modGrp)

        if self.parent:
            self.parentConstrain(self.parent, self.components[0].grp,
                                maintainOffset=True)
