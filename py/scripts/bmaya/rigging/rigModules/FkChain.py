'''FkChain'''

import maya.cmds as cmds

from bmaya.rigging.Osiris.base import module
from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

reload(module)
reload(shapelib)


class FkChain(module.Module):

    def __init__(self, startJoint=None, endJoint=None, exclude=[], name='FkChain1',
                 character=None, parent=None, shapeType='cube'):
        super(FkChain, self).__init__(name=name, modType='FkChain',
                                      character=character, shapeType=shapeType)

        self.parent = parent
        self.startJoint = startJoint
        # If no endJoint is given, the chain will expand through the dag
        # and trim itself at joints in the exclude list
        self.endJoint = endJoint
        self.exclude = exclude

        self.contract = [self.startJoint]

    @wrapBuild
    def build(self):
        self.checkContract()

        # finds the joints that should belong in the chain
        self.bindJoints = self.findHierarchyJoints()

        self.driveJoints = self.createDriveJoints()

        self.buildFkControls()

        # parent the startJoint control to the module's parent
        if self.parent:
            self.parentConstrain(self.parent, self.componentsGrp, maintainOffset=True)

    def buildFkControls(self):

        for i in range(len(self.driveJoints)):
            
            jnt = self.driveJoints[i]

            ctrl = shapelib.Shape(jnt, self.shapeType, jnt=jnt)

            self.components.append(ctrl)

            self.parentConstrain(ctrl.ctrl, jnt, maintainOffset=True)

            if i == 0:
                cmds.parent(ctrl.offsetGrp, self.componentsGrp)
            else:
                parentJoint = cmds.listRelatives(
                    jnt, parent=True, type='joint')[0]
                parentCtrl = cmds.listConnections(parentJoint + '.driveCtrl')

                if parentCtrl:
                    cmds.parent(ctrl.offsetGrp, parentCtrl[0])
                else:
                    cmds.parent(ctrl.offsetGrp, self.components[0].ctrl)

            cmds.addAttr(jnt, longName='driveCtrl', attributeType='message')
            cmds.addAttr(ctrl.ctrl, longName='driveJoint', attributeType='message')
            cmds.connectAttr(ctrl.ctrl + '.driveJoint', jnt + '.driveCtrl')

