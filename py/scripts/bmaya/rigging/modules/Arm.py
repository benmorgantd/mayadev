import maya.cmds as cmds

from bmaya.rigging.rigBuilder.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import name

import _ThreeJointIkFkTwist

from bmaya.rigging.rigBuilder.tools import mathUtils

class Arm(_ThreeJointIkFkTwist.ThreeJointIkFkTwist):

    def __init__(self, startJoint=None, endJoint=None, name='Arm1', character=None, 
                 parent=None, mirror=False, side='L', fkikDefault=0, alignWorld=True):

        _ThreeJointIkFkTwist.ThreeJointIkFkTwist.__init__(self, startJoint=startJoint, endJoint=endJoint, name=name + '_ikFkChain', 
                                                          character=character, parent=parent, mirror=mirror, side=side, 
                                                          fkikDefault=fkikDefault, alignWorld=alignWorld)
        
        self.modType = "Arm"

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        _ThreeJointIkFkTwist.ThreeJointIkFkTwist.build(self, self.startJoint, self.endJoint)

        self.addFkGimbalControl()

        self.setupAlignWorld(self.fkShoulderGimbal, defaultValue=self.alignWorld)

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

