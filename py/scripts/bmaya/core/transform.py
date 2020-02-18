import maya.cmds as cmds
import maya.OpenMaya as om


rotationOrders = {'xyz':(0, om.MEulerRotation.kXYZ),
                 'yzx':(1, om.MEulerRotation.kYZX), 
                 'zxy':(2, om.MEulerRotation.kZXY),
                 'xzy':(3, om.MEulerRotation.kXZY),
                 'yxz':(4, om.MEulerRotation.kYXZ), 
                 'zyx':(5, om.MEulerRotation.kZYX)}


class Transform(object):
    def __init__(self, name):
        try:
            # we only want to deal in objects that have unique names
            sel = om.MSelectionList()
            sel.add(name)
        except RuntimeError:
            raise RuntimeError('More than one object matches name: ' + name)

        self.dagPath = om.MDagPath()
        sel.getDagPath(0, self.dagPath)

        self.name = self.dagPath.fullPathName()
    
    # MFnTransform properties

    @property 
    def fnTransform(self):
        return om.MFnTransform(self.dagPath)

    @property
    def worldPosition(self):
        return self.fnTransform.getTranslation(om.MSpace.kWorld)

    @worldPosition.setter
    def worldPosition(self, vector):
        _vector = om.MVector(vector[0], vector[1], vector[2])
        self.fnTransform.setTranslation(_vector, om.MSpace.kWorld)

    @property
    def quaternion(self):
        quat = om.MQuaternion()
        # gets in transform space
        self.fnTransform.getRotation(quat)
        return quat

    @quaternion.setter
    def quaternion(self, quat):
        # sets in transform space
        self.fnTransform.setRotation(quat)

    @property
    def worldRotation(self):
        vector = self.quaternion.asEulerRotation().asVector()
        vector *= (180.0 / 57.2957795131)
        return om.MEulerRotation(vector.x, vector.y, vector.z, rotationOrders[self.rotationOrder][1])

    @worldRotation.setter
    def worldRotation(self, degreeRotation):
        rotX = om.MAngle(degreeRotation[0], om.MAngle.kDegrees).asRadians()
        rotY = om.MAngle(degreeRotation[1], om.MAngle.kDegrees).asRadians()
        rotZ = om.MAngle(degreeRotation[2], om.MAngle.kDegrees).asRadians()
        rot = om.MEulerRotation(rotX, rotY, rotZ, rotationOrders[self.rotationOrder][1])
        self.fnTransform.setRotation(rot)

    @property
    def rotationOrder(self):
        rotOrderNumber = cmds.getAttr(self.name + '.rotateOrder')
        stringRepresentation = 'xyz'

        for order in rotationOrders.keys():
            if rotationOrders[order] == rotOrderNumber:
                stringRepresentation = order

        return stringRepresentation

    @rotationOrder.setter
    def rotationOrder(self, order):
        cmds.setAttr(self.name + '.rotateOrder', rotationOrders[order][0])

    @property
    def localPosition(self):
        return self.fnTransform.getTranslation(om.MSpace.kObject)

    @localPosition.setter
    def localPosition(self, vector):
        # make a new vector here so we can pass in either an MVector or a list/tuple
        _vector = om.MVector(vector[0], vector[1], vector[2])
        self.fnTransform.setTranslation(_vector, om.MSpace.kObject)

    # MFnDagPath properties 

    @property 
    def fnDag(self):
        return om.MFnDagNode(self.dagPath)

    @property
    def parent(self):
        # return the Transform of the parent
        parentName = cmds.listRelatives(self.fnDag.fullPathName(), parent=True)

        if parentName:
            return Transform(parentName[0])
        else:
            return None

    @parent.setter
    def parent(self, dagName):
        if not dagName:
            cmds.parent(self.name, world=True, absolute=True)
        else:
            cmds.parent(self.name, dagName, absolute=True)

    @property
    def children(self):
        return cmds.listRelatives(self.name, children=True, type='transform') or []

    def lockAttrs(self, attrs):
        axis = ['X','Y','Z']
        for attr in attrs:
            if attr in ['translate', 'rotate', 'scale']:
                for x in axis:
                    cmds.setAttr(self.name + '.' + attr + x, keyable=False, lock=True, channelBox=False)
            else:
                cmds.setAttr(self.name + '.' + attr, keyable=False, lock=True, channelBox=False)

    def constrain(self, parents, constraintType='point', weights=None, maintainOffset=False):
        if not weights:
            weights = [1.0] * len(parents)
        
        for i in range((len(parents))):
            parent = parents[i]
            if constraintType == 'point':
                const = cmds.pointConstraint(parent, self.name, maintainOffset=maintainOffset, weight=weights[i])
            elif constraintType == 'orient':
                const = cmds.orientConstraint(parent, self.name, maintainOffset=maintainOffset, weight=weights[i])
            elif constraintType == 'parent':
                const = cmds.parentConstraint(parent, self.name, maintainOffset=maintainOffset, weight=weights[i])
            else:
                raise ValueError(constraintType + ' is not an accepted constraint type.')

        return const