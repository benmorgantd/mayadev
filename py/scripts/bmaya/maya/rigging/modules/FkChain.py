import maya.cmds as cmds

from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.util import mathUtils, dgUtils, dagUtils


class FkChain(module.Module):

    def __init__(
        self,
        start_joint=None,
        end_joint=None,
        exclude=[],
        name="FkChain1",
        character=None,
        parent=None,
        shapeType="cube",
        mirror=False,
        side="L",
        alignWorld=False,
    ):

        module.Module.__init__(
            self,
            name=name,
            mod_type="FkChain",
            character=character,
            shape_type=shapeType,
            mirror=mirror,
            side=side,
            align_world=alignWorld,
        )

        self.parent = parent
        self.start_joint = start_joint
        # If no end_joint is given, the chain will expand through the dag
        # and trim itself at joints in the exclude list
        self.end_joint = end_joint
        self.exclude = exclude

        """
        Dynamic creation of this chain through to joint ends or between a start and end joint
        makes it difficult to say what the "bind joints" for an FkChain module will look like.
        T
        Therefore, we will allow the user to duplicate and parent guides for FkChain to create the hierarchy.
        """

        self.contract = [self.start_joint]

    @wrapBuild
    def build(self):
        # finds the joints that should belong in the chain
        self.bind_joints = self.find_hierarchy_joints(exclude=self.exclude)
        self.driveJoints = self.create_drive_joints()

        self.components = self.build_fk_controls(
            self.driveJoints, setup_align_world=True
        )

    def build_guides(self):
        """Guides and bind joints are tricky for this module because of the way it dynamically creates itself."""

        start_joint_guide = mathUtils.create_axis_visualizer(name=f'{self.name}_start_joint_GUIDE')
        dgUtils.set_metadata_value(start_joint_guide, 'guide', True)
        dgUtils.set_metadata_value(start_joint_guide, 'guide_module', self.name)
        dgUtils.set_metadata_value(start_joint_guide, 'guide_socket', 'start_joint')

        previous_guide = start_joint_guide

        for i in range(1, 3):
            guide = mathUtils.create_axis_visualizer(name=f'{self.name}_{i:02d}_GUIDE')
            dgUtils.set_metadata_value(guide, 'guide', True)
            dgUtils.set_metadata_value(guide, 'guide_module', self.name)
            dgUtils.set_metadata_value(guide, 'guide_socket', 'tree') # There's no good socket for FkChain
            cmds.parent(guide, previous_guide)
            cmds.setAttr(f'{guide}.translateX', i * 1)
            previous_guide = guide

        grp = cmds.group(start_joint_guide, name=f"{self.name}_GUIDES")
        dgUtils.set_metadata_value(grp, 'guides_group', self.name)

        self.bind_joint_guides['start_joint'] = start_joint_guide

        return grp

    def build_bind_joints(self):
        start_joint_guide = self.get_start_joint_guide()
        all_guides = self.get_all_joint_guides()

        # Map guide DAG paths to the newly created joints
        guide_to_joint = {}

        # 1. Create all joints at the correct locations, unparented
        for guide in all_guides:
            cmds.select(clear=True)
            joint_name = guide.replace("_GUIDE", "_JNT")
            if guide == start_joint_guide:
                joint_name = joint_name.replace('_start_joint_', '_00_')

            joint = cmds.joint(name=joint_name)

            dagUtils.match_transforms(joint, guide)
            guide_to_joint[guide] = joint

        # 2. Reconstruct the hierarchy based on the Maya DAG
        for guide in all_guides:
            parent_node = cmds.listRelatives(guide, parent=True)
            
            if parent_node:
                # If the guide's parent is also a guide, parent the corresponding joint
                parent_guide = parent_node[0]
                if parent_guide in guide_to_joint:
                    child_joint = guide_to_joint[guide]
                    parent_joint = guide_to_joint[parent_guide]
                    cmds.parent(child_joint, parent_joint)

        # TODO: freeze transformations, orient joint
        cmds.select(clear=True)