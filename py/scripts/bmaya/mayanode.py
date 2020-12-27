import json

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.OpenMayaAnim as omAnim

# CONSTANTS #

ROTATION_ORDERS = {'xyz': (0, om.MEulerRotation.kXYZ), 'yzx': (1, om.MEulerRotation.kYZX),
                   'zxy': (2, om.MEulerRotation.kZXY), 'xzy': (3, om.MEulerRotation.kXZY),
                   'yxz': (4, om.MEulerRotation.kYXZ), 'zyx': (5, om.MEulerRotation.kZYX)}

DISPLAY_COLORS = {'black': 1, 'grey': 3, 'blue': 6, 'pink': 9, 'red': 13, 'lime': 14, 'darkblue': 15, 'white': 16,
                  'yellow': 17, 'green': 23}

SPACES = {'world': om.MSpace.kWorld, 'object': om.MSpace.kObject, 'local': om.MSpace.kTransform}


class Connections(object):
    def __init__(self, plug):
        plug = om.MPlug(plug)
        self.inputs = om.MPlugArray()
        self.outputs = om.MPlugArray()

        if plug.isConnected():
            plug.connectedTo(self.inputs, True, False)
            plug.connectedTo(self.outputs, False, True)


class DependencyNode(object):
    def __init__(self, name):
        # I think many OpenMaya objects inherit from MObject, so we may want to directly check types instead
        if isinstance(name, om.MObject):
            self.mObject = om.MObject(name)
        elif isinstance(name, basestring):
            self.mObject = self.stringToMObject(name)

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

    def __getattr__(self, attribute):
        if self.fnDependencyNode.hasAttribute(attribute):
            plug = self.fnDependencyNode.findPlug(attribute)
            plugMObj = plug.attribute()
            plugType = plugMObj.apiType()
            # print(plugMObj.apiTypeStr())

            if plugType == om.MFn.kDoubleLinearAttribute:
                return plug.asDouble()
            elif plugType == om.MFn.kDoubleAngleAttribute:
                return plug.asMAngle()
            elif plugType == om.MFn.kNumericAttribute:
                # get data type
                fnNumericAttr = om.MFnNumericAttribute(plugMObj)
                unitType = fnNumericAttr.unitType()
                if unitType == 1:
                    return plug.asBool()
                elif unitType == 3:
                    return plug.asChar()
                elif unitType == 4:
                    return plug.asShort()
                elif unitType == 7:
                    return plug.asLong()
                elif unitType == 8:
                    return plug.asInt()
                elif unitType in [13, 14]:
                    return plug.asFloat()
                else:
                    raise AttributeError('The given MFnNumericData type {0} is not supported.'.format(unitType))
            elif plugType == om.MFn.kAttribute3Double:
                _result = []
                for i in range(plug.numChildren()):
                    _childPlug = plug.child(i)
                    _result.append(_childPlug.asDouble())
                return _result
            elif plugType == om.MFn.kTypedAttribute:
                fnTypedAttr = om.MFnTypedAttribute(plugMObj)
                typedAttrType = fnTypedAttr.attrType()
                if typedAttrType == 5:
                    # kMatrix type. Get matrix data without the MFnTransform
                    if plug.isArray():
                        # worldMatrix, worldInverseMatrix, parentMatrix, parentInverseMatrix
                        plug = plug.elementByLogicalIndex(0)
                        fnMatrixData = om.MFnMatrixData(plug.asMObject())
                        return fnMatrixData.matrix()
                    else:
                        # matrix, inverseMatrix, xformMatrix
                        # Can't use MDataHandle and MDataBlock to get the matrix attribute since
                        # we'd need to do that in a node's compute method...
                        return None

                        # dataHandle = plug.constructHandle(om.MDataBlock())  # TODO bug here with class argument type.  # fnMatrixData = om.MFnMatrixData(dataHandle.data())  # return fnMatrixData.matrix()

                raise AttributeError('getattr is currently not supported for this attribute type.')
            elif plugType == om.MFn.kEnumAttribute:
                return plug.asInt()
            elif plugType == om.MFn.kStringData:
                return plug.asString()
            elif plugType == om.MFn.kMessageAttribute:
                raise AttributeError('getattr is currently not supported for this attribute type.')
            else:
                raise AttributeError('getattr is currently not supported for this attribute type.')
            return True

        if not hasattr(self, attribute):
            # We're calling __getattr__ before the class has been fully initialized
            return super(DependencyNode, self).__getattribute__(attribute)

    # TODO: supporting setattr is a lot more complicated and introduces possible cycles
    # def __setattr__(self, attribute, value):
    #     if hasattr(self, 'fnDependencyNode'):
    #         if self.fnDependencyNode.hasAttribute(attribute):
    #             plug = self.fnDependencyNode.findPlug(attribute)
    #             plugMObj = plug.attribute()
    #             plugType = plugMObj.apiType()
    #
    #             if plugType in [om.MFn.kDoubleLinearAttribute, om.MFn.kNumericAttribute]:
    #                 plug.setDouble(value)
    #             elif plugType == om.MFn.kAttribute3Double:
    #                 for i in range(plug.numChildren()):
    #                     _childPlug = plug.child(i)
    #                     _childPlug.setDouble(value[i])
    #             elif plugType == om.MFn.kTypedAttribute:
    #                 # TODO
    #                 raise AttributeError('setattr is currently not supported for this attribute type.')
    #             elif plugType == om.MFn.kEnumAttribute:
    #                 plug.setInt(value)
    #         else:
    #             raise AttributeError('{0} has no attribute {1}'.format(self, attribute))
    #     else:
    #         super(DependencyNode, self).__setattr__(attribute, value)


    @property
    def name(self):
        return self.fnDependencyNode.name()

    @name.setter
    def name(self, value):
        self.fnDependencyNode.setName(self.makeShortNameUnique(value))

    @property
    def fnDependencyNode(self):
        try:
            _fnDependencyNode = om.MFnDependencyNode(self.mObject)
            return _fnDependencyNode
        except RuntimeError:
            raise RuntimeError('Given object type is not compatible')

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

    @classmethod
    def stringToMObject(cls, str):
        _mObject = None
        if isinstance(str, basestring):
            try:
                # we only want to deal in objects that have unique names
                _sel = om.MSelectionList()
                _sel.add(str)
                _mObject = om.MObject()
                _sel.getDependNode(0, _mObject)
            except RuntimeError:
                return None
        else:
            return None

        return _mObject


