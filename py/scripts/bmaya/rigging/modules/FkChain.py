import maya.cmds as cmds

from bmaya.rigging.base import module
from bmaya.rigging.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import name


##reload(module)


class FkChain(module.Module):

    def __init__(self, startJoint=None, endJoint=None, exclude=[],
                 name='FkChain1',
                 character=None, parent=None, shapeType='cube', mirror=False,
                 side='L',
                 alignWorld=False):

        module.Module.__init__(self, name=name, modType='FkChain',
                               character=character,
                               shapeType=shapeType, mirror=mirror, side=side,
                               alignWorld=alignWorld)

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
        self.bindJoints = self.findHierarchyJoints(exclude=self.exclude)
        self.driveJoints = self.createDriveJoints()

        self.components = self.buildFkControls(self.driveJoints,
                                               setupAlignWorld=True)

    def buildFkControls(self, driveJoints, setupAlignWorld=False):

        components = []

        for i in range(0, len(driveJoints)):
            jnt = driveJoints[i]

            # easy naming override for face controls...
            # TODO: This could be replaced if I ever made a shape swapping system
            if 'Driver_' in jnt:
                shapeTypeOverride = 'diamond'
            elif 'Base_' in jnt:
                shapeTypeOverride = 'circle'
            else:
                shapeTypeOverride = 'cube'

            ctrl = shapelib.Shape(
                name=name.findControlName(jnt, identifier='Fk'),
                shapeType=shapeTypeOverride, jnt=jnt)

            components.append(ctrl)

            self.parentConstrain(ctrl.ctrl, jnt, maintainOffset=True)

            if i == 0:
                cmds.parent(ctrl.offsetGrp, self.componentsGrp)
            else:
                parentJoint = cmds.listRelatives(
                    jnt, parent=True, type='joint')[0]

                if cmds.objExists(parentJoint + '.driveCtrl'):
                    parentCtrl = cmds.listConnections(parentJoint + '.driveCtrl')
                else:
                    parentCtrl = None

                if parentCtrl:
                    cmds.parent(ctrl.offsetGrp, parentCtrl[0])
                else:
                    cmds.parent(ctrl.offsetGrp, components[0].ctrl)

            cmds.addAttr(jnt, longName='driveCtrl', attributeType='message')
            cmds.addAttr(ctrl.ctrl, longName='driveJoint',
                         attributeType='message')
            cmds.connectAttr(ctrl.ctrl + '.driveJoint', jnt + '.driveCtrl')

        if setupAlignWorld:
            self.setupAlignWorld(components[0], defaultValue=self.alignWorld)

        return components
