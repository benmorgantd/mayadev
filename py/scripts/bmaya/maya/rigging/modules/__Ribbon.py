import maya.cmds as cmds
import maya.api.OpenMaya as om

from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils, mathUtils


class Ribbon(module.Module):

    def __init__(
        self,
        start_joint=None,
        end_joint=None,
        controlAmount=3,
        name="Ribbon1",
        character=None,
        parent=None,
        side="L",
        mirror=False,
        addDeformers=True,
    ):
        super(Ribbon, self).__init__(
            mod_type="Ribbon", name=name, character=character, mirror=mirror, side=side
        )

        self.parent = parent
        self.start_joint = start_joint
        self.end_joint = end_joint

        self.controlAmount = controlAmount
        self.addDeformers = addDeformers

        if self.controlAmount < 2:
            raise ValueError("Ribbons must have at least 2 controls")

        self.contract = [self.start_joint, self.end_joint]

    @wrapBuild
    def build(self):

        self.bind_joints = self.find_hierarchy_joints(
            start_joint=self.start_joint,
            end_joint=self.end_joint,
            shortest_distance=True,
        )
        self.jointAmount = len(self.bind_joints)

        self.skinnedPlane = self.buildSkinnedPlane(self.start_joint, self.end_joint)
        if self.addDeformers:
            self.deformerPlane = self.buildDeformerPlane(
                self.start_joint, self.endJoint, self.skinnedPlane
            )
        self.followJoints = self.makeFollowJoints(self.skinnedPlane, self.start_joint)
        self.driveJoints = self.makeDriveJoints(self.skinnedPlane, self.start_joint)
        self.followControls = self.makeFollowJointControls(
            self.bind_joints, self.followJoints
        )
        self.skinDriverJointsToPlane(self.driveJoints, self.skinnedPlane)
        self.driveControls = self.makeDriverControls(self.start_joint, self.driveJoints)
        self.addVisibilitySwitches()

    def buildRibbon(
        self, start_joint, endJoint, name, twist=True, sine=False, identifier=""
    ):
        self.name = name
        bindJoints = self.find_hierarchy_joints(
            start_joint=start_joint, end_joint=endJoint, shortest_distance=True
        )
        self.jointAmount = len(bindJoints)
        skinnedPlane = self.buildSkinnedPlane(start_joint, endJoint)
        if self.addDeformers:
            deformerPlane = self.buildDeformerPlane(
                start_joint,
                endJoint,
                skinnedPlane,
                twist=twist,
                sine=sine,
                identifier=identifier,
            )
        followJoints = self.makeFollowJoints(skinnedPlane, start_joint, identifier)
        driveJoints = self.makeDriveJoints(skinnedPlane, start_joint, identifier)

        followControls = self.makeFollowJointControls(bindJoints, followJoints)
        self.skinDriverJointsToPlane(driveJoints, skinnedPlane)
        driveControls = self.makeDriverControls(start_joint, driveJoints)
        self.addVisibilitySwitches()

        attrDict = {
            "skinnedPlane": skinnedPlane,
            "followJoints": followJoints,
            "followControls": followControls,
            "bindJoints": bindJoints,
            "driveControls": driveControls,
        }
        return attrDict

    def buildSkinnedPlane(self, start_joint, endJoint):
        # we want the number of U patches to be the same as the joint amount.
        # This makes each joint sit in the center of a patch, which gives good
        # tangents
        skinnedPlane = cmds.nurbsPlane(
            name="{0}_{1}_skinnedPlane".format(self.name, self.side),
            pivot=(0, 0, 0),
            axis=(0, 1, 0),
            width=1,
            lengthRatio=1,
            patchesU=self.jointAmount,
            patchesV=1,
            degree=1,
            constructionHistory=False,
        )[0]

        cmds.parent(skinnedPlane, self.driver_grp)

        # align plane
        cmds.delete(cmds.pointConstraint(start_joint, endJoint, skinnedPlane, mo=0))
        cmds.delete(
            cmds.aimConstraint(
                endJoint,
                skinnedPlane,
                aimVector=[1, 0, 0],
                upVector=[0, 1, 0],
                worldUpType="None",
            )
        )

        start_jointPosition = om.MVector(
            *cmds.xform(start_joint, query=True, worldPosition=True, translation=True)
        )
        endJointPosition = om.MVector(
            *cmds.xform(start_joint, query=True, worldPosition=True, translation=True)
        )

        cmds.xform(
            skinnedPlane,
            scale=[start_jointPosition.length() - endJointPosition.length(), 1, 1],
        )

        cmds.makeIdentity(skinnedPlane, apply=True, t=1, r=1, s=1, pn=1)

        return skinnedPlane

    def buildDeformerPlane(
        self, start_joint, endJoint, skinnedPlane, twist=True, sine=True, identifier=""
    ):
        deformerPlane = cmds.duplicate(
            skinnedPlane,
            name="{0}{1}_{2}_deformerPlane".format(self.name, identifier, self.side),
        )[0]

        cmds.makeIdentity(deformerPlane, apply=True, t=1, r=1, s=1, pn=1)

        if twist:

            # TWIST deformer
            cmds.select(deformerPlane)
            twistDeformer, twistHandle = cmds.nonLinear(
                type="twist", name=deformerPlane + "_twistDef"
            )

            cmds.parent(twistHandle, self.driver_grp)

            cmds.delete(
                cmds.aimConstraint(
                    start_joint,
                    twistHandle,
                    mo=0,
                    aimVector=[0, -1, 0],
                    upVector=[1, 0, 0],
                    worldUpType="None",
                )
            )

            # module attribute names won't be unique if we're making multiple
            # ribbons on a parent module
            attrNames = {
                "twistStart": identifier + "TwistStart",
                "twistEnd": identifier + "TwistEnd",
                "twistStartOffset": identifier + "TwistStartOffset",
                "twistEndOffset": identifier + "TwistEndOffset",
            }

            cmds.addAttr(
                self.node,
                longName=attrNames["twistStart"],
                attributeType="float",
                keyable=True,
            )
            cmds.addAttr(
                self.node,
                longName=attrNames["twistEnd"],
                attributeType="float",
                keyable=True,
            )

            # full chain twist with offsets (for arms, forearms)

            cmds.addAttr(
                self.node,
                longName=attrNames["twistStartOffset"],
                attributeType="float",
                keyable=False,
            )
            cmds.addAttr(
                self.node,
                longName=attrNames["twistEndOffset"],
                attributeType="float",
                keyable=False,
            )

            startPma = cmds.shadingNode(
                "addDoubleLinear", asUtility=True, name=self.node + "_twistStartADL"
            )
            cmds.connectAttr(
                self.node + "." + attrNames["twistStart"], startPma + ".input1"
            )
            cmds.connectAttr(
                self.node + "." + attrNames["twistStartOffset"], startPma + ".input2"
            )

            endPma = cmds.shadingNode(
                "addDoubleLinear", asUtility=True, name=self.node + "_twistEndADL"
            )
            cmds.connectAttr(
                self.node + "." + attrNames["twistEnd"], endPma + ".input1"
            )
            cmds.connectAttr(
                self.node + "." + attrNames["twistEndOffset"], endPma + ".input2"
            )

            cmds.connectAttr(startPma + ".output", twistDeformer + ".startAngle")
            cmds.connectAttr(endPma + ".output", twistDeformer + ".endAngle")

            self.message_connect(
                self.node, twistDeformer, (identifier + "TwistDeformer"), "module"
            )

        if sine:
            # SINE deformer
            cmds.select(deformerPlane)

            sineDeformer, sineHandle = cmds.nonLinear(
                type="sine", name=deformerPlane + "_sineDef"
            )

            sineHandleGrp = cmds.group(empty=True, name=sineHandle + "_grp")
            mathUtils.match_transforms(sineHandle, sineHandleGrp)
            cmds.parent(sineHandleGrp, self.driver_grp)
            cmds.parent(sineHandle, sineHandleGrp)
            cmds.xform(sineHandle, scale=(1, 1, 1), absolute=True)
            dist = mathUtils.getDistance(start_joint, endJoint)
            cmds.xform(sineHandleGrp, scale=[(dist / 2.0), (dist / 2.0), (dist / 2.0)])
            # this rotation assumes an X down, Y up joint orientation
            cmds.xform(sineHandleGrp, rotation=(-90, 0, 90), r=1, os=1)

            cmds.addAttr(
                self.node, longName="sineAmplitude", attributeType="float", keyable=True
            )
            cmds.addAttr(
                self.node,
                longName="sineWavelength",
                attributeType="float",
                dv=1.0,
                keyable=True,
            )
            cmds.addAttr(
                self.node, longName="sineOffset", attributeType="float", keyable=True
            )
            cmds.addAttr(
                self.node, longName="sineSlide", attributeType="float", keyable=True
            )
            cmds.addAttr(
                self.node,
                longName="sineDropoff",
                attributeType="float",
                keyable=True,
                min=0,
                max=1,
            )

            cmds.connectAttr(self.node + ".sineAmplitude", sineDeformer + ".amplitude")
            cmds.connectAttr(
                self.node + ".sineWavelength", sineDeformer + ".wavelength"
            )
            cmds.connectAttr(self.node + ".sineOffset", sineDeformer + ".offset")
            cmds.connectAttr(self.node + ".sineDropoff", sineDeformer + ".dropoff")
            cmds.connectAttr(self.node + ".sineSlide", sineHandle + ".translateY")

        cmds.blendShape(deformerPlane, skinnedPlane, weight=[(0, 1)])

        return deformerPlane

    def makeFollowJoints(self, skinnedPlane, start_joint, identifier=""):

        followJoints = []
        self.followJointGrp = cmds.group(
            empty=True, name=self.name + identifier + "_followJoints"
        )
        cmds.parent(self.followJointGrp, self.components_grp)
        cmds.hide(self.followJointGrp)

        # the bind joints follow the ribbon, which is driven the drivers

        for i in range(self.jointAmount):
            cmds.select(cl=1)

            joint = cmds.joint(
                name=self.find_joint_name(
                    start_joint, identifier=identifier, count=i, suffix="FOLLOW"
                )
            )
            # we actually want the follow joints to be xyz rotate order
            cmds.setAttr(joint + ".rotateOrder", 0)

            infoNode = cmds.createNode(
                "pointOnSurfaceInfo", name=joint + "_POINTONSURFACE"
            )
            cmds.connectAttr(
                "{0}.worldSpace[0]".format(skinnedPlane), infoNode + ".inputSurface"
            )
            cmds.setAttr(infoNode + ".turnOnPercentage", 1)

            cmds.setAttr(infoNode + ".parameterV", 0.5)

            if i != 0:
                cmds.setAttr(
                    infoNode + ".parameterU", (1 / (float(self.jointAmount - 1)) * i)
                )
            else:
                cmds.setAttr(infoNode + ".parameterU", 0)

            # make a matrix rivot
            matrix4x4 = cmds.shadingNode(
                "fourByFourMatrix", name=joint + "_MAT4X4", asUtility=True
            )
            infoAttrs = [
                "normalizedNormal",
                "normalizedTangentU",
                "normalizedTangentV",
                "position",
            ]
            axis = ["X", "Y", "Z"]

            for j in range(4):
                for k in range(3):
                    cmds.connectAttr(
                        "{0}.{1}{2}".format(infoNode, infoAttrs[j], axis[k]),
                        "{0}.in{1}{2}".format(matrix4x4, j, k),
                    )

            # multiply the result of that matrix by the joint's parent inverse matrix.
            # this makes the joint follow the ribbon in world space
            multMatrix = cmds.shadingNode(
                "multMatrix", asUtility=True, name=joint + "_MULTMATRIX"
            )
            cmds.connectAttr(matrix4x4 + ".output", multMatrix + ".matrixIn[0]")
            cmds.connectAttr(
                joint + ".parentInverseMatrix[0]", multMatrix + ".matrixIn[1]"
            )

            decompMatrix = cmds.createNode("decomposeMatrix", name=joint + "_MATDECOMP")
            cmds.connectAttr(multMatrix + ".matrixSum", decompMatrix + ".inputMatrix")
            cmds.connectAttr(decompMatrix + ".outputTranslate", joint + ".translate")
            cmds.connectAttr(decompMatrix + ".outputRotate", joint + ".rotate")

            cmds.parent(joint, self.followJointGrp)

            followJoints.append(joint)

        return followJoints

    def makeDriveJoints(self, skinnedPlane, start_joint, identifier=""):

        driveJoints = []
        driverJointsGrp = cmds.group(empty=True, name=self.name + "_driverJoints")

        for i in range(self.controlAmount):
            cmds.select(cl=1)

            joint = cmds.joint(
                name=self.find_joint_name(
                    start_joint, identifier=identifier, count=i, suffix="DRIVER"
                )
            )
            # cmds.setAttr(joint + '.rotateOrder', 4)
            cmds.setAttr(joint + ".rotateOrder", 1)

            infoNode = cmds.createNode(
                "pointOnSurfaceInfo", name=joint + "_POINTONSURFACE"
            )
            cmds.connectAttr(
                "{0}.worldSpace[0]".format(skinnedPlane), infoNode + ".inputSurface"
            )
            cmds.setAttr(infoNode + ".turnOnPercentage", 1)

            cmds.setAttr(infoNode + ".parameterV", 0.5)

            if i != 0:
                cmds.setAttr(
                    infoNode + ".parameterU", (1 / (float(self.controlAmount - 1)) * i)
                )
            else:
                cmds.setAttr(infoNode + ".parameterU", 0)

            # make a matrix rivot
            matrix4x4 = cmds.shadingNode(
                "fourByFourMatrix", name=joint + "_MAT4X4", asUtility=True
            )
            infoAttrs = [
                "normalizedNormal",
                "normalizedTangentU",
                "normalizedTangentV",
                "position",
            ]
            axis = ["X", "Y", "Z"]

            for j in range(4):
                for k in range(3):
                    cmds.connectAttr(
                        "{0}.{1}{2}".format(infoNode, infoAttrs[j], axis[k]),
                        "{0}.in{1}{2}".format(matrix4x4, j, k),
                    )

            decompMatrix = cmds.createNode("decomposeMatrix", name=joint + "_MATDECOMP")
            cmds.connectAttr(matrix4x4 + ".output", decompMatrix + ".inputMatrix")

            # make orient and sdk groups
            jointPosition = cmds.xform(
                joint, query=True, translation=True, worldSpace=True
            )

            orientGrp = cmds.group(empty=True, name=joint + "_offset_grp")
            sdkGrp = cmds.group(empty=True, name=joint + "_sdkGrp")

            mathUtils.match_transforms(joint, orientGrp)
            mathUtils.match_transforms(joint, orientGrp)

            cmds.parent(joint, sdkGrp)
            cmds.parent(sdkGrp, orientGrp)
            cmds.parent(orientGrp, driverJointsGrp)

            axis = ["X", "Y", "Z"]

            for z in range(3):
                cmds.connectAttr(
                    decompMatrix + ".outputTranslate" + axis[z],
                    orientGrp + ".translate" + axis[z],
                )
                cmds.connectAttr(
                    decompMatrix + ".outputRotate" + axis[z],
                    orientGrp + ".rotate" + axis[z],
                )

                cmds.disconnectAttr(
                    decompMatrix + ".outputTranslate" + axis[z],
                    orientGrp + ".translate" + axis[z],
                )
                cmds.disconnectAttr(
                    decompMatrix + ".outputRotate" + axis[z],
                    orientGrp + ".rotate" + axis[z],
                )

            driveJoints.append(joint)

            cmds.delete(decompMatrix, matrix4x4, infoNode)

        cmds.parent(driverJointsGrp, self.driver_grp)

        # turn off inherit transform on driver group to get rid of double
        # xforms
        cmds.setAttr(self.driver_grp + ".inheritsTransform", 0)

        return driveJoints

    def makeFollowJointControls(self, bindJoints, followJoints):

        followJointControls = []

        self.followControlGrp = cmds.group(
            empty=True, name=self.name + "_followControls"
        )
        cmds.parent(self.followControlGrp, self.components_grp)

        for i in range(len(followJoints)):
            ctrl = shapelib.ControlCurve(
                name=nameUtils.find_control_name(followJoints[i], identifier="Follow"),
                shapeType="square",
                jnt=followJoints[i],
                scale=1.15,
            )

            cmds.parent(ctrl.offset_grp, self.followControlGrp)

            self.parent_constrain(
                followJoints[i], ctrl.offset_grp, maintain_offset=True
            )

            self.parent_constrain(ctrl.ctrl, bindJoints[i], maintain_offset=True)

            self.components.append(ctrl)

            followJointControls.append(ctrl)

        return followJointControls

    def skinDriverJointsToPlane(self, driveJoints, skinnedPlane):

        cmds.select(driveJoints)
        cmds.select(skinnedPlane, add=True)

        cstr = cmds.skinCluster(toSelectedBones=True, skinMethod=0, dropoffRate=3.0)[0]

        cmds.select(skinnedPlane)

        cmds.skinPercent(cstr, pruneWeights=0.05)

    def makeDriverControls(self, start_joint, driveJoints):

        driverControls = []

        driverControlGrp = cmds.group(empty=True, name=self.name + "_driverControls")
        cmds.parent(driverControlGrp, self.components_grp)

        for driveJnt in driveJoints:
            ctrl = shapelib.ControlCurve(
                name=nameUtils.find_control_name(driveJnt, identifier="Driver"),
                shapeType="cube",
                jnt=driveJnt,
            )

            cmds.parent(ctrl.offset_grp, self.components_grp)

            self.parent_constrain(
                ctrl.ctrl, driveJnt + "_offset_grp", maintain_offset=True
            )

            cmds.parent(ctrl.offset_grp, driverControlGrp)

            self.components.append(ctrl)

            driverControls.append(ctrl)

        self.parent_constrain(start_joint, driverControlGrp)

        return driverControls

    def addVisibilitySwitches(self):
        if "showFollowControls" not in cmds.listAttr(self.node):
            cmds.addAttr(
                self.node,
                longName="showFollowControls",
                attributeType="bool",
                keyable=True,
            )

        cmds.connectAttr(
            self.node + ".showFollowControls", self.followControlGrp + ".v"
        )

    def buildFkRibbonDriveControls(self, driveControls):

        fkDriveControls = []

        cmds.addAttr(self.node, longName="showFkDriverControls", dv=False, at="bool")

        for i in range(len(driveControls)):
            driveCtrl = driveControls[i]

            fkCtrl = shapelib.ControlCurve(
                name=nameUtils.find_control_name(driveCtrl.ctrl, identifier="FK"),
                jnt=driveCtrl.ctrl,
                shapeType="cube",
            )

            driveParent = cmds.listRelatives(driveCtrl.offset_grp, parent=True)[0]

            if i == 0:
                cmds.parent(fkCtrl.offset_grp, driveParent)
            else:
                cmds.parent(fkCtrl.offset_grp, fkDriveControls[i - 1].ctrl)

            cmds.parent(driveCtrl.offset_grp, fkCtrl.ctrl)

            fkDriveControls.append(fkCtrl)

        return fkDriveControls
