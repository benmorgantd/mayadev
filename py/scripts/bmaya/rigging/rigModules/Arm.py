import maya.cmds as cmds

from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

import IkFkChain
import Ribbon

from bmaya.rigging.Osiris.tools import mathUtils


class Arm(IkFkChain.IkFkChain, Ribbon.Ribbon):

    def __init__(self, startJoint=None, endJoint=None, name='Arm1', character=None, 
                 parent=None, mirror=False, addDeformers=False, side='L'):

        IkFkChain.IkFkChain.__init__(self, startJoint=startJoint, endJoint=endJoint, name=name + '_ikFkChain', 
                                     character=character, parent=parent, mirror=mirror)
        
        Ribbon.Ribbon.__init__(self, startJoint=startJoint, endJoint=endJoint, 
                              name=name + '_upperRibbon', character=character, parent=parent, side=side, 
                              mirror=mirror, addDeformers=addDeformers, controlAmount=3, jointAmount=4)

        self.contract = [self.startJoint, self.endJoint]


    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bindJoints = self.findHierarchyJoints(shortestDistance=True)

        self.buildFkIkSetup()

        self.components += self.ikComponents
        self.components += self.fkComponents

        storedName = self.name
        storedBindJoints = self.bindJoints

        upperRibbonDict = self.buildRibbon(self.bindJoints[0], self.bindJoints[1], storedName + '_upperRibbon', twist=True, sine=False,
                                           attrPrefix = 'upper')
        # don't change bindJoint variable between instances!
        lowerRibbonDict = self.buildRibbon(self.bindJoints[1], self.bindJoints[2], storedName + '_lowerRibbon', twist=True, sine=False,
                                           attrPrefix='lower')
        self.bindJoints = storedBindJoints
        self.bindJoints += upperRibbonDict['bindJoints']
        self.bindJoints += lowerRibbonDict['bindJoints'][1:]

        self.ribbonDrivers = upperRibbonDict['driveControls'] + lowerRibbonDict['driveControls']
        self.ribbonFollowControls = upperRibbonDict['followControls'] + lowerRibbonDict['followControls']
        self.name = storedName

        self.setupDriverControlVisSwitch()

        self.setupQuatTwist()

    
    def setupDriverControlVisSwitch(self):
        cmds.addAttr(self.node, longName='showDriverControls', attributeType='bool', keyable=True)

        for driverControl in self.ribbonDrivers:
            cmds.connectAttr(self.node + '.showDriverControls', driverControl.offsetGrp + '.v')

    def setupQuatTwist(self):
        # extract twist from start and end joint and connect it to the twistOffset variables

        startQuat = mathUtils.setupQuatTwist(self.bindJoints[0], twistAxis='X')
        cmds.connectAttr(startQuat + '.outputRotateX', self.node + '.upperTwistStartOffset')

        endQuat = mathUtils.setupQuatTwist(self.bindJoints[2], twistAxis='X')
        cmds.connectAttr(endQuat + '.outputRotateX', self.node + '.lowerTwistEndOffset')

        # we need to negate the end result
        unitConversion = cmds.listConnections(endQuat + '.outputRotateX')[0]
        cmds.setAttr(unitConversion + '.conversionFactor', -57.296)

        