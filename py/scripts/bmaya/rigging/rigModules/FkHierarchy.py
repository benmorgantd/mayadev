'''FkHierarchy'''

import maya.cmds as cmds

from bmaya.rigging.Osiris.base import module
from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib

reload(module)
reload(shapelib)


class FkHierarchy(module.Module):

    def __init__(self, startJoint=None, exclude=[], name='fkHierarchy1',
                 character=None, parent=None, shapeType='cube'):
        super(FkHierarchy, self).__init__(name=name, modType='FkHierarchy',
                                          character=character, shapeType=shapeType)

        self.parent = parent
        self.startJoint = startJoint
        self.exclude = exclude

        self.contract = [self.startJoint]

    @wrapBuild
    def build(self):

        self.checkContract()

        # fills self.joints to contain the non-excluded joints 
        # inbetween start and end joint
        self.getContainedJoints()

        rootJnt = True

        for jnt in self.bindJoints:
            ctrl = shapelib.Shape(jnt, self.shapeType, jnt=jnt)

            self.components.append(ctrl)

            self.parentConstrain(ctrl.ctrl, jnt, maintainOffset=True)

            if rootJnt:
                cmds.parent(ctrl.grp, self.componentsGrp)
            else:
                parentJoint = cmds.listRelatives(
                    jnt, parent=True, type='joint')[0]
                parentCtrl = cmds.listConnections(parentJoint + '.ctrl')

                cmds.parent(ctrl.grp, parentCtrl[0])

            cmds.addAttr(jnt, longName='ctrl', attributeType='message')
            cmds.addAttr(ctrl.ctrl, longName='bindJoint',
                         attributeType='message')
            cmds.connectAttr(ctrl.ctrl + '.bindJoint', jnt + '.ctrl')

            rootJnt = False

        # parent the startJoint control to the module's parent
        if self.parent:
            self.parentConstrain(self.parent, self.components[0].grp, maintainOffset=True)