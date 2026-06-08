import maya.cmds as cmds

from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils, mathUtils

from . import _ThreeJointIkFkTwist
from . import _Foot


class Leg(_ThreeJointIkFkTwist.ThreeJointIkFkTwist, _Foot.Foot):

    def __init__(
        self,
        start_joint=None,
        ankle=None,
        ball=None,
        heel=None,
        bankOut=None,
        bankIn=None,
        toeTip=None,
        name="Leg1",
        character=None,
        parent=None,
        mirror=False,
        side="L",
    ):
        _ThreeJointIkFkTwist.ThreeJointIkFkTwist.__init__(
            self,
            start_joint=start_joint,
            endJoint=ankle,
            name=name + "_ikFkChain",
            character=character,
            parent=parent,
            mirror=mirror,
            side=side,
            fkikDefault=1,
            alignWorld=False,
        )

        _Foot.Foot.__init__(
            self,
            ankle=ankle,
            ball=ball,
            heel=heel,
            bankOut=bankOut,
            bankIn=bankIn,
            toeTip=toeTip,
            name=name + "_Foot",
        )

        self.modType = "Leg"

        self.contract = [
            self.start_joint,
            self.endJoint,
            self.ankle,
            self.ball,
            self.toeTip,
            self.bankOut,
            self.bankIn,
            self.heel,
        ]

    @wrapBuild
    def build(self):
        _ThreeJointIkFkTwist.ThreeJointIkFkTwist.build(
            self,
            self.start_joint,
            self.ankle,
            worldAimTarget=self.ball,
            downAxis="Y",
            upAxis="X",
            followWorld=1,
        )
        _Foot.Foot.build(self)

        self.components += self.footComponents

        self.blend_chains(
            self.footFkDriveJoints,
            self.footIkDriveJoints,
            self.footDriveJoints,
            self.node + ".FKIK",
        )

        cmds.parent(self.footIkDriveJoints[0], self.ikDriveJoints[2])
        cmds.parent(self.footFkDriveJoints[0], self.fkDriveJoints[2])
        cmds.parent(self.footDriveJoints[0], self.driverGrp)
        cmds.parent(self.footIkComponents[0].offset_grp, self.components_grp)
        cmds.parent(self.footFkComponents[0].offset_grp, self.fkComponents[-1].ctrl)

        self.parent_constrain(
            self.ikComponents[1].ctrl,
            self.footIkComponents[0].offset_grp,
            maintain_offset=True,
        )

        # remove parent constraint on the drive (leg) ankle and make its driver
        # the (foot) ankle
        for node in [
            self.driveJoints[2],
            self.ikHandleGrp,
            self.ball,
            self.ikDriveJoints[2],
        ]:
            cmds.delete(cmds.listRelatives(node, type="constraint"))

        self.parent_constrain(
            self.footDriveJoints[0], self.driveJoints[2], maintain_offset=True
        )
        self.parent_constrain(
            self.ballRollCtrl.ctrl, self.ikHandleGrp, maintain_offset=True
        )
        self.parent_constrain(self.footDriveJoints[1], self.ball, maintain_offset=True)

        # hook up fk and ik foot control visibility
        cmds.connectAttr(
            self.blendReverse, "{0}.v".format(self.footFkComponents[0].offset_grp)
        )
        cmds.connectAttr(
            self.node + ".FKIK", "{0}.v".format(self.footIkComponents[0].offset_grp)
        )

        self.addFkGimbalControl()
        self.setup_align_world(self.fkHipGimbal, default_value=self.align_world)

        self.addIkToeBend()

    def addFkGimbalControl(self):
        # add a second control on top of the existing leg fk
        # that has zxy (2) rotation order

        shoulderFkOffset = self.fkComponents[0].offset_grp

        ctrlName = nameUtils.find_control_name(
            self.fkComponents[0].ctrl, identifier="Gimbal"
        )
        self.fkHipGimbal = shapelib.ControlCurve(
            name=ctrlName, shapeType="sphere", jnt=shoulderFkOffset
        )

        # change its rotate order to zxy from that of the shoulder fk offset
        # group
        cmds.setAttr(self.fkHipGimbal.ctrl + ".rotateOrder", 2)

        cmds.parent(self.fkHipGimbal.offset_grp, self.components_grp, a=1)
        cmds.parent(self.fkComponents[0].offset_grp, self.fkHipGimbal.ctrl, a=1)

        # hook it up to the visibility switch
        cmds.connectAttr(self.blendReverse, self.fkHipGimbal.offset_grp + ".v")

        self.components.append(self.fkHipGimbal)

    def addIkToeBend(self):
        # create a group in the ik reverse hierarchy that's the parent of the
        # ball ik handle and has the pivot of the next joint in the hierarchy
        toeJntNameSplit = self.toeTip.split("_")
        ballIkGrpName = "{0}Wiggle_{1}_{2}_offset_grp".format(
            toeJntNameSplit[0], toeJntNameSplit[1], toeJntNameSplit[2]
        )

        ballIkGrp = cmds.group(empty=True, name=ballIkGrpName)

        mathUtils.match_transforms(self.reverseHierarchy[1], ballIkGrp)

        cmds.parent(ballIkGrp, self.reverseHierarchy[0])

        cmds.parent(self.ballToToeIk, ballIkGrp)

        self.toeBendCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(ballIkGrp), jnt=ballIkGrp, shapeType="cube"
        )
        cmds.parent(self.toeBendCtrl.offset_grp, self.toeTipCtrl.ctrl)
        self.parent_constrain(self.toeBendCtrl, ballIkGrp)
        self.components.append(self.toeBendCtrl)
