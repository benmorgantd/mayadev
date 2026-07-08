import maya.cmds as cmds

from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild

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
        return self._build_guide_chain()

    def build_bind_joints(self):
        return self._build_bind_joint_chain_from_guides()