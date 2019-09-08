'''FkHierarchy'''

import maya.cmds as cmds

from ..base import module
from ..base.decorators import wrapBuild
from ..tools.shapes import lib as shapeLib


class FkHierarchy(module.Module):

    def __init__(self, startJoint=None, exclude=[], name='fkHierarchy1',
                 character=None):
        super(FkHierarchy, self).__init__(name=name, modType='FkHierarchy',
                                          character=character)

        self.startJoint = startJoint
        self.exclude = exclude

    @wrapBuild
    def build(self):

        self.checkContractJoint(['startJoint'])

        # fills self.joints to contain the non-excluded joints inbetween start and end joint
        self.getContainedJoints()

        rootJnt = True

        for jnt in self.bindJoints:
            ctrl = shapeLib.Shape(jnt, self.shapeType, jnt=jnt)

            self.components.append(ctrl)

            self.parentConstrain(ctrl.ctrl, jnt, maintainOffset=True)

            if rootJnt:
                cmds.parent(ctrl.grp, self.modGrp)
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
