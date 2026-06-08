import maya.cmds as cmds
import maya.api.OpenMaya as om

from bmaya.core import constants
from bmaya.maya.util import nameUtils, mathUtils
from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib


class IkChain(module.Module):

    def __init__(
        self,
        start_joint=None,
        endJoint=None,
        name="IkChain1",
        character=None,
        parent=None,
        mirror=False,
        upVector=[0, 2, 0],
        exclude=[],
        side="L",
    ):

        module.Module.__init__(
            self,
            mod_type="IkChain",
            name=name,
            character=character,
            shape_type="cube",
            mirror=mirror,
            side=side,
        )

        self.parent = parent
        self.start_joint = start_joint
        self.endJoint = endJoint
        self.upVector = upVector
        self.exclude = exclude

        self.contract = [self.start_joint, self.endJoint]

    @wrapBuild
    def build(self):
        # build a simple single chain ik system

        self.bindJoints = self.find_hierarchy_joints(
            shortest_distance=True, exclude=self.exclude
        )

        self.driveJoints = self.create_drive_joints()

        self.components = self.buildIkControls(self.driveJoints)

    def buildIkControls(
        self,
        driveJoints,
        worldAimTarget=None,
        downAxis="X",
        upAxis="Y",
        followWorld=True,
    ):
        # letting components be a local variable here so that we can use this
        # safer in child methods
        components = []

        startCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(driveJoints[0], identifier="Ik"),
            shapeType="cube",
            jnt=driveJoints[0],
        )

        if worldAimTarget:
            endCtrl = shapelib.ControlCurve(
                nameUtils.find_control_name(driveJoints[-1], identifier="Ik"),
                shapeType="cube",
            )

            worldAlignVector = om.MVector(
                *cmds.xform(
                    worldAimTarget, query=True, translation=True, worldSpace=True
                )
            )
            endCtrlVector = om.MVector(
                *cmds.xform(
                    self.driveJoints[-1], query=True, translation=True, worldSpace=True
                )
            )

            U = om.MVector(*constants.UNIT_VECTORS[constants.UP_AXIS])
            # V is our down axis
            V = (worldAlignVector - endCtrlVector).normal()
            W = (U ^ V).normal()
            V = (U ^ W).normal()

            if V * om.MVector(0, 0, 1) < 0:
                V *= -1.0

            # log.info('U: {0},{1},{2}'.format(U.x, U.y, U.z))
            # log.info('V: {0},{1},{2}'.format(V.x, V.y, V.z))
            # log.info('W: {0},{1},{2}'.format(W.x, W.y, W.z))

            pythonMatrixList = [
                V.x,
                V.y,
                V.z,
                0,
                U.x,
                U.y,
                U.z,
                0,
                W.x,
                W.y,
                W.z,
                0,
                endCtrlVector.x,
                endCtrlVector.y,
                endCtrlVector.z,
                1,
            ]

            mMatrix = om.MMatrix()

            om.MScriptUtil.createMatrixFromList(pythonMatrixList, mMatrix)

            if not downAxis:
                downAxis = constants.DOWN_AXIS
            if not upAxis:
                upAxis = constants.UP_AXIS

            # TODO: This isn't variable based on constants, it relies on args
            # coming donwn from the LEG module

            # make a matrix R so that R*M is a reordering of the rows of M
            if downAxis == "X" and upAxis == "Y":
                # x down y up
                R = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
            elif downAxis == "X" and upAxis == "Z":
                # x down z up
                R = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1]
            elif downAxis == "Y" and upAxis == "X":
                # y down x up
                R = [0, 1, 0, 0, 1, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1]
            elif downAxis == "Y" and upAxis == "Z":
                # y down z up
                R = [0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1]
            elif downAxis == "Z" and upAxis == "X":
                # z down x up
                R = [0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1]
            elif downAxis == "Z" and upAxis == "Y":
                # z down y up
                R = [0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1]
            else:
                # for when axis get set to the same value
                R = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

            reorderMatrix = om.MMatrix()
            om.MScriptUtil.createMatrixFromList(R, reorderMatrix)
            # reorder the initial matrix to use the desired down and up axis
            reorderedMatrix = reorderMatrix * mMatrix

            pythonMatrixList = list(
                om.MScriptUtil.getDoubleArrayItem(reorderedMatrix[i], j)
                for i in range(4)
                for j in range(4)
            )

            cmds.xform(endCtrl.offset_grp, matrix=pythonMatrixList)

        else:
            endCtrl = shapelib.ControlCurve(
                nameUtils.find_control_name(driveJoints[-1], identifier="Ik"),
                shapeType="cube",
                jnt=driveJoints[-1],
            )

        cmds.parent(endCtrl.offset_grp, startCtrl.ctrl)

        self.setupIkSpaces(endCtrl, defaultValue=followWorld)

        ik, ikGrp = self.make_ik_handle(
            start_joint=driveJoints[0],
            end_joint=driveJoints[-1],
            solver_type="ikRPsolver",
            name=self.name + "_ikHandle",
        )

        poleVectorCtrl = shapelib.ControlCurve(
            name=nameUtils.find_control_name(driveJoints[0], identifier="IkAim"),
            shapeType="sphere",
            jnt=driveJoints[-1],
        )
        shapelib.ControlCurve.draw_line(
            driveJoints[1] + "_pvLine",
            driveJoints[1],
            poleVectorCtrl.ctrl,
            startCtrl.offset_grp,
        )

        if len(driveJoints) < 3:
            cmds.xform(
                poleVectorCtrl.offset_grp,
                translation=self.upVector,
                relative=True,
                objectSpace=True,
            )
        else:
            cmds.xform(
                poleVectorCtrl.offset_grp,
                translation=mathUtils.find_pole_vector(driveJoints, scaleFactor=1.5),
                worldSpace=True,
            )
            cmds.xform(
                poleVectorCtrl.offset_grp,
                rotation=(0, 0, 0),
                absolute=1,
                worldSpace=True,
            )

        cmds.pointConstraint(
            endCtrl.ctrl, poleVectorCtrl.offset_grp, maintainOffset=True
        )
        cmds.poleVectorConstraint(poleVectorCtrl.ctrl, ik)

        self.setupIkSpaces(poleVectorCtrl, defaultValue=1)

        cmds.parent(ikGrp, self.mod_grp)

        components += [startCtrl, endCtrl, poleVectorCtrl]
        self.ikHandle = ik
        self.ikHandleGrp = ikGrp

        # connect the controls to the joints and effectors
        self.parent_constrain(startCtrl.ctrl, driveJoints[0])
        self.parent_constrain(endCtrl.ctrl, ikGrp)

        cmds.parent(poleVectorCtrl.offset_grp, self.components_grp)
        cmds.parent(startCtrl.offset_grp, self.components_grp)

        return components

    def setupIkSpaces(self, ikCtrl, defaultValue=1):
        # parent to world and add switch
        const = self.parent_constrain(constants.BOTTOM_LAYOUT_CONTROL, ikCtrl.space_grp)
        cmds.addAttr(
            ikCtrl.ctrl,
            longName="followWorld",
            defaultValue=defaultValue,
            attributeType="bool",
            keyable=True,
        )
        cmds.connectAttr(
            ikCtrl.ctrl + ".followWorld",
            "{0}.{1}W0".format(const, constants.BOTTOM_LAYOUT_CONTROL),
        )

        # check if there's a point constraint on the offset group
        poleVectorPointConstraint = cmds.ls(
            cmds.listRelatives(ikCtrl.offset_grp, children=True), type="pointConstraint"
        )

        if poleVectorPointConstraint:
            rev = cmds.createNode("reverse", name=self.name + "_worldFollowReverse")
            cmds.connectAttr(ikCtrl.ctrl + ".followWorld", rev + ".inputX")
            weights = cmds.pointConstraint(
                poleVectorPointConstraint[0], query=True, weightAliasList=True
            )
            cmds.connectAttr(
                rev + ".outputX",
                "{0}.{1}".format(poleVectorPointConstraint[0], weights[0]),
            )
