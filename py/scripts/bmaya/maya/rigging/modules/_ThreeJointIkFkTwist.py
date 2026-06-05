import maya.cmds as cmds

from bmaya3.maya.rigging.base.decorators import wrapBuild
from bmaya3.maya.rigging.shapes import shapelib
from bmaya3.maya.util import nameUtils, mathUtils
from bmaya3.core import constants


from . import IkFkChain


class ThreeJointIkFkTwist(IkFkChain.IkFkChain):
    def __init__(self, startJoint=None, endJoint=None,
                 name='ThreeJointIkFkTwist1', character=None,
                 parent=None, mirror=False, side='L', fkikDefault=0,
                 alignWorld=True):

        IkFkChain.IkFkChain.__init__(self, startJoint=startJoint,
                                     endJoint=endJoint,
                                     name=name + '_ikFkChain',
                                     character=character, parent=parent,
                                     mirror=mirror, side=side,
                                     fkikDefault=fkikDefault,
                                     alignWorld=alignWorld)

        self.modType = "ThreeJointIkFkTwist"
        self.contract = [self.startJoint, self.endJoint]

    def build(self, startJoint, endJoint, worldAimTarget=None, downAxis='X',
              upAxis='Y', followWorld=True):
        self.bindJoints = self.findHierarchyJoints(shortestDistance=True,
                                                   startJoint=startJoint,
                                                   endJoint=endJoint)

        # # force the bind joint start and ends to zyx rotate order 
        # cmds.setAttr(self.bindJoints[0] + '.rotateOrder', 5)
        # cmds.setAttr(self.bindJoints[1] + '.rotateOrder', 0)
        # cmds.setAttr(self.bindJoints[2] + '.rotateOrder', 5)

        self.driveJoints = self.createDriveJoints(label='DRIVER',
                                                  constrain=True)

        self.buildFkIkSetup(worldAimTarget=worldAimTarget, downAxis=downAxis,
                            upAxis=upAxis, followWorld=followWorld)

        self.components += self.ikComponents
        self.components += self.fkComponents

        self.setupUpperTwist()
        self.setupLowerTwist()
        self.addStretchySetup()

        # connect the ik wrist to the ik end joint
        cmds.orientConstraint(self.ikComponents[1].ctrl, self.ikDriveJoints[2],
                              mo=1)

    def setupUpperTwist(self):
        self.upperTwistJoints = self.findTwistJoints(self.bindJoints[0])
        self.bindJoints += self.upperTwistJoints
        self.upperTwistControls = []

        upperTwistGrp = cmds.group(empty=True, name=self.name + 'upperTwistGrp')
        cmds.parent(upperTwistGrp, self.componentsGrp)

        for jnt in self.upperTwistJoints:
            driveJnt = self.createDriveJoint(jnt, label='DRIVER',
                                             constrain=True)
            self.driveJoints.append(driveJnt)
            ctrl = shapelib.ControlCurve(name=nameUtils.findControlName(driveJnt),
                                         shapeType='cube', jnt=driveJnt)
            cmds.parent(ctrl.offsetGrp, upperTwistGrp)
            self.parentConstrain(self.driveJoints[0], ctrl.offsetGrp,
                                 maintainOffset=True)
            self.parentConstrain(ctrl.ctrl, driveJnt, maintainOffset=True)
            self.upperTwistControls.append(ctrl)

        startTwistJoint, ikGrp = mathUtils.setupIkTwist(
            twistJoint=self.driveJoints[0], ikStartJoint=self.driveJoints[1],
            ikHandleParent=self.parent, twistJointParent=self.startJoint,
            name=self.name + 'upperTwist_' + self.side)

        numTwistJoints = float(len(self.upperTwistJoints))

        j = int(numTwistJoints - 1)

        for i in range(int(numTwistJoints) - 1):
            md = cmds.shadingNode('multDL', asUtility=True,
                                  name=self.upperTwistControls[i].ctrl + '_md')
            cmds.connectAttr(startTwistJoint + '.rotateX', md + '.input1')
            cmds.setAttr(md + '.input2', j / (numTwistJoints - 1))
            cmds.connectAttr(md + '.output',
                             self.upperTwistControls[i].spaceGrp + '.rotateX',
                             force=True)

            j -= 1

        cmds.parent(ikGrp, self.driverGrp)

        cmds.addAttr(self.node, longName='upperTwistVisibility',
                     attributeType='bool', keyable=True)
        cmds.connectAttr(self.node + '.upperTwistVisibility',
                         upperTwistGrp + '.visibility')

        self.components += self.upperTwistControls

    def setupLowerTwist(self):
        self.lowerTwistJoints = self.findTwistJoints(self.bindJoints[1])
        self.bindJoints += self.lowerTwistJoints
        self.lowerTwistControls = []
        lowerTwistGrp = cmds.group(empty=True, name=self.name + 'lowerTwistGrp')
        cmds.parent(lowerTwistGrp, self.componentsGrp)

        for jnt in self.lowerTwistJoints:
            driveJnt = self.createDriveJoint(jnt, label='DRIVER',
                                             constrain=True)
            self.driveJoints.append(driveJnt)
            ctrl = shapelib.ControlCurve(name=nameUtils.findControlName(driveJnt),
                                         shapeType='cube', jnt=driveJnt)
            cmds.parent(ctrl.offsetGrp, lowerTwistGrp)
            self.parentConstrain(self.driveJoints[1], ctrl.offsetGrp,
                                 maintainOffset=True)
            self.parentConstrain(ctrl.ctrl, driveJnt, maintainOffset=True)
            self.lowerTwistControls.append(ctrl)

        # extract twist from start and end joint and connect it to the twistOffset variables

        endQuat = mathUtils.setupQuatTwist(self.driveJoints[2], twistAxis='X')

        numTwistJoints = float(len(self.lowerTwistJoints))

        for i in range(1, int(numTwistJoints)):
            md = cmds.shadingNode('multDL', asUtility=True,
                                  name=self.lowerTwistControls[i].ctrl + '_md')
            cmds.connectAttr(endQuat + '.outputRotateX', md + '.input1')
            cmds.setAttr(md + '.input2', i / (numTwistJoints - 1))
            cmds.connectAttr(md + '.output',
                             self.lowerTwistControls[i].spaceGrp + '.rotateX',
                             force=True)

        cmds.addAttr(self.node, longName='lowerTwistVisibility',
                     attributeType='bool', keyable=True)
        cmds.connectAttr(self.node + '.lowerTwistVisibility',
                         lowerTwistGrp + '.visibility')

        self.components += self.lowerTwistControls

    def addStretchySetup(self):
        """Build a simple stretchy limb setup"""

        # get starting length of upper and lower ik limbs
        upLimbLen = cmds.getAttr(
            '{0}.translate{1}'.format(self.ikDriveJoints[1],
                                      constants.DOWN_AXIS.upper()))
        loLimbLen = cmds.getAttr(
            '{0}.translate{1}'.format(self.ikDriveJoints[2],
                                      constants.DOWN_AXIS.upper()))

        maxStretch = abs(upLimbLen) + abs(loLimbLen)

        # create a distanceBetween node to track the distance between the upper
        # and lower ik controls
        ikDistance = cmds.createNode('distanceBetween',
                                     name='{0}_{1}_legIkLength'.format(
                                         self.name, self.side))
        cmds.connectAttr(self.ikComponents[0].ctrl + '.worldMatrix[0]',
                         ikDistance + '.inMatrix1')
        cmds.connectAttr(self.ikComponents[1].ctrl + '.worldMatrix[0]',
                         ikDistance + '.inMatrix2')

        # create a condition node to track if we're stretching
        stretchCondition = cmds.createNode('condition',
                                           name='{0}_{1}_ikStretchCondition'.format(
                                               self.name, self.side))

        # connect that distance to the first term of our conditional
        cmds.connectAttr(ikDistance + '.distance',
                         stretchCondition + '.firstTerm')

        # the second term should be maxStretch
        cmds.setAttr(stretchCondition + '.secondTerm', maxStretch)

        # if greater than
        cmds.setAttr(stretchCondition + '.operation', 2)

        # false conditions are the initial down axis values for the limbs
        cmds.setAttr(stretchCondition + '.colorIfFalseR', upLimbLen)
        cmds.setAttr(stretchCondition + '.colorIfFalseG', loLimbLen)

        # true conditions are the amount we're stretching times the starting
        # lengths

        # we need a multiply node to find that out
        stretchFactor = cmds.shadingNode('multDL',
                                         name='{0}_{1}_stretchFactor'.format(
                                             self.name, self.side),
                                         asUtility=True)
        cmds.connectAttr(ikDistance + '.distance', stretchFactor + '.input1')
        cmds.setAttr(stretchFactor + '.input2', float(1 / maxStretch))

        # now we need a multiply node for each limb's length
        upLimbStretchedLength = cmds.shadingNode('multDL',
                                                 name='{0}_{1}_upLimbStretchFactor'.format(
                                                     self.name, self.side),
                                                 asUtility=True)
        cmds.connectAttr(stretchFactor + '.output',
                         upLimbStretchedLength + '.input1')
        cmds.setAttr(upLimbStretchedLength + '.input2', upLimbLen)

        loLimbStretchedLength = cmds.shadingNode('multDL',
                                                 name='{0}_{1}_loLimbStretchFactor'.format(
                                                     self.name, self.side),
                                                 asUtility=True)
        cmds.connectAttr(stretchFactor + '.output',
                         loLimbStretchedLength + '.input1')
        cmds.setAttr(loLimbStretchedLength + '.input2', loLimbLen)

        # connect that to the true value of our conditional
        cmds.connectAttr(upLimbStretchedLength + '.output',
                         stretchCondition + '.colorIfTrueR')
        cmds.connectAttr(loLimbStretchedLength + '.output',
                         stretchCondition + '.colorIfTrueG')

        # make another multiply node for controlling the length of the upper leg

        upLimbLength = cmds.createNode('multiplyDivide',
                                       name='{0}_{1}_upLimbLengthMultiplier'.format(
                                           self.name, self.side))
        # add an attribute to the limb for controlling this
        cmds.addAttr(self.node, longName='upLimbLength', keyable=True,
                     attributeType='float', defaultValue=1.0)
        cmds.connectAttr(self.node + '.upLimbLength', upLimbLength + '.input1X')
        cmds.connectAttr(stretchCondition + '.outColorR',
                         upLimbLength + '.input2X')
        # if stretch is off, multiply the value by the default limb length instead
        cmds.setAttr(upLimbLength + '.input1Y', upLimbLen)
        cmds.connectAttr(self.node + '.upLimbLength', upLimbLength + '.input2Y')

        # create a conditional that'll allow us to turn off stretch for the limb
        stretchSwitchConditition = cmds.createNode('condition',
                                                   name='{0}_{1}_ikStretchSwitchCondition'.format(
                                                       self.name, self.side))
        cmds.addAttr(self.node, longName='stretchyLimb', keyable=True,
                     attributeType='bool', defaultValue=True)
        cmds.connectAttr(self.node + '.stretchyLimb',
                         stretchSwitchConditition + '.firstTerm')
        cmds.setAttr(stretchSwitchConditition + '.secondTerm', 1)
        # if equal to 1, use the values computer before. Otherwise use default
        # limb lengths
        cmds.setAttr(stretchSwitchConditition + '.operation', 0)
        cmds.connectAttr(upLimbLength + '.outputX',
                         stretchSwitchConditition + '.colorIfTrueR')
        cmds.connectAttr(stretchCondition + '.outColorG',
                         stretchSwitchConditition + '.colorIfTrueG')
        # the first stretch conditional will keep that value not stretchy
        cmds.connectAttr(upLimbLength + '.outputY',
                         stretchSwitchConditition + '.colorIfFalseR')
        cmds.connectAttr(stretchCondition + '.colorIfFalseG',
                         stretchSwitchConditition + '.colorIfFalseG')

        cmds.connectAttr(stretchSwitchConditition + '.outColorR',
                         '{0}.translate{1}'.format(self.ikDriveJoints[1],
                                                   constants.DOWN_AXIS.upper()))
        cmds.connectAttr(stretchSwitchConditition + '.outColorG',
                         '{0}.translate{1}'.format(self.ikDriveJoints[2],
                                                   constants.DOWN_AXIS.upper()))

        # keep twist controls in their relative position by utilizing their
        # space groups

        for twistControl in self.upperTwistControls:
            const = cmds.pointConstraint(self.ikDriveJoints[0],
                                         self.ikDriveJoints[1],
                                         twistControl.spaceGrp,
                                         maintainOffset=True)
            weights = cmds.pointConstraint(const[0], query=True,
                                           weightAliasList=True)
            for w in weights:
                cmds.connectAttr(self.node + '.FKIK',
                                 '{0}.{1}'.format(const[0], w))

        for twistControl in self.lowerTwistControls:
            const = cmds.pointConstraint(self.ikDriveJoints[1],
                                         self.ikDriveJoints[2],
                                         twistControl.spaceGrp,
                                         maintainOffset=True)
            weights = cmds.pointConstraint(const[0], query=True,
                                           weightAliasList=True)
            for w in weights:
                cmds.connectAttr(self.node + '.FKIK',
                                 '{0}.{1}'.format(const[0], w))
