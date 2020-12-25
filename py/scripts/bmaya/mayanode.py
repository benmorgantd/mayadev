import json

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.OpenMayaAnim as omAnim

ROTATION_ORDERS = {'xyz': (0, om.MEulerRotation.kXYZ),
                  'yzx': (1, om.MEulerRotation.kYZX),
                  'zxy': (2, om.MEulerRotation.kZXY),
                  'xzy': (3, om.MEulerRotation.kXZY),
                  'yxz': (4, om.MEulerRotation.kYXZ),
                  'zyx': (5, om.MEulerRotation.kZYX)}

DISPLAY_COLORS = {'black': 1,
                 'grey': 3,
                 'blue': 6,
                 'pink': 9,
                 'red': 13,
                 'lime': 14,
                 'darkblue': 15,
                 'white': 16,
                 'yellow': 17,
                 'green': 23}


class DependencyNode(object):
    def __init__(self, name):
        # I think many OpenMaya objects inherit from MObject, so we may want to directly check types instead
        if isinstance(name, om.MObject):
            self.mObject = om.MObject(name)
        elif isinstance(name, basestring):
            try:
                # we only want to deal in objects that have unique names
                sel = om.MSelectionList()
                sel.add(name)
                self.mObject = om.MObject()
                sel.getDependNode(0, self.mObject)
            except RuntimeError:
                raise RuntimeError('0 or more than one object matches name: ' + name)
        else:
            raise RuntimeError('Given argument type {0} not supported.'.format(type(name)))

        # since an object's MObject is consistent, we can create its fn sets in the init
        try:
            self.fnDependencyNode = om.MFnDependencyNode(self.mObject)
        except RuntimeError:
            raise RuntimeError('Given object type is not compatible')

    def __repr__(self):
        # return '<{0} {1} object {2}>'.format(__name__, type(self).__name__, self.fnDependencyNode.name())
        return self.fnDependencyNode.name()

    def __str__(self):
        return self.fnDependencyNode.name()

    def __add__(self, other):
        return self.fnDependencyNode.name() + other

    def __radd__(self, other):
        return other + self.fnDependencyNode.name()

    def __eq__(self, other):
        if isinstance(other, DependencyNode):
            return self.mObject == other.mObject
        else:
            return False

    @property
    def name(self):
        return self.fnDependencyNode.name()
    #
    # @property
    # def attributes(self):
    #
    #     _attributes = []
    #     for i in xrange(self.fnDependencyNode.attributeCount()):
    #         attributeMObject = self.fnDependencyNode.attribute(i)
    #         plug = self.fnDependencyNode.findPlug(attributeMObject)
    #         # These args return us the long name of the attribute without the node
    #         _attributes.append(plug.partialName(False, False, False, False, False, True))
    #
    #     return _attributes


class DagNode(DependencyNode):
    def __init__(self, name):
        super(DagNode, self).__init__(name)

    @property
    def dagPath(self):
        sel = om.MSelectionList()
        # we create a cycle on Transforms if we reuse the object's dependency node fn set
        fnDependencyNode = om.MFnDependencyNode(self.mObject)
        sel.add(fnDependencyNode.name())
        dag = om.MDagPath()
        sel.getDagPath(0, dag)

        return dag

    @property
    def fnDagNode(self):
        return om.MFnDagNode(self.dagPath)

    def __repr__(self):
        # return '<{0} {1} object {2}>'.format(__name__, type(self).__name__, self.fnDependencyNode.name())
        return self.dagPath.fullPathName()

    def __str__(self):
        return self.dagPath.fullPathName()

    def __add__(self, other):
        return self.dagPath.fullPathName() + other

    def __radd__(self, other):
        return other + self.dagPath.fullPathName()

    def __eq__(self, other):
        if isinstance(other, DagNode):
            return self.mObject == other.mObject
        else:
            return False


