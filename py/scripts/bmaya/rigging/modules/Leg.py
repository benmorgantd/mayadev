import maya.cmds as cmds

from bmaya.rigging.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import name 

import _ThreeJointIkFkTwist
import _Foot

class Leg(_ThreeJointIkFkTwist.ThreeJointIkFkTwist, _Foot.Foot):

    def __init__(self, startJoint=None, ankle=None, ball=None, heel=None, bankOut=None, bankIn=None, toeTip=None, 
                 name='Leg1', character=None, parent=None, mirror=False, side='L'):

        _ThreeJointIkFkTwist.ThreeJointIkFkTwist.__init__(self, startJoint=startJoint, endJoint=ankle, name=name + '_ikFkChain', 
                                                          character=character, parent=parent, mirror=mirror, side=side, 
                                                          fkikDefault=1, alignWorld=True)

        _Foot.Foot.__init__(self, ankle=ankle, ball=ball, heel=heel, bankOut=bankOut, bankIn=bankIn, toeTip=toeTip, name=name + '_Foot')
        
        self.modType = "Leg"

        self.contract = [self.startJoint, self.endJoint, self.ankle, self.ball, 
                        self.toeTip, self.bankOut, self.bankIn, self.heel]

    @wrapBuild
    def build(self):
        _ThreeJointIkFkTwist.ThreeJointIkFkTwist.build(self, self.startJoint, self.ankle, worldAimTarget=self.ball, downAxis='Y', upAxis='X')
        _Foot.Foot.build(self)

        self.components += self.footComponents 

        self.blendChains(self.footFkDriveJoints, self.footIkDriveJoints, 
                         self.footDriveJoints, self.node + '.FKIK')

        cmds.parent(self.footIkDriveJoints[0], self.ikDriveJoints[2])
        cmds.parent(self.footFkDriveJoints[0], self.fkDriveJoints[2])
        cmds.parent(self.footDriveJoints[0], self.driverGrp)
        cmds.parent(self.footIkComponents[0].offsetGrp, self.componentsGrp)
        cmds.parent(self.footFkComponents[0].offsetGrp, self.fkComponents[-1].ctrl)

        cmds.parentConstraint(self.ikComponents[1].ctrl, self.footIkComponents[0].offsetGrp, maintainOffset=True)

        # remove parent constraint on the drive (leg) ankle and make its driver the (foot) ankle
        for node in [self.driveJoints[2], self.ikHandleGrp, self.ball, self.ikDriveJoints[2]]:
            cmds.delete(cmds.listRelatives(node, type='constraint'))

        cmds.parentConstraint(self.footDriveJoints[0], self.driveJoints[2], maintainOffset=True)
        cmds.parentConstraint(self.ballRollCtrl.ctrl, self.ikHandleGrp, maintainOffset=True)
        cmds.parentConstraint(self.footDriveJoints[1], self.ball, maintainOffset=True)

        # hook up fk and ik foot control visibility
        cmds.connectAttr(self.blendReverse, '{0}.v'.format(self.footFkComponents[0].offsetGrp))
        cmds.connectAttr(self.node + '.FKIK', '{0}.v'.format(self.footIkComponents[0].offsetGrp))

        self.addFkGimbalControl()
        self.setupAlignWorld(self.fkShoulderGimbal, defaultValue=self.alignWorld)

        self.addIkToeBend()

    def addFkGimbalControl(self):
        # add a second control on top of the existing leg fk 
        # that has zxy (2) rotation order

        shoulderFkOffset = self.fkComponents[0].offsetGrp

        ctrlName = name.findControlName(self.fkComponents[0].ctrl, identifier='Gimbal')
        self.fkShoulderGimbal = shapelib.Shape(name=ctrlName, shapeType='sphere', jnt=shoulderFkOffset)

        # change its rotate order to zxy from that of the shoulder fk offset group
        cmds.setAttr(self.fkShoulderGimbal.ctrl + '.rotateOrder', 2)

        cmds.parent(self.fkShoulderGimbal.offsetGrp, self.componentsGrp, a=1)
        cmds.parent(self.fkComponents[0].offsetGrp, self.fkShoulderGimbal.ctrl, a=1)

        # hook it up to the visibility switch
        cmds.connectAttr(self.blendReverse, self.fkShoulderGimbal.offsetGrp + '.v')

        self.components.append(self.fkShoulderGimbal)

    def addIkToeBend(self):

        # create a group in the ik reverse hierarchy that's the parent of the
        # ball ik handle and has the pivot of the next joint in the hierarchy
        toeJntNameSplit = self.toeTip.split('_')
        ballIkGrpName = '{0}Wiggle_{1}_{2}_offsetGrp'.format(toeJntNameSplit[0], toeJntNameSplit[1], toeJntNameSplit[2])

        ballIkGrp = cmds.group(empty=True, name=ballIkGrpName)

        cmds.delete(cmds.parentConstraint(self.reverseHierarchy[1], ballIkGrp, maintainOffset=False))
        
        cmds.parent(ballIkGrp, self.reverseHierarchy[0])

        cmds.parent(self.ballToToeIk, ballIkGrp)

        self.toeBendCtrl = shapelib.Shape(name=name.findControlName(ballIkGrp), jnt=ballIkGrp, shapeType='cube')
        cmds.parent(self.toeBendCtrl.offsetGrp, self.toeTipCtrl.ctrl)
        cmds.parentConstraint(self.toeBendCtrl, ballIkGrp)

