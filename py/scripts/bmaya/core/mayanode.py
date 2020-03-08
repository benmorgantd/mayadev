import json

import maya.cmds as cmds
import maya.OpenMaya as om



rotationOrders = {'xyz':(0, om.MEulerRotation.kXYZ),
                 'yzx':(1, om.MEulerRotation.kYZX), 
                 'zxy':(2, om.MEulerRotation.kZXY),
                 'xzy':(3, om.MEulerRotation.kXZY),
                 'yxz':(4, om.MEulerRotation.kYXZ), 
                 'zyx':(5, om.MEulerRotation.kZYX)}

displayColors = {'black':1,
                'grey':3,
                'blue':6,
                'pink':9,
                'red':13,
                'lime':14,
                'darkblue':15,
                'white':16,
                'yellow':17,
                'green':23}


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
        self.shortName = self.dagPath.partialPathName()
    
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
        self.fnTransform.getRotation(quat, om.MSpace.kWorld)
        return quat

    @quaternion.setter
    def quaternion(self, quat):
        # sets in transform space
        quat = om.MQuaternion(quat[0], quat[1], quat[2], quat[3])
        self.fnTransform.setRotation(quat, om.MSpace.kWorld)

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
    def scale(self):
        return list(cmds.getAttr(self.name + '.scale')[0])
    
    @scale.setter
    def scale(self, value):
        cmds.setAttr(self.name + '.scale', *value)

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

    @property
    def transformationMatrix(self):
        return self.fnTransform.transformation()
    
    @property
    def matrix(self):
        return self.transformationMatrix.asMatrix()

    @property
    def matrixVectors(self):
        matrix = self.matrixList
        matrixVectors = om.MVectorArray()

        for vector in matrix:
            matrixVectors.append(om.MVector(*vector))

        return matrixVectors


    @property
    def matrixList(self):
        matrix = self.matrix

        util = om.MScriptUtil()

        matrixList = []

        for row in range(4):
            rowList = []
            for column in range(3):
                rowList.append(util.getDoubleArrayItem(matrix[row], column))
        
            matrixList.append(rowList)

        return matrixList

    @property 
    def fnDag(self):
        return om.MFnDagNode(self.dagPath)

    @property
    def parent(self):
        # return the Transform of the parent
        parentName = cmds.listRelatives(self.name, parent=True)

        if parentName:
            return Transform(parentName[0])
        else:
            return None

    @parent.setter
    def parent(self, dagName):
        if not dagName:
            cmds.parent(self.name, world=True, absolute=True)
        else:
            _shortName = self.shortName
            try:
                cmds.parent(self.name, dagName, absolute=True)
            except RuntimeError:
                # already a child of that node
                return 
            # update the dag path after changing parent
            sel = om.MSelectionList()
            sel.add(_shortName)
            dag = om.MDagPath()
            sel.getDagPath(0, dag)

            self.dagPath = dag
            self.shortName = dag.partialPathName()
            self.name = dag.fullPathName()

    @property
    def children(self):
        return cmds.listRelatives(self.name, children=True, type='transform') or []

    @property
    def displayColor(self):
        return cmds.getAttr(self.name + '.overrideColor')

    @displayColor.setter
    def displayColor(self, value):
        cmds.setAttr(self.name + '.overrideEnabled', True)
        if value in displayColors.keys():
            cmds.setAttr(self.name + '.overrideColor', displayColors[value])
        else:
            cmds.setAttr(self.name + '.overrideColor', value)
    
    @property
    def metadata(self):
        if 'metadata' in cmds.listAttr(self.name):
            return json.loads(cmds.getAttr(self.name + '.metadata'))
        else:
            return {}

    @metadata.setter
    def metadata(self, value):
        # use json.dumps. Make this value a json dictionary
        if 'metadata' not in cmds.listAttr(self.name):
            cmds.addAttr(self.name, longName='metadata', dataType='string')

        cmds.setAttr(self.name + '.metadata', json.dumps(value), type='string')

    @property
    def longAxis(self):
        axis = ['X', 'Y', 'Z']
        translate = cmds.getAttr(self.name + '.translate')[0]
        return axis[translate.index(max(translate))]
    
    @property 
    def vectorFromParent(self):
        if self.parent:
            return self.worldPosition - self.parent.worldPosition
        else:
            return self.worldPosition

    @property
    def distanceFromParent(self):
        return self.vectorFromParent.length()

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


class Locator(Transform):
    def __init__(self, name):
        if not cmds.objExists(name):
            cmds.spaceLocator(name=name)
            
        super(Locator, self).__init__(name)

        self.localScale = .35

        
    @property
    def shape(self):
        return cmds.listRelatives(self.name, type='shape', children=True)[0]

    @property
    def localScaleX(self):
        return cmds.getAttr(self.shape + '.localScaleX')
    
    @localScaleX.setter
    def localScaleX(self, value):
        cmds.setAttr(self.shape + '.localScaleX', value)

    @property
    def localScaleY(self):
        return cmds.getAttr(self.shape + '.localScaleY')
    
    @localScaleY.setter
    def localScaleY(self, value):
        cmds.setAttr(self.shape + '.localScaleY', value)

    @property
    def localScaleZ(self):
        return cmds.getAttr(self.shape + '.localScaleZ')
    
    @localScaleZ.setter
    def localScaleZ(self, value):
        cmds.setAttr(self.shape + '.localScaleZ', value)

    @property
    def localScale(self):
        return list(cmds.getAttr(self.shape + '.localScale')[0])

    @localScale.setter
    def localScale(self, value):
        for axis in ['X', 'Y', 'Z']:
            cmds.setAttr(self.shape + '.localScale' + axis, value)
    
    def localScale(self, value):
        for axis in ['X', 'Y', 'Z']:
            cmds.setAttr(self.shape + '.localScale' + axis, value)


class Joint(Transform):
    def __init__(self, name):
        if not cmds.objExists(name):
            previousSelection = cmds.ls(sl=1)
            cmds.select(clear=True)

            cmds.joint(name=name)

            if previousSelection:
                cmds.select(previousSelection)

        super(Joint, self).__init__(name)


    @property
    def radius(self):
        return cmds.getAttr(self.name + '.radius')
    
    @radius.setter
    def radius(self, value):
        cmds.setAttr(self.name + '.radius', value)

    @property
    def orient(self):
        return cmds.getAttr(self.name + '.jointOrient')[0]

    @orient.setter
    def orient(self, value):
        cmds.setAttr(self.name + '.jointOrient', *value)
