
import Osiris.lib.base.module as module
import Osiris.lib.tools.shapes.lib as shapeLib
import maya.cmds as cmds
from Osiris.lib.base.decorators import wrapBuild


class SingleJoint(module.Module):

    def __init__(self, character,
                 side=None,
                 mirror=False,
                 shapeType='cube',
                 contract={'startJoint': None},
                 modType='SingleJoint',
                 name='SingleJoint1'):

        super(SingleJoint, self).__init__(
            character,
            modType='SingleJoint',
            side=side,
            mirror=mirror,
            name=name,
            shapeType=shapeType)

        self.components = []
        self.contract = contract
        self.shapeType = shapeType

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.checkContractJoint('startJoint')

        ctrl = shapeLib.Shape(
            self.contract['startJoint'], self.shapeType, jnt=self.contract['startJoint'])

        self.components.append(ctrl)

        self.bindJoints.append(self.contract['startJoint'])

        # binds the joint to the control
        self.parentConstrain(
            ctrl.ctrl, self.contract['startJoint'], maintainOffset=True)

        cmds.parent(ctrl.grp, self.modGrp)
