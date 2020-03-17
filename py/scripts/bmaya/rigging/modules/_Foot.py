import maya.cmds as cmds 

from bmaya.rigging.shapes import shapelib
from bmaya.core import name, constants


class Foot(object):

    def __init__(self, name='Foot1', ankle=None, ball=None, heel=None, bankOut=None, bankIn=None, toeTip=None):

        self.name = name

        self.ankle = ankle
        self.heel = heel
        self.bankOut = bankOut
        self.bankIn = bankIn
        self.toeTip = toeTip
        self.ball = ball

    def build(self):
        # finds the joints that should belong in the chain
        self.footHierarchy = [self.heel, self.bankOut, self.bankIn, self.toeTip, self.ball]

        self.reverseHierarchy = self.createReverseHierarchy()

        self.footFkDriveJoints = self.createFkHierarchy()
        self.footIkDriveJoints = self.createIkHierarchy()
        self.footDriveJoints = self.createDriveHierarchy()

        self.createIkHandles()
        self.footIkComponents = self.createIkControls()
        self.footFkComponents = self.createFkControls()

        # delete the non-essential bind joints
        cmds.delete(self.heel, self.reverseHierarchy[0])
        self.reverseHierarchy = self.reverseHierarchy[-3:]

        self.footComponents = self.footIkComponents + self.footFkComponents

    def createFkHierarchy(self):

        fkJoints = []
        
        cmds.select(clear=True)
        for jnt in [self.ankle, self.ball, self.toeTip]:
            fkJnt = cmds.joint(name=jnt.replace(constants.JOINT_SUFFIX, 'FOOTFK'))
            cmds.delete(cmds.parentConstraint(jnt, fkJnt, maintainOffset=False))
            cmds.makeIdentity(fkJnt, apply=True, rotate=True)

            fkJoints.append(fkJnt)

        # orient joint chain x down y up

        return fkJoints

    def createIkHierarchy(self):
        ikJoints = []
        
        cmds.select(clear=True)
        for jnt in [self.ankle, self.ball, self.toeTip]:
            ikJnt = cmds.joint(name=jnt.replace(constants.JOINT_SUFFIX, 'FOOTIK'))
            cmds.delete(cmds.parentConstraint(jnt, ikJnt, maintainOffset=False))
            cmds.makeIdentity(ikJnt, apply=True, rotate=True)

            ikJoints.append(ikJnt)

        return ikJoints

    def createDriveHierarchy(self):
        driveJoints = []
        
        cmds.select(clear=True)
        for jnt in [self.ankle, self.ball, self.toeTip]:
            blendJnt = cmds.joint(name=jnt.replace(constants.JOINT_SUFFIX, 'FOOTDRIVE'))
            cmds.delete(cmds.parentConstraint(jnt, blendJnt, maintainOffset=False))
            cmds.makeIdentity(blendJnt, apply=True, rotate=True)

            driveJoints.append(blendJnt)

        return driveJoints

    def createReverseHierarchy(self):

        # create a reverse hierarchy of oriented joints

        reverseHierarchy = []

        cmds.select(clear=True)

        # the ballSwivel joint is unique because it doesn't have a supplied joint
        ballSwivelName = ['ballSwivel']
        ballSwivelName += self.footHierarchy[0].split('_')[1:]
        ballSwivelJnt = cmds.joint(name='_'.join(ballSwivelName))
        cmds.delete(cmds.pointConstraint(self.ball, ballSwivelJnt, maintainOffset=False))
        # project onto the groundplane
        cmds.setAttr(ballSwivelJnt + '.translateY', 0)
        cmds.setAttr(ballSwivelJnt + '.rotateOrder', 2)
        reverseHierarchy.append(ballSwivelJnt)

        i = 0

        for jnt in self.footHierarchy + [self.ankle]:
            revJnt = cmds.joint(name=jnt + '_Reverse')
            cmds.delete(cmds.parentConstraint(jnt, revJnt, maintainOffset=False))
            cmds.makeIdentity(revJnt, apply=True, rotate=True)
            cmds.setAttr(revJnt + '.rotateOrder', 2)
           
            if i == 4:
                cmds.parentConstraint(revJnt, self.footHierarchy[i], maintainOffset=True)

            reverseHierarchy.append(revJnt)

            i += 1

        cmds.select(clear=True)

        cmds.parent(reverseHierarchy[-3], self.driverGrp)

        return reverseHierarchy

    def createIkHandles(self):
        # create two single chain iks

        self.ankleToBallIk = cmds.ikHandle(startJoint=self.footIkDriveJoints[0], 
                                           endEffector=self.footIkDriveJoints[1],
                                           name=self.name + '_ankleSCik', solver='ikSCsolver')[0]

        self.ballToToeIk = cmds.ikHandle(startJoint=self.footIkDriveJoints[1], 
                                           endEffector=self.footIkDriveJoints[2],
                                           name=self.name + '_ballSCik', solver='ikSCsolver')[0]

        cmds.parent(self.ankleToBallIk, self.reverseHierarchy[-2])
        cmds.parent(self.ballToToeIk, self.reverseHierarchy[-3])
    
    def createIkControls(self):
        self.ballSwivelCtrl = shapelib.Shape(name=name.findControlName(self.reverseHierarchy[0]), jnt=self.reverseHierarchy[0], shapeType='circleArrow')
        cmds.setAttr(self.heel + '.rotateOrder', 2)
        self.heelCtrl = shapelib.Shape(name=name.findControlName(self.heel), jnt=self.heel, shapeType='archedDoubleArrow')
        self.toeTipCtrl = shapelib.Shape(name=name.findControlName(self.toeTip), jnt=self.toeTip, shapeType='archedDoubleArrow')
        self.ballRollCtrl = shapelib.Shape(name=name.findControlName(self.ball, identifier='IK'), jnt=self.ball, shapeType='circleStick')
        self.bankOutCtrl = shapelib.Shape(name=name.findControlName(self.bankOut), jnt=self.bankOut, shapeType='archedDoubleArrow')
        self.bankInCtrl = shapelib.Shape(name=name.findControlName(self.bankIn), jnt=self.bankIn, shapeType='archedDoubleArrow')

        cmds.parent(self.ballRollCtrl.offsetGrp, self.toeTipCtrl.ctrl)
        cmds.parent(self.toeTipCtrl.offsetGrp, self.bankInCtrl.ctrl)
        cmds.parent(self.bankInCtrl.offsetGrp, self.bankOutCtrl.ctrl)
        cmds.parent(self.bankOutCtrl.offsetGrp, self.heelCtrl.ctrl)
        cmds.parent(self.heelCtrl.offsetGrp, self.ballSwivelCtrl.ctrl)

        cmds.parentConstraint(self.toeTipCtrl.ctrl, self.reverseHierarchy[-3], maintainOffset=True)
        cmds.parentConstraint(self.ballRollCtrl.ctrl, self.reverseHierarchy[-2], maintainOffset=True)

        return [self.ballSwivelCtrl, self.heelCtrl, self.toeTipCtrl, self.ballRollCtrl, self.bankOutCtrl, self.bankInCtrl]

    def createFkControls(self):
        jnt = self.footFkDriveJoints[1]

        ctrl = shapelib.Shape(name=name.findControlName(jnt, identifier='FK'), jnt=jnt, shapeType='cube')
        cmds.parentConstraint(ctrl.ctrl, jnt, maintainOffset=False)

        return [ctrl]