import maya.cmds as cmds

from bmaya.rigging.rigBuilder.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import name

import IkFkChain

from bmaya.rigging.rigBuilder.tools import mathUtils

class Arm(IkFkChain.IkFkChain):

    def __init__(self, startJoint=None, endJoint=None, name='Arm1', character=None, 
                 parent=None, mirror=False, side='L', fkikDefault=0, alignWorld=True):

        IkFkChain.IkFkChain.__init__(self, startJoint=startJoint, endJoint=endJoint, name=name + '_ikFkChain', 
                                     character=character, parent=parent, mirror=mirror, side=side, 
                                     fkikDefault=fkikDefault, alignWorld=alignWorld)
        
        self.modType = "Arm"

        self.contract = [self.startJoint, self.endJoint]


    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bindJoints = self.findHierarchyJoints(shortestDistance=True)
        self.driveJoints = self.createDriveJoints(label='DRIVER', constrain=True)

        # force the bind joint start and ends to zyx rotate order 
        cmds.setAttr(self.bindJoints[0] + '.rotateOrder', 5)
        cmds.setAttr(self.bindJoints[1] + '.rotateOrder', 0)
        cmds.setAttr(self.bindJoints[2] + '.rotateOrder', 5)

        self.buildFkIkSetup()

        self.components += self.ikComponents
        self.components += self.fkComponents

        self.setupUpperTwist()
        self.setupLowerTwist()
        
        self.addFkGimbalControl()

        # connect the ik wrist to the ik end joint
        cmds.orientConstraint(self.ikComponents[1].ctrl, self.ikDriveJoints[2], mo=1)

    def setupUpperTwist(self):
        self.upperTwistJoints = self.findTwistJoints(self.bindJoints[0])
        self.bindJoints += self.upperTwistJoints
        self.upperTwistControls = []

        upperTwistGrp = cmds.group(empty=True, name=self.name + 'upperTwistGrp')
        cmds.parent(upperTwistGrp, self.componentsGrp)

        for jnt in self.upperTwistJoints:
            driveJnt = self.createDriveJoint(jnt, label='DRIVER', constrain=True)
            self.driveJoints.append(driveJnt)
            ctrl = shapelib.Shape(name=name.findControlName(driveJnt), shapeType='cube', jnt=driveJnt)
            cmds.parent(ctrl.offsetGrp, upperTwistGrp)
            cmds.parentConstraint(self.driveJoints[0], ctrl.offsetGrp, maintainOffset=True)
            cmds.parentConstraint(ctrl.ctrl, driveJnt, maintainOffset=True)
            self.upperTwistControls.append(ctrl)

        startTwistJoint, ikGrp = mathUtils.setupIkTwist(twistJoint=self.driveJoints[0], ikStartJoint=self.driveJoints[1], ikHandleParent=self.parent, twistJointParent=self.startJoint, name=self.name + 'upperTwist_' + self.side)

        numTwistJoints = float(len(self.upperTwistJoints))

        j = int(numTwistJoints - 1)

        for i in range(int(numTwistJoints) - 1):
            md = cmds.shadingNode('multDoubleLinear', asUtility=True, name=self.upperTwistControls[i].ctrl + '_md')
            cmds.connectAttr(startTwistJoint + '.rotateX', md + '.input1')
            cmds.setAttr(md + '.input2', j / (numTwistJoints -1))
            cmds.connectAttr(md + '.output', self.upperTwistControls[i].spaceGrp + '.rotateX', force=True)

            j -= 1

        cmds.parent(ikGrp, self.driverGrp)

        cmds.addAttr(self.node, longName='upperTwistVisibility', attributeType='bool', keyable=True)
        cmds.connectAttr(self.node + '.upperTwistVisibility', upperTwistGrp + '.visibility')

        self.components += self.upperTwistControls

    def setupLowerTwist(self):
        self.lowerTwistJoints = self.findTwistJoints(self.bindJoints[1])
        self.bindJoints += self.lowerTwistJoints
        self.lowerTwistControls = []
        lowerTwistGrp = cmds.group(empty=True, name=self.name + 'lowerTwistGrp')
        cmds.parent(lowerTwistGrp, self.componentsGrp)

        for jnt in self.lowerTwistJoints:
            driveJnt = self.createDriveJoint(jnt, label='DRIVER', constrain=True)
            self.driveJoints.append(driveJnt)
            ctrl = shapelib.Shape(name=name.findControlName(driveJnt), shapeType='cube', jnt=driveJnt)
            cmds.parent(ctrl.offsetGrp, lowerTwistGrp)
            cmds.parentConstraint(self.driveJoints[1], ctrl.offsetGrp, maintainOffset=True)
            cmds.parentConstraint(ctrl.ctrl, driveJnt, maintainOffset=True)
            self.lowerTwistControls.append(ctrl)

        # extract twist from start and end joint and connect it to the twistOffset variables

        endQuat = mathUtils.setupQuatTwist(self.driveJoints[2], twistAxis='X')

        numTwistJoints = float(len(self.lowerTwistJoints))

        for i in range(1, int(numTwistJoints)):
            md = cmds.shadingNode('multDoubleLinear', asUtility=True, name=self.lowerTwistControls[i].ctrl + '_md')
            cmds.connectAttr(endQuat + '.outputRotateX', md + '.input1')
            cmds.setAttr(md + '.input2', i / (numTwistJoints -1))
            cmds.connectAttr(md + '.output', self.lowerTwistControls[i].spaceGrp + '.rotateX', force=True)

        cmds.addAttr(self.node, longName='lowerTwistVisibility', attributeType='bool', keyable=True)
        cmds.connectAttr(self.node + '.lowerTwistVisibility', lowerTwistGrp + '.visibility')

        self.components += self.lowerTwistControls

    def addFkGimbalControl(self):
        # add a second control on top of the existing shoulder fk 
        # that has zxy (2) rotation order

        shoulderFkOffset = self.fkComponents[0].offsetGrp

        ctrlName = name.findControlName(self.fkComponents[0].ctrl, identifier='Gimbal')
        self.fkShoulderGimbal = shapelib.Shape(name=ctrlName, shapeType='sphere', jnt=shoulderFkOffset)

        # change its rotate order to zxy from that of the shoulder fk offset group
        cmds.setAttr(self.fkShoulderGimbal.ctrl + '.rotateOrder', 2)

        cmds.parent(self.fkShoulderGimbal.offsetGrp, self.componentsGrp, a=1)
        cmds.parent(self.fkComponents[0].offsetGrp, self.fkShoulderGimbal.ctrl, a=1)

        # hook it up to the visibility switch
        cmds.connectAttr(self.blendReverse, self.fkShoulderGimbal.offsetGrp + '.v')

        self.components.append(self.fkShoulderGimbal)

