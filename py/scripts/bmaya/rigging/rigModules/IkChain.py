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

        self.bindJoints = self.findHierarchyJoints()

        self.driveJoints = self.createDriveJoints()

        self.components = self.buildIkControls(self.driveJoints)

    def buildIkControls(self, driveJoints):
        # letting components be a local variable here so that we can use this 
        # safer in child methods
        components = []

        startCtrl = shapelib.Shape(driveJoints[0], 'cube',
                                   jnt=driveJoints[0])

        endCtrl = shapelib.Shape(driveJoints[-1], shapeType='cube', 
                                 jnt=driveJoints[-1])

        cmds.parent(endCtrl.offsetGrp, startCtrl.ctrl)

        ik, ikGrp = self.makeIkHandle(startJoint=driveJoints[0], endJoint=driveJoints[-1], 
                                      solverType='ikRPsolver', name=self.name + '_ikHandle')

        poleVectorCtrl = shapelib.Shape(driveJoints[-1] + '_pv', shapeType='cube', jnt=driveJoints[-1])
        
        if len(driveJoints) < 3:
            cmds.xform(poleVectorCtrl.offsetGrp, translation=self.upVector, relative=True, objectSpace=True)
        else:
            cmds.xform(poleVectorCtrl.offsetGrp, translation=mathUtils.findPoleVector(driveJoints), worldSpace=True)
        
        cmds.parent(poleVectorCtrl.offsetGrp, startCtrl.ctrl)
        cmds.pointConstraint(endCtrl.ctrl, poleVectorCtrl.offsetGrp, maintainOffset=True)
        cmds.poleVectorConstraint(poleVectorCtrl.ctrl, ik)

        cmds.parent(ikGrp, self.modGrp)

        components += [startCtrl, endCtrl, poleVectorCtrl]
        self.ikHandles = ik

        # connect the controls to the joints and effectors
        self.parentConstrain(startCtrl.ctrl, driveJoints[0])
        self.parentConstrain(endCtrl.ctrl, ikGrp)

        cmds.parent(startCtrl.offsetGrp, self.componentsGrp)

        return components