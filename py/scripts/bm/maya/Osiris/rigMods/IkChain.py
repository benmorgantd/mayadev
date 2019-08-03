'''Generic IK Chain'''


import maya.cmds as cmds

from ..base import module
from ..base.decorators import wrapBuild
from ..tools.shapes import lib as shapeLib


class IkChain(module.Module):
    solverTypes = ['ikSCsolver', 'ikRPsolver']

    def __init__(self, character,
                 side=None,
                 mirror=False,
                 shapeType='cube',
                 contract={'startJoint': None, 'endJoint': None},
                 exclude=[],
                 modType='IkChain',
                 name='IkChain1',
                 solverType='singleChain'):

        super(IkChain, self).__init__(
            character,
            modType='IkChain',
            side=side,
            mirror=mirror,
            name=name,
            shapeType=shapeType)

        self.components = []
        self.contract = contract
        self.shapeType = shapeType

    @wrapBuild
    def build(self):
        
        self.checkContractJoint(['startJoint', 'endJoint'])
        self.getContainedJoints()


        # ikctrl = shapeLib.Shape(
        #     self.contract['startJoint'], self.shapeType, jnt=self.contract['startJoint'])

        # self.components.append(ctrl)

        # self.bindJoints.append(self.contract['startJoint'])

        # # binds the joint to the control
        # self.parentConstrain(
        #     ctrl.ctrl, self.contract['startJoint'], maintainOffset=True)

        # cmds.parent(ctrl.grp, self.modGrp)

