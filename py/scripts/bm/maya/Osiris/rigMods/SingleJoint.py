import maya.cmds as cmds

from ..base import module
from ..base.decorators import wrapBuild
from ..tools.shapes import lib as shapeLib


class SingleJoint(module.Module):

    def __init__(self, character, side=None, mirror=False, shapeType='cube',
                 contract={'startJoint': None}, name='SingleJoint1',
                 alignWorld=False):

        super(SingleJoint, self).__init__(character,modType='SingleJoint',
                                          side=side, mirror=mirror, name=name,
                                          shapeType=shapeType,
                                          alignWorld=alignWorld)

        self.components = []
        self.contract = contract
        self.shapeType = shapeType

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.checkContractJoint('startJoint')

        ctrl = shapeLib.Shape(self.contract['startJoint'], self.shapeType,
                              jnt=self.contract['startJoint'])

        self.components.append(ctrl)

        self.bindJoints.append(self.contract['startJoint'])

        # binds the joint to the control
        self.parentConstrain(
            ctrl.ctrl, self.contract['startJoint'], maintainOffset=True)

        cmds.parent(ctrl.grp, self.modGrp)
