import maya.cmds as cmds 

from bmaya.rigging.rigBuilder.base import module
from bmaya.rigging.rigBuilder.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

##reload(module)


class FkChain(module.Module):

    def __init__(self, startJoint=None, endJoint=None, exclude=[], name='FkChain1',
                 character=None, parent=None, shapeType='cube', mirror=False, side='L',
                 alignWorld=False):

        module.Module.__init__(self, name=name, modType='FkChain', character=character, 
                               shapeType=shapeType, mirror=mirror, side=side, alignWorld=alignWorld)

        self.parent = parent
        self.startJoint = startJoint
        # If no endJoint is given, the chain will expand through the dag
        # and trim itself at joints in the exclude list
        self.endJoint = endJoint
        self.exclude = exclude

        self.contract = [self.startJoint]

    @wrapBuild
    def build(self):
        # finds the joints that should belong in the chain
        self.bindJoints = self.findHierarchyJoints()
        self.driveJoints = self.createDriveJoints()

        self.components = self.buildFkControls(self.driveJoints)

    def buildFkControls(self, driveJoints):

        components = []

        for i in range(len(driveJoints)):
            jnt = driveJoints[i]

            ctrl = shapelib.Shape(name=self.findControlName(jnt, identifier='Fk'),
                                  shapeType=self.shapeType, jnt=jnt)

            components.append(ctrl)

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
                    cmds.parent(ctrl.offsetGrp, components[0].ctrl)

            cmds.addAttr(jnt, longName='driveCtrl', attributeType='message')
            cmds.addAttr(ctrl.ctrl, longName='driveJoint', attributeType='message')
            cmds.connectAttr(ctrl.ctrl + '.driveJoint', jnt + '.driveCtrl')

        self.setupAlignWorld(components[0], defaultValue=self.alignWorld)

        return components

