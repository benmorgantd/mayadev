import maya.cmds as cmds

from bmaya.rigging.Osiris.base import module
from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

from bmaya.rigging.Osiris.tools import mathUtils

reload(module)
reload(shapelib)


class IkChain(module.Module):

    def __init__(self, startJoint=None, endJoint=None, name='IkChain1', character=None, 
                parent=None, mirror=False, upVector=[0,2,0], exclude=[]):
        super(IkChain, self).__init__(modType='IkChain', name=name, character=character, 
                                          shapeType='cube', mirror=mirror)

        self.parent = parent
        self.startJoint = startJoint
        self.endJoint = endJoint
        self.upVector = upVector
        self.exclude = exclude

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        # build a simple single chain ik system

        self.checkContract()

        self.bindJoints = self.findHierarchyJoints()

        self.driveJoints = self.createDriveJoints()

        startCtrl = shapelib.Shape(self.getDriver(self.startJoint), 'cube',
                                   jnt=self.getDriver(self.startJoint))

        endCtrl = shapelib.Shape(self.getDriver(self.endJoint), shapeType='cube', 
                                 jnt=self.getDriver(self.endJoint))

        cmds.parent(endCtrl.offsetGrp, startCtrl.ctrl)

        ik, ikGrp = self.makeIkHandle(startJoint=self.getDriver(self.startJoint), endJoint=self.getDriver(self.endJoint), 
                                      solverType='ikRPsolver', name=self.name + '_ikHandle')

        poleVectorCtrl = shapelib.Shape(self.getDriver(self.endJoint) + '_pv', shapeType='cube', jnt=self.getDriver(self.endJoint))
        
        if len(self.driveJoints) < 3:
            cmds.xform(poleVectorCtrl.offsetGrp, translation=self.upVector, relative=True, objectSpace=True)
        else:
            cmds.xform(poleVectorCtrl.offsetGrp, translation=mathUtils.findPoleVector(self.driveJoints), worldSpace=True)
        
        cmds.parent(poleVectorCtrl.offsetGrp, startCtrl.ctrl)
        cmds.pointConstraint(endCtrl.ctrl, poleVectorCtrl.offsetGrp, maintainOffset=True)
        cmds.poleVectorConstraint(poleVectorCtrl.ctrl, ik)

        cmds.parent(ikGrp, self.modGrp)

        self.components += [startCtrl, endCtrl, poleVectorCtrl]
        self.ikHandles = ik

        # connect the controls to the joints and effectors
        self.parentConstrain(startCtrl.ctrl, self.getDriver(self.startJoint))
        self.parentConstrain(endCtrl.ctrl, ikGrp)

        cmds.parent(startCtrl.offsetGrp, self.componentsGrp)

        if self.parent:
            self.parentConstrain(self.parent, self.components[0].offsetGrp,
                                maintainOffset=True)
