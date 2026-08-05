import maya.cmds as cmds

from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils, mathUtils
from bmaya.core import constants


class Foot(object):

    def __init__(
        self,
        name="Foot1",
        ankle=None,
        ball=None,
        heel=None,
        bankOut=None,
        bankIn=None,
        toeTip=None,
    ):

        self.name = name

        self.ankle = ankle
        self.heel = heel
        self.bankOut = bankOut
        self.bankIn = bankIn
        self.toeTip = toeTip
        self.ball = ball

    def build(self):
        # finds the joints that should belong in the chain
        self.footHierarchy = [
            self.heel,
            self.bankOut,
            self.bankIn,
            self.toeTip,
            self.ball,
        ]

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
            fkJnt = cmds.joint(name=jnt.replace(constants.JOINT_SUFFIX, "FOOTFK"))
            mathUtils.match_transforms(jnt, fkJnt)
            cmds.makeIdentity(fkJnt, apply=True, rotate=True)

            fkJoints.append(fkJnt)

        # orient joint chain x down y up

        return fkJoints

    def createIkHierarchy(self):
        ikJoints = []

        cmds.select(clear=True)
        for jnt in [self.ankle, self.ball, self.toeTip]:
            ikJnt = cmds.joint(name=jnt.replace(constants.JOINT_SUFFIX, "FOOTIK"))
            mathUtils.match_transforms(jnt, ikJnt)
            cmds.makeIdentity(ikJnt, apply=True, rotate=True)

            ikJoints.append(ikJnt)

        return ikJoints

    def createDriveHierarchy(self):
        driveJoints = []

        cmds.select(clear=True)
        for jnt in [self.ankle, self.ball, self.toeTip]:
            blendJnt = cmds.joint(name=jnt.replace(constants.JOINT_SUFFIX, "FOOTDRIVE"))
            mathUtils.match_transforms(jnt, blendJnt)
            cmds.makeIdentity(blendJnt, apply=True, rotate=True)

            driveJoints.append(blendJnt)

        return driveJoints

    def createReverseHierarchy(self):

        # create a reverse hierarchy of oriented joints

        reverseHierarchy = []

        cmds.select(clear=True)

        # the ballSwivel joint is unique because it doesn't have a supplied
        # joint
        ballSwivelName = ["ballSwivel"]
        ballSwivelName += self.footHierarchy[0].split("_")[1:]
        ballSwivelJnt = cmds.joint(name="_".join(ballSwivelName))
        cmds.delete(
            cmds.pointConstraint(self.ball, ballSwivelJnt, maintainOffset=False)
        )
        # project onto the groundplane
        cmds.setAttr(ballSwivelJnt + ".translateY", 0)
        cmds.setAttr(ballSwivelJnt + ".rotateOrder", 2)
        reverseHierarchy.append(ballSwivelJnt)

        i = 0

        for jnt in self.footHierarchy + [self.ankle]:
            revJnt = cmds.joint(name=jnt + "_Reverse")
            mathUtils.match_transforms(jnt, revJnt)
            cmds.makeIdentity(revJnt, apply=True, rotate=True)
            cmds.setAttr(revJnt + ".rotateOrder", 2)

            if i == 4:
                self.parent_constrain(revJnt, self.footHierarchy[i])

            reverseHierarchy.append(revJnt)

            i += 1

        cmds.select(clear=True)

        cmds.parent(reverseHierarchy[-3], self.driver_grp)

        return reverseHierarchy

    def createIkHandles(self):
        # create two single chain iks

        self.ankleToBallIk = cmds.ikHandle(
            startJoint=self.footIkDriveJoints[0],
            endEffector=self.footIkDriveJoints[1],
            name=self.name + "_ankleSCik",
            solver="ikSCsolver",
        )[0]

        self.ballToToeIk = cmds.ikHandle(
            startJoint=self.footIkDriveJoints[1],
            endEffector=self.footIkDriveJoints[2],
            name=self.name + "_ballSCik",
            solver="ikSCsolver",
        )[0]

        cmds.parent(self.ankleToBallIk, self.reverseHierarchy[-2])
        cmds.parent(self.ballToToeIk, self.reverseHierarchy[-3])

    def createIkControls(self):
        self.ballSwivelCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(self.reverseHierarchy[0]),
            jnt=self.reverseHierarchy[0],
            shapeType="circleArrow",
        )
        cmds.setAttr(self.heel + ".rotateOrder", 2)
        self.heelCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(self.heel),
            jnt=self.heel,
            shapeType="archedDoubleArrow",
        )
        self.toeTipCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(self.toeTip),
            jnt=self.toeTip,
            shapeType="archedDoubleArrow",
        )
        self.ballRollCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(self.ball, identifier="IK"),
            jnt=self.ball,
            shapeType="circleStick",
        )
        self.bankOutCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(self.bankOut),
            jnt=self.bankOut,
            shapeType="archedDoubleArrow",
        )
        self.bankInCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(self.bankIn),
            jnt=self.bankIn,
            shapeType="archedDoubleArrow",
        )

        cmds.parent(self.ballRollCtrl.offset_grp, self.toeTipCtrl.ctrl)
        cmds.parent(self.toeTipCtrl.offset_grp, self.bankInCtrl.ctrl)
        cmds.parent(self.bankInCtrl.offset_grp, self.bankOutCtrl.ctrl)
        cmds.parent(self.bankOutCtrl.offset_grp, self.heelCtrl.ctrl)
        cmds.parent(self.heelCtrl.offset_grp, self.ballSwivelCtrl.ctrl)

        self.parent_constrain(self.toeTipCtrl.ctrl, self.reverseHierarchy[-3])
        self.parent_constrain(self.ballRollCtrl.ctrl, self.reverseHierarchy[-2])

        return [
            self.ballSwivelCtrl,
            self.heelCtrl,
            self.toeTipCtrl,
            self.ballRollCtrl,
            self.bankOutCtrl,
            self.bankInCtrl,
        ]

    def createFkControls(self):
        jnt = self.footFkDriveJoints[1]

        ctrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(jnt, identifier="FK"),
            jnt=jnt,
            shapeType="cube",
        )
        self.parent_constrain(ctrl.ctrl, jnt, maintain_offset=False)

        return [ctrl]
