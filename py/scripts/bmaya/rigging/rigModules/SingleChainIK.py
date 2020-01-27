import maya.cmds as cmds

from bmaya.rigging.Osiris.base import module
from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

reload(module)
reload(shapelib)

class SingleChainIK(module.Module):

    def __init__(self, startJoint=None, endJoint=None, name='singleChainIK1', character=None, 
                parent=None, mirror=False):
        super(SingleChainIK, self).__init__(modType='SingleChainIK', name=name, character=character, 
                                          shapeType='cube', mirror=mirror)

        self.parent = parent
        self.startJoint = startJoint
        self.endJoint = endJoint

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        # build a simple single chain ik system

        self.checkContract()

        startCtrl = shapelib.Shape(self.startJoint, 'cube',
                                   jnt=self.startJoint)

        endCtrl = shapelib.Shape(self.endJoint, shapeType='cube', 
                                 jnt=self.endJoint)

        cmds.parent(endCtrl.offsetGrp, startCtrl.ctrl)

        ik, ikGrp = self.makeIkHandle(startJoint=self.startJoint, endJoint=self.endJoint, 
                                      solverType='ikSCsolver', name=self.name + '_ikHandle')

        cmds.parent(ikGrp, self.modGrp)

        # poleVectorCtrl  = shapelib.Shape(self.endJoint, shapeType='cube')

        self.components += [startCtrl, endCtrl]
        self.ikHandles = ik

        self.bindJoints.append(self.startJoint)

        # connect the controls to the joints and effectors
        self.parentConstrain(startCtrl.ctrl, self.startJoint)
        self.parentConstrain(endCtrl.ctrl, ikGrp)

        cmds.parent(startCtrl.offsetGrp, self.componentsGrp)

        if self.parent:
            self.parentConstrain(self.parent, self.components[0].offsetGrp,
                                maintainOffset=True)
