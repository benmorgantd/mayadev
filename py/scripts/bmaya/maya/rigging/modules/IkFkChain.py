import maya.cmds as cmds

from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib

from . import IkChain
from . import FkChain


class IkFkChain(FkChain.FkChain, IkChain.IkChain):

    def __init__(
        self,
        start_joint=None,
        endJoint=None,
        name="IkFkChain1",
        character=None,
        parent=None,
        mirror=False,
        upVector=[0, 2, 0],
        exclude=[],
        side="L",
        fkikDefault=0,
        alignWorld=True,
    ):
        IkChain.IkChain.__init__(
            self,
            start_joint=start_joint,
            endJoint=endJoint,
            name=name,
            character=character,
            parent=parent,
            mirror=mirror,
            upVector=upVector,
            exclude=exclude,
            side=side,
        )

        FkChain.FkChain.__init__(
            self,
            start_joint=start_joint,
            endJoint=endJoint,
            name=name,
            character=character,
            parent=parent,
            mirror=mirror,
            shapeType="cube",
            side=side,
            alignWorld=alignWorld,
        )

        self.modType = "IkFkChain"
        self.contract = [self.start_joint, self.endJoint]
        self.fkikDefault = fkikDefault

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bindJoints = self.find_hierarchy_joints(
            shortest_distance=True, exclude=self.exclude
        )
        self.driveJoints = self.create_drive_joints(label="DRIVER", constrain=True)

        self.buildFkIkSetup()

        self.components += self.ikComponents
        self.components += self.fkComponents

    def buildFkIkSetup(
        self, worldAimTarget=None, downAxis="X", upAxis="Y", followWorld=True
    ):
        # need to feed it our specific drive joints
        self.ikDriveJoints = self.create_drive_joints(label="IKDRIVER", constrain=False)
        self.fkDriveJoints = self.create_drive_joints(label="FKDRIVER", constrain=False)

        self.ikComponents = self.buildIkControls(
            self.ikDriveJoints,
            worldAimTarget=worldAimTarget,
            downAxis=downAxis,
            upAxis=upAxis,
            followWorld=followWorld,
        )
        self.fkComponents = self.build_fk_controls(self.fkDriveJoints)

        # add an attribute for blending
        cmds.addAttr(
            self.node,
            longName="FKIK",
            attributeType="float",
            dv=self.fkikDefault,
            min=0,
            max=1,
            keyable=True,
        )

        self.blendReverse = self.blend_chains(
            self.fkDriveJoints,
            self.ikDriveJoints,
            self.driveJoints,
            self.node + ".FKIK",
        )

        # connect blend control to visibility
        cmds.connectAttr(
            self.blendReverse, "{0}.v".format(self.fkComponents[0].offset_grp)
        )
        cmds.connectAttr(
            self.node + ".FKIK", "{0}.v".format(self.ikComponents[0].offset_grp)
        )
        cmds.connectAttr(
            self.node + ".FKIK", "{0}.v".format(self.ikComponents[-1].offset_grp)
        )
