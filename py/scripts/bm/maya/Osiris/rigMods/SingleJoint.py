import maya.cmds as cmds

from ..base import module
from ..base.decorators import wrapBuild
from ..tools.shapes import lib as shapeLib


class SingleJoint(module.Module):
    defaultArgs = {'startJoint': None,
                   'modType': 'SingleJoint',
                   'name': 'singleJoint1',
                   'shapeType':'cube',
                   'alignWorld':False}


    def __init__(self, startJoint=None, name='singleJoint1', character=None):
        super(SingleJoint, self).__init__(modType='SingleJoint',
                                          name=name, character=character)

        self.startJoint = startJoint

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.checkContractJoint('startJoint')

        ctrl = shapeLib.Shape(self.startJoint, self.shapeType,
                              jnt=self.startJoint)

        self.components.append(ctrl)

        self.bindJoints.append(self.startJoint)

        # binds the joint to the control
        self.parentConstrain(
            ctrl.ctrl, self.startJoint, maintainOffset=True)

        cmds.parent(ctrl.grp, self.modGrp)
