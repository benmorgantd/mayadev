import maya.cmds as cmds

from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

import IkFkChain
import Ribbon

from bmaya.rigging.Osiris.tools import mathUtils


class Arm(IkFkChain.IkFkChain, Ribbon.Ribbon):

    def __init__(self, startJoint=None, endJoint=None, name='Arm1', character=None, 
                 parent=None, mirror=False, side='L', fkikDefault=0):

        IkFkChain.IkFkChain.__init__(self, startJoint=startJoint, endJoint=endJoint, name=name + '_ikFkChain', 
                                     character=character, parent=parent, mirror=mirror, side=side, fkikDefault=fkikDefault)
        
        Ribbon.Ribbon.__init__(self, startJoint=startJoint, endJoint=endJoint, 
                              name=name + '_upperRibbon', character=character, parent=parent, side=side, 
                              mirror=mirror, controlAmount=3, jointAmount=3, addDeformers=True)

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

        storedName = self.name
        storedBindJoints = self.bindJoints

        upperRibbonDict = self.buildRibbon(self.bindJoints[0], self.bindJoints[1], storedName + '_upperRibbon', twist=True, sine=False,
                                           identifier='Upper')
        # don't change bindJoint variable between instances!
        lowerRibbonDict = self.buildRibbon(self.bindJoints[1], self.bindJoints[2], storedName + '_lowerRibbon', twist=True, sine=False,
                                           identifier='Lower')
        self.bindJoints = storedBindJoints
        self.bindJoints += upperRibbonDict['bindJoints']
        self.bindJoints += lowerRibbonDict['bindJoints'][1:]

        self.ribbonDrivers = upperRibbonDict['driveControls'] + lowerRibbonDict['driveControls']
        self.ribbonFollowControls = upperRibbonDict['followControls'] + lowerRibbonDict['followControls']
        self.name = storedName

        self.setupDriverControlVisSwitch()

        self.setupLowerTwist()
        self.setupUpperTwist()
        self.addFkGimbalControl()

        # connect the ik wrist to the ik end joint
        cmds.orientConstraint(self.ikComponents[1].ctrl, self.ikDriveJoints[2], mo=1)

    def setupDriverControlVisSwitch(self):
        cmds.addAttr(self.node, longName='showDriverControls', attributeType='bool', keyable=True)

        for driverControl in self.ribbonDrivers:
            cmds.connectAttr(self.node + '.showDriverControls', driverControl.offsetGrp + '.v')

    def setupLowerTwist(self):
        # extract twist from start and end joint and connect it to the twistOffset variables

        # startQuat = mathUtils.setupQuatTwist(self.bindJoints[0], twistAxis='X')
        # cmds.connectAttr(startQuat + '.outputRotateX', self.node + '.UpperTwistStartOffset')

        endQuat = mathUtils.setupQuatTwist(self.driveJoints[2], twistAxis='X')
        cmds.connectAttr(endQuat + '.outputRotateX', self.node + '.LowerTwistEndOffset')

        # we need to negate the end result
        unitConversion = cmds.listConnections(endQuat + '.outputRotateX')[0]
        if self.side == 'L':
            cmds.setAttr(unitConversion + '.conversionFactor', -57.296)

    def setupUpperTwist(self):
        startTwistJoint, ikGrp = mathUtils.setupIkTwist(twistJoint=self.driveJoints[0], ikStartJoint=self.driveJoints[1], ikHandleParent=self.parent, twistJointParent=self.startJoint, name=self.name + 'upperTwist_' + self.side)
        cmds.connectAttr(startTwistJoint + '.rotateX', self.node + '.UpperTwistStartOffset')
        unitConversion = cmds.listConnections(startTwistJoint + '.rotateX')[0]
        if self.side == 'L':
            cmds.setAttr(unitConversion + '.conversionFactor', -57.296)

        cmds.parent(ikGrp, self.driverGrp)

    def addFkGimbalControl(self):
        # add a second control on top of the existing shoulder fk 
        # that has zxy (2) rotation order

        shoulderFkOffset = self.fkComponents[0].offsetGrp

        name = '{0}Gimbal_00_{1}_ctrl'.format(self.fkComponents[0].ctrl.split('_')[0], self.side)

        self.fkShoulderGimbal = shapelib.Shape(name=name, shapeType='sphere', jnt=shoulderFkOffset)

        # change its rotate order to zxy from that of the shoulder fk offset group
        cmds.setAttr(self.fkShoulderGimbal.ctrl + '.rotateOrder', 2)

        cmds.parent(self.fkShoulderGimbal.offsetGrp, self.componentsGrp, a=1)
        cmds.parent(self.fkComponents[0].offsetGrp, self.fkShoulderGimbal.ctrl, a=1)

        # hook it up to the visibility switch
        cmds.connectAttr(self.blendReverse, self.fkShoulderGimbal.offsetGrp + '.v')

        self.components.append(self.fkShoulderGimbal)