class DagNode(DependencyNode):
    def __init__(self, name):
        super(DagNode, self).__init__(name)

    def __repr__(self):
        return self.dagPath.fullPathName()

    def __str__(self):
        return self.dagPath.fullPathName()

    def __add__(self, other):
        return self.dagPath.fullPathName() + other

    def __radd__(self, other):
        return other + self.dagPath.fullPathName()

    @property
    def fnDependencyNode(self):
        try:
            _fnDependencyNode = om.MFnDependencyNode(self.mObject)
            return _fnDependencyNode
        except RuntimeError:
            raise RuntimeError('Given object type is not compatible')

    @property
    def fnDagNode(self):
        return om.MFnDagNode(self.dagPath)

    @property
    def name(self):
        return self.dagPath.fullPathName()

    @name.setter
    def name(self, value):
        self.fnDependencyNode.setName(value)

    @property
    def shortName(self):
        return self.dagPath.partialPathName()

    @property
    def dagPath(self):
        _sel = om.MSelectionList()
        _fnDependencyNode = om.MFnDependencyNode(self.mObject)
        # TODO: this doesn't work with shortName duplicates in a scene
        try:
            _sel.add(_fnDependencyNode.name())
            _dag = om.MDagPath()
            _sel.getDagPath(0, _dag)
            return _dag
        except RuntimeError:
            # object's short name is not unique. Iterate through the dag until we find this mObject
            raise RuntimeError('Object short name is not unique')


    @property
    def parent(self):
        # return the Transform of the parent
        if self.dagPath.length() > 1:
            return DagNode(self.fnDagNode.parent(0))
        else:
            return None

    @parent.setter
    def parent(self, newParent):
        if newParent == None and self.dagPath.length() > 1:
            # TODO find out how to parent to world
            return
        elif not isinstance(newParent, DagNode):
            newParent = DagNode(newParent)

        if not self.parent:
            newParent.fnDagNode.addChild(self.mObject)
        elif self.parent and self.parent.mObject != newParent.mObject:
            newParent.fnDagNode.addChild(self.mObject)
        else:
            om.MGlobal.displayWarning('{0} is already the parent of {1}'.format(newParent.shortName, self.shortName))

        # if not dagName:  #     cmds.parent(self.name, world=True, absolute=True)  # else:  #     _shortName = self.shortName  #     try:  #         cmds.parent(self.name, dagName, absolute=True)  #     except RuntimeError:  #         # already a child of that node  #         return  #         # update the dag path after changing parent  #     sel = om.MSelectionList()  #     sel.add(_shortName)  #     dag = om.MDagPath()  #     sel.getDagPath(0, dag)  #  #     self.dagPath = dag  #     self.shortName = dag.partialPathName()  #     self.name = dag.fullPathName()

    @property
    def children(self):
        '''Return child transforms'''

        # Filters don't seem to work here
        _itDag = om.MItDag(om.MItDag.kDepthFirst)
        _itDag.reset(self.dagPath)

        if _itDag.isDone():
            return []
        else:
            # don't give ourself as the first item
            _itDag.next()

        _mObjArray = om.MObjectArray()

        while not _itDag.isDone():
            if _itDag.depth() == 1:
                _currentMObject = _itDag.currentItem()
                if _currentMObject.hasFn(om.MFns.kTransform):
                    _mObjArray.append(_currentMObject)
            _itDag.next()

        _result = []
        for i in xrange(_mObjArray.length()):
            _result.append(DagNode(_mObjArray[i]))
        return _result

    @property
    def allChildren(self):
        '''Return all descendent children transforms'''
        # Filters don't seem to work here
        _itDag = om.MItDag(om.MItDag.kDepthFirst)
        _itDag.reset(self.dagPath)

        if _itDag.isDone():
            return []
        else:
            # don't give ourself as the first item
            _itDag.next()

        _mObjArray = om.MObjectArray()

        while not _itDag.isDone():
            _currentMObject = _itDag.currentItem()
            if _currentMObject.hasFn(om.MFn.kTransform):
                _mObjArray.append(_currentMObject)
            _itDag.next()

        _result = []
        for i in xrange(_mObjArray.length()):
            _result.append(DagNode(_mObjArray[i]))
        return _result

    @property
    def fnTransform(self):
        return om.MFnTransform(self.dagPath)

    @property
    def worldPosition(self):
        _worldMatrixList = self.worldMatrixList
        return om.MVector(*_worldMatrixList[3])

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
        return om.MEulerRotation(vector.x, vector.y, vector.z, ROTATION_ORDERS[self.rotationOrder][1])

    @worldRotation.setter
    def worldRotation(self, degreeRotation):
        rotX = om.MAngle(degreeRotation[0], om.MAngle.kDegrees).asRadians()
        rotY = om.MAngle(degreeRotation[1], om.MAngle.kDegrees).asRadians()
        rotZ = om.MAngle(degreeRotation[2], om.MAngle.kDegrees).asRadians()
        rot = om.MEulerRotation(rotX, rotY, rotZ, ROTATION_ORDERS[self.rotationOrder][1])
        self.fnTransform.setRotation(rot)

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
    def matrixVectors(self):
        matrix = self.matrixList
        matrixVectors = om.MVectorArray()

        for vector in matrix:
            matrixVectors.append(om.MVector(*vector))

        return matrixVectors

    @property
    def matrixList(self):
        return self.matrixToList(self.matrix)

    @property
    def worldMatrixList(self):
        return self.matrixToList(self.worldMatrix)

    @property
    def metadata(self):
        if self.fnDependencyNode.hasAttribute('metadata'):
            return json.loads(self.metadata)
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
        _translate = self.translate
        axis = ['X', 'Y', 'Z']
        return axis[_translate.index(max(_translate))]

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
            _dag = om.MDagPath(self.dagPath)
            # Only supports 1 shape
            _dag.extendToShapeDirectlyBelow(0)
            # check what the shape's type is
            _shapeMObj = _dag.node()
            if _shapeMObj.hasFn(om.MFn.kMesh):
                return Mesh(_shapeMObj)
            elif _shapeMObj.hasFn(om.MFn.kNurbsCurve):
                return Curve(_shapeMObj)
            # TODO support more shape types
            else:
                return Shape(_shapeMObj)

        except RuntimeError:
            # no shape
            return None

    @property
    def worldTransforms(self):
        return self.worldMatrix

    @worldTransforms.setter
    def worldTransforms(self, value):
        # set translation
        _xformMatrix = om.MTransformationMatrix(value)
        self.fnTransform.setTranslation(_xformMatrix.getTranslation(om.MSpace.kWorld), om.MSpace.kWorld)
        # Set rotation
        _quat = _xformMatrix.rotation()
        self.fnTransform.setRotationQuaternion(_quat.x,
                                               _quat.y,
                                               _quat.z,
                                               _quat.w,
                                               om.MSpace.kTransform)

    @property
    def scale(self):
        plug = self.fnDependencyNode.findPlug('scale')
        # type is om.MFn.kAttribute3Double
        _result = []
        for i in range(3):
            _childPlug = plug.child(i)
            _result.append(_childPlug.asDouble())
        return _result

    @scale.setter
    def scale(self, value):
        plug = self.fnDependencyNode.findPlug('scale')
        # type is om.MFn.kAttribute3Double
        for i in range(3):
            _childPlug = plug.child(i)
            _childPlug.setDouble(value[i])

    @property
    def rotateOrder(self):
        plug = self.fnDependencyNode.findPlug('rotateOrder')
        return plug.asInt()

    @rotateOrder.setter
    def rotateOrder(self, value):
        plug = self.fnDependencyNode.findPlug('rotateOrder')
        # type is om.MFn.kEnumAttribute
        plug.setInt(value)


    @classmethod
    def matrixToList(cls, matrix):
        util = om.MScriptUtil()

        matrixList = []

        for row in range(4):
            rowList = []
            for column in range(3):
                rowList.append(util.getDoubleArrayItem(matrix[row], column))

            matrixList.append(rowList)

        return matrixList

    @classmethod
    def makeShortNameUnique(cls, name):
        _itDag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kTransform)
        _dag = om.MDagPath()
        _numDuplicates = 0
        _possibleName = name

        while not _itDag.isDone():
            if _numDuplicates:
                _possibleName = '{0}{1}'.format(name, _numDuplicates)
            if _itDag.partialPathName() == _possibleName:
                _numDuplicates += 1
            _itDag.next()

        if _numDuplicates:
            return '{0}{1}'.format(name, _numDuplicates)
        else:
            return name

    def hasParent(self, parent):
        if isinstance(parent, DependencyNode):
            parent = parent.mObject
        elif isinstance(parent, basestring):
            parent = self.stringToMObject(parent)

        if parent:
            return self.fnDagNode.hasParent(parent)
        else:
            return False

    def hasChild(self, child):
        if isinstance(child, DependencyNode):
            child = child.mObject
        elif isinstance(child, basestring):
            child = self.stringToMObject(child)

        if child:
            return self.fnDagNode.hasChild(child)
        else:
            return False

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


