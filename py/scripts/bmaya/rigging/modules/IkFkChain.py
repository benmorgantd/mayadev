import maya.cmds as cmds

from bmaya.rigging.rigBuilder.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

import IkChain
import FkChain


class IkFkChain(FkChain.FkChain, IkChain.IkChain):

    def __init__(self, startJoint=None, endJoint=None, name='IkFkChain1', character=None, 
                parent=None, mirror=False, upVector=[0,2,0], exclude=[], side='L', fkikDefault=0,
                alignWorld=True):

        IkChain.IkChain.__init__(self, startJoint=startJoint, endJoint=endJoint, name=name, 
                         character=character, parent=parent, mirror=mirror, upVector=upVector,
                         exclude=exclude, side=side)

        FkChain.FkChain.__init__(self, startJoint=startJoint, endJoint=endJoint, name=name, 
                        character=character, parent=parent, mirror=mirror, shapeType='cube', side=side,
                        alignWorld=alignWorld)

        self.modType = "IkFkChain"
        self.contract = [self.startJoint, self.endJoint]
        self.fkikDefault = fkikDefault

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.bindJoints = self.findHierarchyJoints()
        self.driveJoints = self.createDriveJoints(label='DRIVER', constrain=True)

        self.buildFkIkSetup()

        self.components += self.ikComponents
        self.components += self.fkComponents

    def buildFkIkSetup(self, worldAimTarget=None):
        # need to feed it our specific drive joints
        self.ikDriveJoints = self.createDriveJoints(label='IKDRIVER', constrain=False)
        self.fkDriveJoints = self.createDriveJoints(label='FKDRIVER', constrain=False)

        self.ikComponents = self.buildIkControls(self.ikDriveJoints, worldAimTarget=worldAimTarget)
        self.fkComponents = self.buildFkControls(self.fkDriveJoints)

        # add an attribute for blending
        cmds.addAttr(self.node, longName='FKIK', attributeType='float', dv=self.fkikDefault, 
                     min=0, max=1, keyable=True)

        self.blendReverse = self.blendChains(self.fkDriveJoints, self.ikDriveJoints, self.driveJoints, self.node + '.FKIK')

        # connect blend control to visibility
        cmds.connectAttr(self.blendReverse, '{0}.v'.format(self.fkComponents[0].offsetGrp))
        cmds.connectAttr(self.node + '.FKIK', '{0}.v'.format(self.ikComponents[0].offsetGrp))
        cmds.connectAttr(self.node + '.FKIK', '{0}.v'.format(self.ikComponents[-1].offsetGrp))