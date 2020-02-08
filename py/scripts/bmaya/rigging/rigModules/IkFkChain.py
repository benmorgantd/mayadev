import maya.cmds as cmds

from bmaya.rigging.Osiris.base import module
from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

from IkChain import IkChain
from FkChain import FkChain

# reload(IkChain)
# reload(FkChain)

reload(module)
reload(shapelib)


class IkFkChain(FkChain, IkChain):

    def __init__(self, startJoint=None, endJoint=None, name='IkFkChain1', character=None, 
                parent=None, mirror=False, upVector=[0,2,0], exclude=[]):

        IkChain.__init__(self, startJoint=startJoint, endJoint=endJoint, name=name, 
                        character=character, parent=parent, mirror=mirror, upVector=upVector, exclude=exclude)

        FkChain.__init__(self, startJoint=startJoint, endJoint=endJoint, name=name, 
                        character=character, parent=parent, mirror=mirror, shapeType='cube')

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        # build a single joint control on the given joint

        self.checkContract()

        self.bindJoints = self.findHierarchyJoints()

        self.buildFkIkSetup()

        self.components += self.ikComponents
        self.components += self.fkComponents

    def buildFkIkSetup(self):
        # need to feed it our specific drive joints
        self.ikDriveJoints = self.createDriveJoints(label='IKDRIVER', constrain=False)
        self.fkDriveJoints = self.createDriveJoints(label='FKDRIVER', constrain=False)

        self.ikComponents = self.buildIkControls(self.ikDriveJoints)

        self.fkComponents = self.buildFkControls(self.fkDriveJoints)

        # add an attribute for blending
        cmds.addAttr(self.node, longName='FKIK', attributeType='float', dv=0.0, 
                     min=0, max=1, keyable=True)

        self.blendReverse = self.blendChains(self.fkDriveJoints, self.ikDriveJoints, self.bindJoints, self.node + '.FKIK')

        # connect blend control to visibility
        cmds.connectAttr(self.blendReverse, '{0}.v'.format(self.fkComponents[0].offsetGrp))
        cmds.connectAttr(self.node + '.FKIK', '{0}.v'.format(self.ikComponents[0].offsetGrp))