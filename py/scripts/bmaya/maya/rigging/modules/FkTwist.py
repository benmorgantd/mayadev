import maya.cmds as cmds

from bmaya.maya.rigging.modules import FkChain
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.util import nameUtils, mathUtils
from bmaya.core import constants


class FkTwist(FkChain.FkChain):

    def __init__(self, startJoint=None, endJoint=None, exclude=[],
                 name='FkTwist1',
                 character=None, parent=None, shapeType='cube', mirror=False,
                 side='L',
                 alignWorld=False, twistAxis='X', exponent=1):

        FkChain.FkChain.__init__(self, name=name, character=character,
                                 shapeType=shapeType, mirror=mirror, side=side,
                                 alignWorld=alignWorld,
                                 startJoint=startJoint, endJoint=endJoint,
                                 exclude=exclude)

        self.twistAxis = twistAxis
        self.exponent = exponent
        self.modType = 'FkTwist'

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        self.buildFkTwist()

    def buildFkTwist(self):
        # finds the joints that should belong in the chain
        self.bindJoints = self.findHierarchyJoints(shortestDistance=True,
                                                   exclude=self.exclude)
        # create base and twist drive joints separately so the controls can be too
        self.twistJoints = self.findTwistJoints(self.bindJoints[0])

        if not self.twistJoints:
            raise ValueError(
                'You must give at least one twist joint to an FkTwist module')

        self.bindJoints += self.twistJoints

        self.driveJoints = self.createDriveJoints()

        self.components = self.buildFkControls(self.driveJoints,
                                               setupAlignWorld=True)
        endComp = self.components[1]
        self.components.append(endComp)
        self.components.pop(1)

        self.twistComponents = [comp for comp in self.components if
                                'Twist' in comp.ctrl]

        cmds.addAttr(self.node, longName='showTwistControls',
                     attributeType='bool', keyable=True)

        for comp in self.twistComponents:
            cmds.connectAttr(self.node + '.showTwistControls',
                             comp.offsetGrp + '.visibility')

        self.setupTwist()

    def setupTwist(self):
        """Setup the twist from the start of the chain"""

        # we already have controls built for the chain, so add offset groups 
        # to drive them

        endQuat = mathUtils.setupQuatTwist(self.driveJoints[1],
                                           twistAxis=self.twistAxis)

        for i in range(len(self.twistComponents)):
            ctrl = self.twistComponents[i].ctrl

            twistMult = cmds.shadingNode('multDL', asUtility=True,
                                         name=ctrl + '_twistMD')
            cmds.connectAttr(
                '{0}.outputRotate{1}'.format(endQuat, self.twistAxis),
                twistMult + '.input1')
            # so with one twist joint, this is 0.5, and with two it's 0.33
            curveX = (1 / float((len(self.twistComponents) + 1))) * (i + 1)
            # we are making a polynomial 
            curveValue = curveX ** self.exponent

            # add a new attribute to our node for controlling the twist value
            attrName = 'twist' + str(i).zfill(2)
            cmds.addAttr(self.node, attributeType='float',
                         defaultValue=curveValue,
                         longName=attrName, keyable=True)

            cmds.connectAttr('{0}.{1}'.format(self.node, attrName),
                             twistMult + '.input2')

            # add an extra offset group to hold the transform
            upperTwistGrp = cmds.group(empty=True,
                                       name=ctrl.replace(constants.CTRL_SUFFIX,
                                                         'upperTwist'))
            cmds.setAttr(upperTwistGrp + '.rotateOrder',
                         cmds.getAttr(ctrl + '.rotateOrder'))
            mathUtils.matchTransforms(self.twistComponents[i].offsetGrp,
                                      upperTwistGrp)
            cmds.parent(upperTwistGrp, cmds.listRelatives(ctrl, parent=True)[0])
            cmds.parent(ctrl, upperTwistGrp)

            cmds.connectAttr(twistMult + '.output',
                             '{0}.rotate{1}'.format(upperTwistGrp,
                                                    self.twistAxis))
