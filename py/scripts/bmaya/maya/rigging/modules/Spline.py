# a spine is a ribbon that has attachments at both ends to other joints
# (the pelvis drives the parent of the start, the chest drives the parent of the end)
# it just takes a start and end joint

import maya.cmds as cmds

from bmaya.core import constants
from bmaya.maya.util import nameUtils, mathUtils

from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.rigging.base import module


class Spline(module.Module):
    def __init__(
        self,
        start_joint=None,
        end_joint=None,
        name="Spline1",
        character=None,
        side="M",
        mirror=False,
        parent=None,
        setupTwist=True,
        controlAmount=3,
        stretchy=True,
        startTwistParent=None,
        shapeType="cube",
    ):
        super(Spline, self).__init__(
            mod_type="Spline",
            name=name,
            character=character,
            mirror=mirror,
            side=side,
            shape_type=shapeType,
        )

        self.start_joint = start_joint
        self.end_joint = end_joint
        self.setupTwist = setupTwist
        self.controlAmount = controlAmount
        self.stretchy = stretchy
        self.startTwistParent = startTwistParent

        self.contract = [self.start_joint, self.end_joint]

    @wrapBuild
    def build(self):
        self.bind_joints = self.find_hierarchy_joints(
            start_joint=self.start_joint,
            end_joint=self.end_joint,
            shortest_distance=True,
        )

        self.fkDriveJoints = self.create_drive_joints(label="FKDRIVER", constrain=False)
        self.ikDriveJoints = self.create_drive_joints(label="IKDRIVER", constrain=False)
        self.driveJoints = self.create_drive_joints(label="DRIVER", constrain=True)

        self.fkComponents = self.build_fk_controls()
        self.ikComponents = self.buildIkControls()

        if self.setupTwist:
            self.setupAdvancedTwist()

        self.setupIkEndJoint()
        self.setupIkHierarchy()

        # add an attribute for blending
        cmds.addAttr(
            self.node,
            longName="FKIK",
            attributeType="float",
            dv=1,
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

        for ctrl in self.ikComponents:
            cmds.connectAttr(self.node + ".FKIK", "{0}.v".format(ctrl.offset_grp))

        self.components += self.fkComponents
        self.components += self.ikComponents

    def build_fk_controls(self):

        _components = []

        for i in range(len(self.fkDriveJoints)):
            jnt = self.fkDriveJoints[i]

            ctrl = shapelib.ControlCurve(
                name=nameUtils.find_control_name(jnt, identifier="Fk"),
                shapeType=self.shape_type,
                jnt=jnt,
            )

            _components.append(ctrl)

            self.parent_constrain(ctrl.ctrl, jnt, maintain_offset=True)

            if i == 0:
                cmds.parent(ctrl.offset_grp, self.components_grp)
            else:
                parentJoint = cmds.listRelatives(jnt, parent=True, type="joint")[0]
                parentCtrl = cmds.listConnections(parentJoint + ".driveCtrl")

                if parentCtrl:
                    cmds.parent(ctrl.offset_grp, parentCtrl[0])
                else:
                    cmds.parent(ctrl.offset_grp, _components[0].ctrl)

            cmds.addAttr(jnt, longName="driveCtrl", attributeType="message")
            cmds.addAttr(ctrl.ctrl, longName="driveJoint", attributeType="message")
            cmds.connectAttr(ctrl.ctrl + ".driveJoint", jnt + ".driveCtrl")

        return _components

    def buildIkControls(self):
        self.splineIkHandle, self.splineCurve = self.buildIkSpline()

        self.splineDriverJoints = self.buildSplineDriverJoints()

        cmds.hide(self.splineCurve, self.splineDriverJoints)

        # skin the driver joints to the curve
        cmds.skinCluster(self.splineDriverJoints, self.splineCurve, maximumInfluences=4)

        ikControls = []

        # build the controls
        for i in range(len(self.splineDriverJoints)):
            jnt = self.splineDriverJoints[i]

            ctrl = shapelib.ControlCurve(
                name=nameUtils.find_control_name(jnt, identifier="Ik"),
                shapeType=self.shape_type,
                jnt=jnt,
            )

            cmds.parent(ctrl.offset_grp, self.components_grp)
            self.parent_constrain(ctrl.ctrl, jnt, maintain_offset=True)

            if i == 0 and self.startTwistParent:
                self.parent_constrain(
                    self.startTwistParent, ctrl.offset_grp, maintain_offset=True
                )

            ikControls.append(ctrl)

        self.setupStretch()

        return ikControls

    def buildIkSpline(self):
        """Note that there will be some movement on the ikJoints after creating this.
        Having the blend maintain offset will help.
        """

        jntLocs = [cmds.xform(jnt, q=1, t=1, ws=1) for jnt in self.ikDriveJoints]

        splineCurve = mathUtils.fit_curve_to_points(jntLocs, name=self.name + "_spline")
        cmds.setAttr(splineCurve + ".inheritsTransform", False)

        # the end effector for the splineIKHandle is one joint too early?

        splineIkHandle = cmds.ikHandle(
            name=self.name + "_splineIkHandle",
            solver="ikSplineSolver",
            startJoint=self.ikDriveJoints[0],
            endEffector=self.ikDriveJoints[-1],
            curve=splineCurve,
            createCurve=False,
        )[0]

        if constants.SPINE_UP_AXIS == "Y":
            # special attribute values for making a y up spine
            # +y forward axis
            cmds.setAttr(splineIkHandle + ".dForwardAxis", 2)
            # +z up axis
            cmds.setAttr(splineIkHandle + ".dWorldUpAxis", 3)
            cmds.setAttr(splineIkHandle + ".dWorldUpVector", 0, 0, 1)
            cmds.setAttr(splineIkHandle + ".dWorldUpVectorEnd", 0, 0, 1)

        cmds.parent(splineCurve, splineIkHandle, self.components_grp)

        return [splineIkHandle, splineCurve]

    def setupStretch(self):

        # create a curveInfo node to track the current arc length of the curve
        curveShape = cmds.listRelatives(self.splineCurve, shapes=True)[0]
        curveInfo = cmds.createNode("curveInfo")
        cmds.connectAttr(curveShape + ".worldSpace[0]", curveInfo + ".inputCurve")

        # create a multiply divide node to track the stretch factor
        stretchFactor = cmds.shadingNode(
            "multDL", asUtility=True, name=self.name + "_stretchFactor"
        )
        cmds.connectAttr(curveInfo + ".arcLength", stretchFactor + ".input1")
        cmds.setAttr(
            stretchFactor + ".input2", 1 / float(cmds.getAttr(curveInfo + ".arcLength"))
        )

        for i in range(1, len(self.ikDriveJoints)):
            jnt = self.ikDriveJoints[i]

            # create a mdl for this joint's original length (default down axis
            # is x)
            lengthMultiplier = cmds.shadingNode(
                "multDL", asUtility=True, name=jnt + "_stretchMultiplier"
            )
            cmds.setAttr(
                lengthMultiplier + ".input1",
                cmds.getAttr("{0}.translate{1}".format(jnt, constants.SPINE_UP_AXIS)),
            )
            cmds.connectAttr(stretchFactor + ".output", lengthMultiplier + ".input2")

            cmds.connectAttr(
                lengthMultiplier + ".output",
                "{0}.translate{1}".format(jnt, constants.SPINE_UP_AXIS),
            )

    def buildSplineDriverJoints(self):

        # we could go on a variable here since this is essentially the number of
        # controls

        splineDriverJoints = []

        # use the forward vector of our start joint as the y axis value
        # start_jointMatrix = cmds.getAttr(self.start_joint + '.worldMatrix[0]')
        # forwardVector = om.MVector(*start_jointMatrix[4:7])

        for i in range(self.controlAmount):
            cmds.select(clear=True)

            # make a control at a percentage distance along the curve
            matrix = mathUtils.get_matrix_along_curve(
                self.splineCurve,
                i / float(self.controlAmount - 1),
                downAxis=constants.SPINE_UP_AXIS,
            )

            jnt = cmds.joint(
                name=nameUtils.find_joint_name(
                    self.bind_joints[0], count=i, suffix="CURVEDRIVER"
                )
            )

            if constants.SPINE_UP_AXIS == "X":
                cmds.setAttr(jnt + ".rotateOrder", 2)
            else:
                cmds.setAttr(jnt + ".rotateOrder", 3)

            cmds.xform(jnt, matrix=matrix, worldSpace=True)

            cmds.makeIdentity(jnt, apply=True)

            cmds.parent(jnt, self.components_grp)

            splineDriverJoints.append(jnt)

        return splineDriverJoints

    def setupAdvancedTwist(self):

        cmds.setAttr(self.splineIkHandle + ".dTwistControlEnable", True)
        # set world up to Object Rotation Up (Start, End)
        cmds.setAttr(self.splineIkHandle + ".dWorldUpType", 4)

        cmds.connectAttr(
            self.ikComponents[0].ctrl + ".worldMatrix[0]",
            self.splineIkHandle + ".dWorldUpMatrix",
        )
        cmds.connectAttr(
            self.ikComponents[-1].ctrl + ".worldMatrix[0]",
            self.splineIkHandle + ".dWorldUpMatrixEnd",
        )

    def setupIkEndJoint(self):
        """Create a joint at the end of the ik chain that serves as more of an fk-style control"""

        cmds.select(clear=True)
        jnt = cmds.joint(
            name=nameUtils.find_joint_name(
                self.ikDriveJoints[-1], count=len(self.ikDriveJoints), suffix="IKDRIVER"
            )
        )
        cmds.setAttr(
            jnt + ".rotateOrder", cmds.getAttr(self.ikDriveJoints[-1] + ".rotateOrder")
        )
        mathUtils.match_transforms(self.ikDriveJoints[-1], jnt)

        cmds.parent(jnt, self.ikDriveJoints[-2])
        self.parent_constrain(self.ikComponents[-1], jnt, maintain_offset=True)

        # just replace the end joint with this joint so when we setup the blend
        # it just works
        self.ikDriveJoints[-1] = jnt

    def setupIkHierarchy(self):
        """Make a simple switch to make the ik hierarchy behave like an fk one"""

        cmds.addAttr(
            self.node,
            longName="hybridIk",
            attributeType="bool",
            keyable=True,
            defaultValue=False,
        )

        for i in range(len(self.ikComponents) - 1):
            # TODO: blending for matrix constraint method
            const = cmds.parentConstraint(
                self.ikComponents[i].ctrl, self.ikComponents[i + 1].offset_grp, maintainOffset=False
            )[0]

            cmds.connectAttr(
                self.node + ".hybridIk",
                "{0}.{1}".format(
                    const,
                    cmds.parentConstraint(const, query=True, weightAliasList=True)[0],
                ),
            )

        # switch off the base ik's constraint with this if there is one
        if self.startTwistParent:
            rev = cmds.createNode("reverse", name=self.name + "_ikHybridReverse")
            cmds.connectAttr(self.node + ".hybridIk", rev + ".inputX")
            # get the parent constraint on the first ik component's offset
            # group
            const = cmds.ls(
                cmds.listRelatives(self.ikComponents[0].offset_grp, children=True),
                type="parentConstraint",
            )

            if const:
                # switch it off when we go into hybridIk mode
                cmds.connectAttr(
                    rev + ".outputX",
                    "{0}.{1}".format(
                        const[0],
                        cmds.parentConstraint(
                            const[0], query=True, weightAliasList=True
                        )[0],
                    ),
                )
