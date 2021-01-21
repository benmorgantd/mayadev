import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

from component import Component
import bmaya.mayanode


class Skeleton(Component):

    def __init__(self, asset, componentType):
        super(Skeleton, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/skeleton.ma
        return os.path.join('rig', 'components', self.type + self.extension)

    @classmethod
    def serializeJointHierarchy(cls, rootJoint):
        rootJoint = bmaya.mayanode.DagNode(rootJoint)

        joints = [{'shortName': rootJoint.shortName,
                   'worldMatrix': rootJoint.worldMatrixList, 
                   'parent': None,
                   'radius':rootJoint.get('radius')}]

        def _getJointData(jnt):
            jointData = dict()

            jointData['shortName'] = jnt.shortName
            jointParent = jnt.parent
            jointData['parent'] = jointParent.shortName if jointParent else None
            jointData['worldMatrix'] = jnt.worldMatrixList
            jointData['radius'] = jnt.get('radius')

            return jointData

        for childJoint in rootJoint.allChildren(filterType=om.MFn.kJoint):
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

