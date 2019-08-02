'''FkHierarchy'''
import Osiris.lib.base.module as module
import Osiris.lib.tools.shapes.lib as shapeLib
import maya.cmds as cmds
from Osiris.lib.base.decorators import wrapBuild


class FkHierarchy(module.Module):

    def __init__(self, character,
                 side='l',
                 mirror=False,
                 shapeType='cube',
                 contract={'startJoint': None, 'exclude': []},
                 modType='FkHierarchy',
                 name='fkHierarchy1'):

        super(FkHierarchy, self).__init__(
            character,
            modType='FkHierarchy',
            side=side,
            mirror=mirror,
            name=name,
            shapeType=shapeType)

        self.components = []
        self.contract = contract
        self.shapeType = shapeType

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
