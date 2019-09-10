'''Generic IK Chain'''


import maya.cmds as cmds

from ..base import module
from ..base.decorators import wrapBuild
from ..tools.shapes import lib as shapeLib


class IkChain(module.Module):

    solverTypes = ['ikSCsolver', 'ikRPsolver']

    def __init__(self, startJoint=None, endJoint=None, exclude=[],
                 name='ikChain1', solverType='singleChain',
                 shapeType='cube', character=None, parent=None):

        super(IkChain, self).__init__(name=name, modType='IkChain',
                                      shapeType=shapeType,character=character)

        self.parent = parent
        self.startJoint = startJoint
        self.endJoint = endJoint
        self.exclude = exclude
        self.solverType = solverType

    @wrapBuild
    def build(self):
        
        self.checkContractJoint(['startJoint', 'endJoint'])
        self.getContainedJoints()


        ikctrl = shapeLib.Shape(
            self.startJoint, self.shapeType, jnt=self.startJoint)

        self.components.append(ikctrl)

        self.bindJoints.append(self.startJoint)

        # binds the joint to the control
        self.parentConstrain(
            ctrl.ctrl, self.startJoint, maintainOffset=True)

        cmds.parent(ctrl.grp, self.modGrp)

        # if self.parent:
            # self.parentConstrain(self.parent, self.compon)

