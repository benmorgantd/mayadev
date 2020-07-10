import maya.cmds as cmds

from bmaya.rigging.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import name, constants 

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
        self.addStretchySetup()

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

    def addStretchySetup(self):
        """Build a simple stretchy leg setup using knee slide, pin, and stretch"""
        
        # get starting length of upper and lower ik limbs
        upLimbLen = cmds.getAttr('{0}.translate{1}'.format(self.ikDriveJoints[1], constants.DOWN_AXIS.upper()))
        loLimbLen = cmds.getAttr('{0}.translate{1}'.format(self.ikDriveJoints[2], constants.DOWN_AXIS.upper()))
        
        maxStretch = upLimbLen + loLimbLen

        # create a distanceBetween node to track the distance between the upper
        # and lower ik controls
        ikDistance = cmds.createNode('distanceBetween', name='{0}_{1}_legIkLength'.format(self.name, self.side))
        cmds.connectAttr(self.ikComponents[0].ctrl + '.worldMatrix[0]', ikDistance + '.inMatrix1')
        cmds.connectAttr(self.ikComponents[1].ctrl + '.worldMatrix[0]', ikDistance + '.inMatrix2')
        
        # create a condition node to track if we're stretching
        stretchCondition = cmds.createNode('condition', name='{0}_{1}_ikStretchCondition'.format(self.name, self.side))

        # connect that distance to the first term of our conditional
        cmds.connectAttr(ikDistance + '.distance', stretchCondition + '.firstTerm')
        
        # the second term should be maxStretch
        cmds.setAttr(stretchCondition + '.secondTerm', maxStretch)

        # if greater than
        cmds.setAttr(stretchCondition + '.operation', 2)

        # false conditions are the initial down axis values for the limbs
        cmds.setAttr(stretchCondition + '.colorIfFalseR', upLimbLen)
        cmds.setAttr(stretchCondition + '.colorIfFalseG', loLimbLen)

        # true conditions are the amount we're stretching times the starting
        # lengths
        
        # we need a multiply node to find that out
        stretchFactor = cmds.shadingNode('multDoubleLinear', name='{0}_{1}_stretchFactor'.format(self.name, self.side), asUtility=True)
        cmds.connectAttr(ikDistance + '.distance', stretchFactor + '.input1')
        cmds.setAttr(stretchFactor + '.input2', float(1 / maxStretch))

        # now we need a multiply node for each limb's length
        upLimbStretchedLength = cmds.shadingNode('multDoubleLinear', name='{0}_{1}_upLimbStretchFactor'.format(self.name, self.side), asUtility=True)
        cmds.connectAttr(stretchFactor + '.output', upLimbStretchedLength + '.input1')
        cmds.setAttr(upLimbStretchedLength + '.input2', upLimbLen)

        loLimbStretchedLength = cmds.shadingNode('multDoubleLinear', name='{0}_{1}_loLimbStretchFactor'.format(self.name, self.side), asUtility=True)
        cmds.connectAttr(stretchFactor + '.output', loLimbStretchedLength + '.input1')
        cmds.setAttr(loLimbStretchedLength + '.input2', loLimbLen)

        # connect that to the true value of our conditional
        cmds.connectAttr(upLimbStretchedLength + '.output', stretchCondition + '.colorIfTrueR')
        cmds.connectAttr(loLimbStretchedLength + '.output', stretchCondition + '.colorIfTrueG')
        
        # this is where we could make another multiply node for knee slide

        kneeSlideNode = cmds.shadingNode('multDoubleLinear', name='{0}_{1}_kneeSlideMultiplier'.format(self.name, self.side), asUtility=True)
        # add an attribute to the limb for controlling this
        cmds.addAttr(self.node, longName='kneeSlide', keyable=True, attributeType='float', defaultValue=1.0)
        cmds.connectAttr(self.node + '.kneeSlide', kneeSlideNode + '.input1')
        cmds.connectAttr(stretchCondition + '.outColorR', kneeSlideNode + '.input2')
        

        cmds.connectAttr(kneeSlideNode + '.output', '{0}.translate{1}'.format(self.ikDriveJoints[1], constants.DOWN_AXIS.upper()))
        cmds.connectAttr(stretchCondition + '.outColorG', '{0}.translate{1}'.format(self.ikDriveJoints[2], constants.DOWN_AXIS.upper()))


        # keep twist controls in their relative position by utilizing their
        # space groups

        for twistControl in self.upperTwistControls:
            cmds.pointConstraint(self.ikDriveJoints[0], self.ikDriveJoints[1], twistControl.spaceGrp, maintainOffset=True)
            
        for twistControl in self.lowerTwistControls:
            cmds.pointConstraint(self.ikDriveJoints[1], self.ikDriveJoints[2], twistControl.spaceGrp, maintainOffset=True)
        