class Transform(DagNode):
    def __init__(self, name):
        super(Transform, self).__init__(name)

        self.fnDependencyNode = om.MFnDependencyNode(self.mObject)

    @property
    def name(self):
        return self.dagPath.fullPathName()

    @property
    def shortName(self):
        return self.dagPath.partialPathName()

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
        return om.MEulerRotation(vector.x, vector.y, vector.z,
                                 ROTATION_ORDERS[self.rotationOrder][1])

    @worldRotation.setter
    def worldRotation(self, degreeRotation):
        rotX = om.MAngle(degreeRotation[0], om.MAngle.kDegrees).asRadians()
        rotY = om.MAngle(degreeRotation[1], om.MAngle.kDegrees).asRadians()
        rotZ = om.MAngle(degreeRotation[2], om.MAngle.kDegrees).asRadians()
        rot = om.MEulerRotation(rotX, rotY, rotZ,
                                ROTATION_ORDERS[self.rotationOrder][1])
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

        for order in ROTATION_ORDERS.keys():
            if ROTATION_ORDERS[order] == rotOrderNumber:
                stringRepresentation = order

        return stringRepresentation

    @rotationOrder.setter
    def rotationOrder(self, order):
        cmds.setAttr(self.name + '.rotateOrder', ROTATION_ORDERS[order][0])

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
        return cmds.listRelatives(self.name, children=True,
                                  type='transform') or []

    @property
    def displayColor(self):
        return cmds.getAttr(self.name + '.overrideColor')

    @displayColor.setter
    def displayColor(self, value):
        cmds.setAttr(self.name + '.overrideEnabled', True)
        if value in DISPLAY_COLORS.keys():
            cmds.setAttr(self.name + '.overrideColor', DISPLAY_COLORS[value])
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

    @property
    def shape(self):
        # get the transform's shape if it has one
        try:
            # Don't modify the node's existing dag path object
            tempDag = om.MDagPath(self.dagPath)
            # Only supports 1 shape
            tempDag.extendToShapeDirectlyBelow(0)
            return Mesh(tempDag.node())
        except RuntimeError:
            # no shape
            return None

    def lockAttr(self, attrs):
        if self.fnDependencyNode.hasAttribute(attr):
            plug = self.fnDependencyNode.findPlug(attr)
            plug.setLocked(True)

    def unlockAttr(self, attr):
        if self.fnDependencyNode.hasAttribute(attr):
            plug = self.fnDependencyNode.findPlug(attr)
            plug.setLocked(False)

    def lockTransforms(self):
        # This is not undoable
        for attr in ['translate', 'rotate', 'scale']:
            for axis in ['X', 'Y', 'Z']:
                self.lockAttr(attr + axis)

    def unlockTransforms(self):
        # This is not undoable
        for attr in ['translate', 'rotate', 'scale']:
            for axis in ['X', 'Y', 'Z']:
                self.unlockAttr(attr + axis)

    def constrain(self, parents, constraintType='point', weights=None,
                  maintainOffset=False):
        if not weights:
            weights = [1.0] * len(parents)

        for i in range((len(parents))):
            parent = parents[i]
            if constraintType == 'point':
                const = cmds.pointConstraint(parent, self.name,
                                             maintainOffset=maintainOffset,
                                             weight=weights[i])
            elif constraintType == 'orient':
                const = cmds.orientConstraint(parent, self.name,
                                              maintainOffset=maintainOffset,
                                              weight=weights[i])
            elif constraintType == 'parent':
                const = cmds.parentConstraint(parent, self.name,
                                              maintainOffset=maintainOffset,
                                              weight=weights[i])
            else:
                raise ValueError(
                    constraintType + ' is not an accepted constraint type.')

        return const


class Mesh(DagNode):
    def __init__(self, name):
        super(Mesh, self).__init__(name)

        try:
            self.fnMesh = om.MFnMesh(self.mObject)
        except RuntimeError:
            raise RuntimeError('Given object type is not compatible. Did you pass a kTransform type?')

    @property
    def transform(self):
        # return this mesh's transform
        _dag = om.MDagPath(self.dagPath)
        return Transform(_dag.transform())

    @property
    def getSkinCluster(self):

        itDG = om.MItDependencyGraph(self.mObject,
                                     om.MFn.kSkinClusterFilter,
                                     om.MItDependencyGraph.kUpstream,
                                     om.MItDependencyGraph.kDepthFirst,
                                     om.MItDependencyGraph.kNodeLevel)

        if itDG.isDone():
            # No skin cluster. Are you sure you passed a mesh?
            return None

        skinClusterMObjArray = om.MObjectArray()

        while not itDG.isDone():
            currentNode = itDG.currentItem()
            skinClusterMObjArray.append(currentNode)

            itDG.next()

        # Return the first item in the array
        return SkinCluster(skinClusterMObjArray[0])


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


class SkinCluster(DependencyNode):
    def __init__(self, name):
        super(SkinCluster, self).__init__(name)

        self.fnSkinCluster = omAnim.MFnSkinCluster(self.mObject)

    @property
    def outputGeometry(self):
        outputGeometryArrayPlug = self.fnDependencyNode.findPlug('outputGeometry')
        outputGeometryPlug = outputGeometryArrayPlug.elementByPhysicalIndex(0)
        connectedMeshes = om.MPlugArray()
        outputGeometryPlug.connectedTo(connectedMeshes, False, True)
        # return the first connected mesh
        return Mesh(connectedMeshes[0].node())

    @property
    def influenceObjects(self):
        _influenceObjects = om.MDagPathArray()
        # make this static for now so that we don't constantly calculate it
        self.fnSkinCluster.influenceObjects(_influenceObjects)
        return _influenceObjects

    @property
    def influenceCount(self):
        return self.influenceObjects.length()

    @property
    def infCountPointer(self):
        _infCount = om.MScriptUtil(self.influenceCount)
        # c++ utility needed for the get weights function
        _infCountPtr = _infCount.asUintPtr()
        return _infCountPtr

    @property
    def influenceIndices(self):
        _influenceIndices = om.MIntArray()
        # create an MIntArray that just counts from 0 to infCount
        for i in xrange(self.influenceCount):
            _influenceIndices.append(i)

        return _influenceIndices

    def getWeights(self, components=None):
        weights = om.MDoubleArray()

        if not components:
            components = om.MObject()
        else:
            assert isinstance(components, om.MObject())

        self.fnSkinCluster.getWeights(self.outputGeometry.dagPath, components, weights, self.infCountPointer)

        return weights

    def setWeights(self, weights, components=None):
        if not components:
            components = om.MObject()
        else:
            assert isinstance(components, om.MObject())

        assert isinstance(weights, (om.MDoubleArray, list))

        mFnSkinCluster.setWeights(self.outputGeometry.dagPath, components, self.influenceIndices, weights)

    def pruneWeights(self, maxInfluence=4):
        return True

    def getWeightDictionary(self):
        return {}
