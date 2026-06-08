"""Purpose:
The Skeleton class is a MayaComponent that contains the joint hierarchy for a rig.
It contains the logic for serializing and deserializing a joint hierarchy, which is used to save and load the skeleton component of a rig.
"""

import os
import maya.cmds as cmds

from .mayaComponent import MayaComponent


class Skeleton(MayaComponent):

    def __init__(self, asset, component_type):
        super(Skeleton, self).__init__(asset, component_type)

    @property
    def relative_path(self):
        # /rig/components/skeleton.ma
        return os.path.join('rig', 'components', self.type + self.extension)

    @classmethod
    def serialize_joint_hierarchy(cls, root_joint):
        def _get_joint_data(jnt):
            joint_data = dict()

            joint_data['shortName'] = jnt
            jointParent = cmds.listRelatives(jnt, parent=True, type='joint')
            joint_data['parent'] = jointParent
            joint_data['worldMatrix'] = cmds.xform(
                jnt, query=True, matrix=True, worldSpace=True)
            joint_data['radius'] = cmds.getAttr(f'{jnt}.radius')

            return joint_data

        joints = [_get_joint_data(root_joint)]

        for child_joint in cmds.listRelatives(
                root_joint,
                children=True,
                type='joint',
                allDescendents=True):
            joints.append(_get_joint_data(child_joint))

        return joints

    @classmethod
    def deserialize_joint_hierarchy(cls, data):
        new_joints = []

        for joint_data in data:
            cmds.select(clear=True)
            jointName = joint_data['shortName']
            newJoint = cmds.joint(name=jointName)
            cmds.xform(newJoint, matrix=joint_data['worldMatrix'])

            if joint_data.get('parent'):
                cmds.parent(newJoint, joint_data['parent'])
            if joint_data.get('radius'):
                cmds.setAttr(newJoint + '.radius', joint_data['radius'])

            cmds.makeIdentity(newJoint, apply=True)

            new_joints.append(newJoint)

        cmds.select(clear=True)
