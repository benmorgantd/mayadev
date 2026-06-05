"""Purpose:
The Skeleton class is a MayaComponent that contains the joint hierarchy for a rig.
It contains the logic for serializing and deserializing a joint hierarchy, which is used to save and load the skeleton component of a rig.
"""

import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

from .mayaComponent import MayaComponent

class Skeleton(MayaComponent):

    def __init__(self, asset, componentType):
        super(Skeleton, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/skeleton.ma
        return os.path.join('rig', 'components', self.type + self.extension)

    @classmethod
    def serializeJointHierarchy(cls, rootJoint):
        def _getJointData(jnt):
            jointData = dict()

            jointData['shortName'] = jnt
            jointParent = cmds.listRelatives(jnt, parent=True, type='joint')
            jointData['parent'] = jointParent
            jointData['worldMatrix'] = cmds.xform(jnt, query=True, matrix=True, worldSpace=True)
            jointData['radius'] = cmds.getAttr(f'{jnt}.radius')

            return jointData

        joints = [_getJointData(rootJoint)]

        for childJoint in cmds.listRelatives(rootJoint, children=True, type='joint', allDescendents=True):
            joints.append(_getJointData(childJoint))

        return joints

    @classmethod
    def deserializeJointHierarchy(cls, data):
        newJoints = []

        for jointData in data:
            cmds.select(clear=True)
            jointName = jointData['shortName']
            newJoint = cmds.joint(name=jointName)
            cmds.xform(newJoint, matrix=jointData['worldMatrix'])

            if jointData.get('parent'):
                cmds.parent(newJoint, jointData['parent'])
            if jointData.get('radius'):
                cmds.setAttr(newJoint + '.radius', jointData['radius'])

            cmds.makeIdentity(newJoint, apply=True)

            newJoints.append(newJoint)

        cmds.select(clear=True)