class Shape(DagNode):
    def __init__(self, name):
        super(Shape, self).__init__(name)

    @property
    def transform(self):
        # return this shape's transform
        _dag = om.MDagPath(self.dagPath)
        return DagNode(_dag.transform())


class Mesh(Shape):
    def __init__(self, name):
        super(Mesh, self).__init__(name)

        try:
            self.fnMesh = om.MFnMesh(self.mObject)
        except RuntimeError:
            raise RuntimeError('Given object type is not compatible. Did you pass a kTransform type?')

    @property
    def getSkinCluster(self):

        itDG = om.MItDependencyGraph(self.mObject, om.MFn.kSkinClusterFilter, om.MItDependencyGraph.kUpstream,
                                     om.MItDependencyGraph.kDepthFirst, om.MItDependencyGraph.kNodeLevel)

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


class Curve(Shape):
    def __init__(self, name):
        super(Curve, self).__init__(name)

    @property
    def fnNurbsCurve(self):
        return om.MFnNurbsCurve(self.dagPath)

    def getPoints(self, space='world'):
        space = SPACES.get(space)
        if not space:
            raise ValueError('Unsupported space type \'{0}\' given.'.format(space))

        _cvs = om.MPointArray()
        self.fnNurbsCurve.getCVs(_cvs, space)

        return _cvs

    def setPoints(self, points, space='world'):
        space = SPACES.get(space)
        if not space:
            raise ValueError('Unsupported space type \'{0}\' given.'.format(space))

        _points = om.MPointArray()
        _numCVs = self.fnNurbsCurve.numCVs()

        if isinstance(points, list):
            if len(points) != _numCVs:
                raise ValueError('The number of points given does not match the number of CV points.')
            for i in xrange(len(points)):
                _points.append(om.MPoint(*points[i]))
        elif isinstance(points, om.MPointArray):
            if points.length() != _numCVs:
                raise ValueError('The number of points given does not match the number of CV points.')
            _points = points

        self.fnNurbsCurve.setCVs(_points, space)
        self.fnNurbsCurve.updateCurve()

    @classmethod
    def createLinearCurve(cls, points):
        om.MGlobal.clearSelectionList()
        _points = om.MPointArray()
        _knots = om.MDoubleArray()
        if not isinstance(points, om.MPointArray):
            for i in xrange(len(points)):
                _points.append(om.MPoint(*points[i]))
                _knots.append(i)
        else:
            _points = points

        _newCurveMObj = om.MFnNurbsCurve().create(_points, _knots, 1, om.MFnNurbsCurve.kOpen, False, False)

        return _newCurveMObj


class SkinCluster(DependencyNode):
    def __init__(self, name):
        super(SkinCluster, self).__init__(name)

    @property
    def fnSkinCluster(self):
        return omAnim.MFnSkinCluster(self.mObject)

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
        raise RuntimeError('pruneWeights is not yet implemented')

    def getWeightDictionary(self):
        raise RuntimeError('getWeightDictionary is not yet implemented')
