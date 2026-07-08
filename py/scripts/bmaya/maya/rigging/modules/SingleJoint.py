import maya.cmds as cmds

from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils, mathUtils, dgUtils, dagUtils


class SingleJoint(module.Module):

    def __init__(
        self,
        start_joint=None,
        name="singleJoint1",
        character=None,
        parent=None,
        shapeType="cube",
        mirror=False,
        side="L",
        alignWorld=None,
        addOffsetControl=False,
        offsetShapeType="cube",
    ):
        super(SingleJoint, self).__init__(
            mod_type="SingleJoint",
            name=name,
            character=character,
            shape_type=shapeType,
            mirror=mirror,
            side=side,
            align_world=alignWorld,
        )

        self.parent = parent
        self.start_joint = start_joint

        self.addOffsetControl = addOffsetControl
        self.offsetShapeType = offsetShapeType

        self.contract = [self.start_joint]

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bind_joints.append(self.start_joint)

        self.driveJoints = self.create_drive_joints()

        self.start_jointDriver = self.get_driver(self.start_joint)

        ctrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(self.start_jointDriver),
            shapeType=self.shape_type,
            jnt=self.start_jointDriver,
        )

        self.components.append(ctrl)

        if self.addOffsetControl:
            offsetCtrl = shapelib.ControlCurve(
                name=nameUtils.find_control_name(
                    self.start_jointDriver, identifier="Offset"
                ),
                shapeType=self.offsetShapeType,
                jnt=self.start_jointDriver,
            )
            cmds.parent(offsetCtrl.offset_grp, ctrl.ctrl)
            self.parent_constrain(
                offsetCtrl.ctrl, self.start_jointDriver, maintain_offset=True
            )
            self.components.append(offsetCtrl)
        else:
            self.parent_constrain(
                ctrl.ctrl, self.start_jointDriver, maintain_offset=True
            )

        cmds.parent(ctrl.offset_grp, self.components_grp)

        self.setup_align_world(ctrl, default_value=self.align_world)
    
    def build_guides(self):
        """Create a joint creation rig for this module"""
        start_joint_guide = mathUtils.create_axis_visualizer(name=f'{self.name}_start_joint_GUIDE')
        dgUtils.set_metadata_value(start_joint_guide, 'guide', True)
        dgUtils.set_metadata_value(start_joint_guide, 'guide_module', self.name)
        dgUtils.set_metadata_value(start_joint_guide, 'guide_socket', 'start_joint')

        grp = cmds.group(start_joint_guide, name=f"{self.name}_GUIDES")
        dgUtils.set_metadata_value(grp, 'guides_group', self.name)

        self.bind_joint_guides['start_joint'] = start_joint_guide

        return grp

    def build_bind_joints(self):
        # TODO: this would be a lot more convenient if we weren't reliant on tagging
        start_joint = cmds.joint(name=f'{self.name}_00_{self.side}_JNT')

        # Match tranforms
        dagUtils.match_transforms(start_joint, self.get_start_joint_guide())

        # TODO: manage parenting. 
        # For now, all module bind joints will get created floating, and parenting will have to be done manually.

        cmds.select(clear=True)