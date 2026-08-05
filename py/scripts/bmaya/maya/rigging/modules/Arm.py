import maya.cmds as cmds

from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils

from . import _ThreeJointIkFkTwist


class Arm(_ThreeJointIkFkTwist.ThreeJointIkFkTwist):

    def __init__(
        self,
        start_joint=None,
        end_joint=None,
        name="Arm1",
        character=None,
        parent=None,
        mirror=False,
        side="L",
        fkikDefault=0,
        alignWorld=True,
    ):
        _ThreeJointIkFkTwist.ThreeJointIkFkTwist.__init__(
            self,
            start_joint=start_joint,
            end_joint=end_joint,
            name=name + "_ikFkChain",
            character=character,
            parent=parent,
            mirror=mirror,
            side=side,
            fkikDefault=fkikDefault,
            alignWorld=alignWorld,
        )

        self.modType = "Arm"

        self.contract = [self.start_joint, self.end_joint]

    @wrapBuild
    def build(self):
        _ThreeJointIkFkTwist.ThreeJointIkFkTwist.build(
            self, self.start_joint, self.end_joint, followWorld=1
        )

        self.addFkGimbalControl()
        self.setup_align_world(self.fkShoulderGimbal, default_value=self.align_world)
        # TODO: there's no ikfk switch control

    def addFkGimbalControl(self):
        # add a second control on top of the existing shoulder fk
        # that has xyz (0) rotation order

        shoulderFkOffset = self.fkComponents[0].offset_grp

        ctrlName = nameUtils.find_control_name(
            self.fkComponents[0].ctrl, identifier="Gimbal"
        )
        self.fkShoulderGimbal = shapelib.ControlCurve(
            name=ctrlName, shapeType="sphere", jnt=shoulderFkOffset
        )

        # change its rotate order to zxy from that of the shoulder fk offset group
        # cmds.setAttr(self.fkShoulderGimbal.ctrl + '.rotateOrder', 0)

        cmds.parent(self.fkShoulderGimbal.offset_grp, self.components_grp, a=1)
        cmds.parent(self.fkComponents[0].offset_grp, self.fkShoulderGimbal.ctrl, a=1)

        # hook it up to the visibility switch
        cmds.connectAttr(self.blendReverse, self.fkShoulderGimbal.offset_grp + ".v")

        self.components.append(self.fkShoulderGimbal)

    def build_guides(self):
        return self._build_guide_chain()

    def build_bind_joints(self):
        return self._build_bind_joint_chain_from_guides()