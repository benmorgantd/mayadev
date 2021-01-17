import sys
import inspect
import json

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as omAnim

# TODO: remove dependencies from outside this file
from bmaya.core import boundingBox

__all__ = [className for className, obj in inspect.getmembers(sys.modules[__name__]) if inspect.isclass(obj)]

# CONSTANTS #

ROTATE_ORDERS = [om.MEulerRotation.kXYZ, om.MEulerRotation.kYZX,
                 om.MEulerRotation.kZXY, om.MEulerRotation.kXZY,
                 om.MEulerRotation.kYXZ, om.MEulerRotation.kZYX]

DISPLAY_COLORS = {'black': 1, 'grey': 3, 'blue': 6, 'pink': 9, 'red': 13, 'lime': 14, 'darkblue': 15, 'white': 16,
                  'yellow': 17, 'green': 23}

SPACES = {'world': om.MSpace.kWorld, 'object': om.MSpace.kObject, 'local': om.MSpace.kTransform}


class Connections(object):
    def __init__(self, plug):

        if plug.isConnected():
            self.inputs = plug.connectedTo(True, False)
            self.outputs = plug.connectedTo(False, True)


class DependencyNode(object):
    def __init__(self, seed):
        self._initialized = False
        # I think many OpenMaya objects inherit from MObject, so we may want to directly check types instead
        if isinstance(seed, om.MObject):
            self.mObject = om.MObject(seed)
        elif isinstance(seed, basestring):
            self.mObject = self.stringToMObject(seed)
        else:
            raise RuntimeError(
                'Cannot initialize a mayanode with the given seed {0} of type {1}'.format(seed, type(seed)))

        self.fnDependencyNode = om.MFnDependencyNode(self.mObject)
        self._initialized = True

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

    # def __getattr__(self, attribute):
    #     # print('in getattr for {0}'.format(attribute))
    #     if attribute != '_initialized' and hasattr(self, '_initialized') and self._initialized:
    #         if hasattr(self, 'fnDependencyNode') and self.fnDependencyNode.hasAttribute(attribute):
    #             plug = self.findPlug(attribute)
    #             attributeMObj = plug.attribute()
    #             plugType = attributeMObj.apiType()
    #
    #             if plugType == om.MFn.kDoubleLinearAttribute:
    #                 return plug.asDouble()
    #             elif plugType == om.MFn.kDoubleAngleAttribute:
    #                 return plug.asMAngle()
    #             elif plugType == om.MFn.kNumericAttribute:
    #                 # get data type
    #                 fnNumericAttr = om.MFnNumericAttribute(attributeMObj)
    #                 unitType = fnNumericAttr.unitType()
    #                 if unitType == 1:
    #                     return plug.asBool()
    #                 elif unitType == 3:
    #                     return plug.asChar()
    #                 elif unitType == 4:
    #                     return plug.asShort()
    #                 elif unitType == 7:
    #                     return plug.asLong()
    #                 elif unitType == 8:
    #                     return plug.asInt()
    #                 elif unitType in [13, 14]:
    #                     return plug.asFloat()
    #                 else:
    #                     raise AttributeError('The given MFnNumericData type {0} is not supported.'.format(unitType))
    #             elif plugType == om.MFn.kAttribute3Double:
    #                 _result = []
    #                 for i in range(plug.numChildren()):
    #                     _childPlug = plug.child(i)
    #                     _result.append(_childPlug.asDouble())
    #                 return _result
    #             elif plugType == om.MFn.kTypedAttribute:
    #                 fnTypedAttr = om.MFnTypedAttribute(attributeMObj)
    #                 typedAttrType = fnTypedAttr.attrType()
    #                 if typedAttrType == 5:
    #                     # kMatrix type. Get matrix data without the MFnTransform
    #                     if plug.isArray():
    #                         # worldMatrix, worldInverseMatrix, parentMatrix, parentInverseMatrix
    #                         _childPlug = plug.elementByLogicalIndex(0)
    #                         fnMatrixData = om.MFnMatrixData(_childPlug.asMObject())
    #                         fnAttribute = om.MFnAttribute(_childPlug.attribute())
    #                         return fnMatrixData.transformation()
    #                     else:
    #                         fnAttribute = om.MFnAttribute(plug.attribute())
    #                         # matrix, inverseMatrix, xformMatrix
    #                         _util = om.MScriptUtil()
    #                         _fnMatrixData = om.MFnMatrixData(plug.asMObject())
    #                         return _fnMatrixData.transformation()
    #
    #                 raise AttributeError('getattr is currently not supported for this attribute type.')
    #             elif plugType == om.MFn.kEnumAttribute:
    #                 return plug.asInt()
    #             elif plugType == om.MFn.kStringData:
    #                 return plug.asString()
    #             elif plugType == om.MFn.kMessageAttribute:
    #                 raise AttributeError('getattr is currently not supported for this attribute type.')
    #             else:
    #                 raise AttributeError('getattr is currently not supported for this attribute type.')
    #         else:
    #             return super(DependencyNode, self).__getattribute__(attribute)
    #     else:
    #         return super(DependencyNode, self).__getattribute__(attribute)

    # def __setattr__(self, attribute, value):
    #     # print('in setattr for {0} > {1}'.format(attribute, value))
    #     if attribute != '_initialized' and hasattr(self, '_initialized') and self._initialized:
    #         if hasattr(self, 'fnDependencyNode') and self.fnDependencyNode.hasAttribute(attribute):
    #             plug = self.findPlug(attribute)
    #             attributeMObj = plug.attribute()
    #             plugType = attributeMObj.apiType()
    #             fnAttr = om.MFnAttribute(attributeMObj)
    #
    #             if not plugType == om.MFn.kTypedAttribute and not fnAttr.isWritable():
    #                 raise AttributeError('Given attribute {0} is not writable.'.format(fnAttr.name()))
    #
    #             if plugType == om.MFn.kDoubleLinearAttribute:
    #                 plug.setDouble(value)
    #             elif plugType == om.MFn.kDoubleAngleAttribute:
    #                 plug.setMAngle(value)
    #             elif plugType == om.MFn.kNumericAttribute:
    #                 # get data type
    #                 fnNumericAttr = om.MFnNumericAttribute(attributeMObj)
    #                 unitType = fnNumericAttr.unitType()
    #                 if unitType == 1:
    #                     plug.setBool(value)
    #                 elif unitType == 3:
    #                     plug.setChar(value)
    #                 elif unitType == 4:
    #                     plug.setShort(value)
    #                 elif unitType == 7:
    #                     plug.setLong(value)
    #                 elif unitType == 8:
    #                     plug.setInt(value)
    #                 elif unitType in [13, 14]:
    #                     plug.setFloat(value)
    #                 else:
    #                     raise AttributeError('The given MFnNumericData type {0} is not supported.'.format(unitType))
    #             elif plugType == om.MFn.kAttribute3Double:
    #                 if isinstance(value, om.MQuaternion):
    #                     _eulerRot = value.asEulerRotation()
    #                     _eulerRot = _eulerRot.reorder(ROTATE_ORDERS[self.rotateOrder])
    #                     value = _eulerRot
    #                 for i in range(plug.numChildren()):
    #                     _childPlug = plug.child(i)
    #                     _childPlug.setDouble(value[i])
    #
    #             elif plugType == om.MFn.kTypedAttribute:
    #                 fnTypedAttr = om.MFnTypedAttribute(attributeMObj)
    #                 typedAttrType = fnTypedAttr.attrType()
    #                 if typedAttrType == 5:
    #                     # Matrix attributes are not writable! You cannot write to them, only read from them.
    #                     # They cannot be directly connected, which means their values cannot be set
    #                     # outside of a node's compute function.
    #                     # Instead, read the data from the matrix and set attributes instead...
    #                     # NOTE: you cannot set this attribute on anything but self.matrix
    #
    #                     if fnTypedAttr.isArray():
    #                         raise RuntimeError(
    #                             '{0}.DependencyNode : setattr is unsupported for Matrix Array attribute {1}'.format(
    #                                 __name__, plug.name()))
    #
    #                     _xformMatrix = om.MTransformationMatrix(value)
    #                     _translateVector = _xformMatrix.getTranslation(om.MSpace.kWorld)
    #                     _rotateQuaternion = _xformMatrix.rotation()
    #                     _scaleUtil = om.MScriptUtil()
    #                     _scaleUtil.createFromDouble(1.0, 1.0, 1.0)
    #                     _scalePtr = _scaleUtil.asDoublePtr()
    #                     _xformMatrix.getScale(_scalePtr, om.MSpace.kWorld)
    #                     _scale = [_scaleUtil.getDoubleArrayItem(_scalePtr, 0),
    #                               _scaleUtil.getDoubleArrayItem(_scalePtr, 1),
    #                               _scaleUtil.getDoubleArrayItem(_scalePtr, 2)]
    #                     _shearUtil = om.MScriptUtil()
    #                     _shearPtr = _shearUtil.asDoublePtr()
    #                     _xformMatrix.getShear(_shearPtr, om.MSpace.kTransform)
    #                     _shear = [_shearUtil.getDoubleArrayItem(_shearPtr, 0),
    #                               _shearUtil.getDoubleArrayItem(_shearPtr, 1),
    #                               _shearUtil.getDoubleArrayItem(_shearPtr, 2)]
    #
    #                     setattr(self, 'translate', _translateVector)
    #                     setattr(self, 'rotate', _rotateQuaternion)
    #                     setattr(self, 'scale', _scale)
    #                     setattr(self, 'shear', _shear)
    #
    #
    #             elif plugType == om.MFn.kEnumAttribute:
    #                 plug.setInt(value)
    #             elif plugType == om.MFn.kStringData:
    #                 plug.setString(value)
    #             elif plugType == om.MFn.kMessageAttribute:
    #                 raise AttributeError('setattr is currently not supported for this attribute type.')
    #             else:
    #                 raise AttributeError('setattr is currently not supported for this attribute type.')
    #         else:
    #             # We're calling __setattr__ before the class has been fully initialized
    #             super(DependencyNode, self).__setattr__(attribute, value)
    #     else:
    #         super(DependencyNode, self).__setattr__(attribute, value)

    def get(self, attribute):
        if hasattr(self, 'fnDependencyNode') and self.fnDependencyNode.hasAttribute(attribute):
            plug = self.findPlug(attribute)
            attributeMObj = plug.attribute()
            plugType = attributeMObj.apiType()

            if plugType == om.MFn.kDoubleLinearAttribute:
                return plug.asDouble()
            elif plugType == om.MFn.kDoubleAngleAttribute:
                return plug.asMAngle()
            elif plugType == om.MFn.kNumericAttribute:
                # get data type
                fnNumericAttr = om.MFnNumericAttribute(attributeMObj)
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
                fnTypedAttr = om.MFnTypedAttribute(attributeMObj)
                typedAttrType = fnTypedAttr.attrType()
                if typedAttrType == 5:
                    # kMatrix type. Get matrix data without the MFnTransform
                    if plug.isArray():
                        # worldMatrix, worldInverseMatrix, parentMatrix, parentInverseMatrix
                        _childPlug = plug.elementByLogicalIndex(0)
                        fnMatrixData = om.MFnMatrixData(_childPlug.asMObject())
                        return fnMatrixData.transformation()
                    else:
                        # matrix, inverseMatrix, xformMatrix
                        _fnMatrixData = om.MFnMatrixData(plug.asMObject())
                        return _fnMatrixData.transformation()

                raise AttributeError('getattr is currently not supported for this attribute type.')
            elif plugType == om.MFn.kEnumAttribute:
                return plug.asInt()
            elif plugType == om.MFn.kStringData:
                return plug.asString()
            elif plugType == om.MFn.kMessageAttribute:
                raise AttributeError('getattr is currently not supported for this attribute type.')
            else:
                raise AttributeError('getattr is currently not supported for this attribute type.')

    def set(self, attribute, value):
        if hasattr(self, 'fnDependencyNode') and self.fnDependencyNode.hasAttribute(attribute):
            plug = self.findPlug(attribute)
            attributeMObj = plug.attribute()
            plugType = attributeMObj.apiType()
            fnAttr = om.MFnAttribute(attributeMObj)

            if not plugType == om.MFn.kTypedAttribute and not fnAttr.isWritable():
                raise AttributeError('Given attribute {0} is not writable.'.format(fnAttr.name()))

            if plugType == om.MFn.kDoubleLinearAttribute:
                plug.setDouble(value)
            elif plugType == om.MFn.kDoubleAngleAttribute:
                plug.setMAngle(value)
            elif plugType == om.MFn.kNumericAttribute:
                # get data type
                fnNumericAttr = om.MFnNumericAttribute(attributeMObj)
                unitType = fnNumericAttr.unitType()
                if unitType == 1:
                    plug.setBool(value)
                elif unitType == 3:
                    plug.setChar(value)
                elif unitType == 4:
                    plug.setShort(value)
                elif unitType == 7:
                    plug.setLong(value)
                elif unitType == 8:
                    plug.setInt(value)
                elif unitType in [13, 14]:
                    plug.setFloat(value)
                else:
                    raise AttributeError('The given MFnNumericData type {0} is not supported.'.format(unitType))
            elif plugType == om.MFn.kAttribute3Double:
                if isinstance(value, om.MQuaternion):
                    _eulerRot = value.asEulerRotation()
                    _eulerRot = _eulerRot.reorder(ROTATE_ORDERS[self.rotateOrder])
                    value = _eulerRot
                for i in range(plug.numChildren()):
                    _childPlug = plug.child(i)
                    _childPlug.setDouble(value[i])

            elif plugType == om.MFn.kTypedAttribute:
                fnTypedAttr = om.MFnTypedAttribute(attributeMObj)
                typedAttrType = fnTypedAttr.attrType()
                if typedAttrType == 5:
                    # Matrix attributes are not writable! You cannot write to them, only read from them.
                    # They cannot be directly connected, which means their values cannot be set
                    # outside of a node's compute function.
                    # Instead, read the data from the matrix and set attributes instead...
                    # NOTE: you cannot set this attribute on anything but self.matrix

                    if fnTypedAttr.isArray():
                        raise RuntimeError(
                            '{0}.DependencyNode : setattr is unsupported for Matrix Array attribute {1}'.format(
                                __name__, plug.name()))

                    _xformMatrix = om.MTransformationMatrix(value)
                    _translateVector = _xformMatrix.getTranslation(om.MSpace.kWorld)
                    _rotateQuaternion = _xformMatrix.rotation()
                    _scaleUtil = om.MScriptUtil()
                    _scaleUtil.createFromDouble(1.0, 1.0, 1.0)
                    _scalePtr = _scaleUtil.asDoublePtr()
                    _xformMatrix.getScale(_scalePtr, om.MSpace.kWorld)
                    _scale = [_scaleUtil.getDoubleArrayItem(_scalePtr, 0), _scaleUtil.getDoubleArrayItem(_scalePtr, 1),
                              _scaleUtil.getDoubleArrayItem(_scalePtr, 2)]
                    _shearUtil = om.MScriptUtil()
                    _shearPtr = _shearUtil.asDoublePtr()
                    _xformMatrix.getShear(_shearPtr, om.MSpace.kTransform)
                    _shear = [_shearUtil.getDoubleArrayItem(_shearPtr, 0), _shearUtil.getDoubleArrayItem(_shearPtr, 1),
                              _shearUtil.getDoubleArrayItem(_shearPtr, 2)]

                    setattr(self, 'translate', _translateVector)
                    setattr(self, 'rotate', _rotateQuaternion)
                    setattr(self, 'scale', _scale)
                    setattr(self, 'shear', _shear)


            elif plugType == om.MFn.kEnumAttribute:
                plug.setInt(value)
            elif plugType == om.MFn.kStringData:
                plug.setString(value)
            elif plugType == om.MFn.kMessageAttribute:
                raise AttributeError('setattr is currently not supported for this attribute type.')
            else:
                raise AttributeError('setattr is currently not supported for this attribute type.')

    def findPlug(self, plugString):
        if self.fnDependencyNode.hasAttribute(plugString):
            return self.fnDependencyNode.findPlug(plugString, False)
        else:
            raise AttributeError('Object {0} has no plug {1}'.format(self, plugString))

    @classmethod
    def connect(cls, sourcePlug, destPlug):
        _sourceFnAttr = om.MFnAttribute(sourcePlug.attribute())
        _destFnAttr = om.MFnAttribute(destPlug.attribute())

        if not _sourceFnAttr.isConnectable() or not _destFnAttr.isConnectable():
            raise ValueError('A given plug is not connectable.')

        _sourceFnAttr.setWritable(True)
        _destFnAttr.setWritable(True)

        _dgMod = om.MDGModifier()
        _dgMod.connect(sourcePlug, destPlug)
        _dgMod.doIt()

    # @property
    # def fnDependencyNode(self):
    #     return om.MFnDependencyNode(self.mObject)

    @property
    def name(self):
        return self.fnDependencyNode.name()

    @name.setter
    def name(self, value):
        self.fnDependencyNode.setName(self.makeShortNameUnique(value))

    '''
    @property
    def attributes(self):

        _attributes = []
        for i in xrange(self.fnDependencyNode.attributeCount()):
            attributeMObject = self.fnDependencyNode.attribute(i)
            plug = self.findPlug(attributeMObject)
            # These args return us the long name of the attribute without the node
            _attributes.append(plug.partialName(False, False, False, False, False, True))

        return _attributes
    '''

    @classmethod
    def stringToMObject(cls, str):
        _mObject = None
        if isinstance(str, basestring):
            try:
                # we only want to deal in objects that have unique names
                _sel = om.MSelectionList()
                _sel.add(str)
                _mObject = _sel.getDependNode(0)
            except RuntimeError:
                raise RuntimeError('Object {0} does not exist or is not unique.'.format(str))
        else:
            return None

        return _mObject


class DagNode(DependencyNode):
    def __init__(self, seed):
        super(DagNode, self).__init__(seed)

        self._initialized = False

        _sel = om.MSelectionList()
        try:
            _sel.add(self.fnDependencyNode.name())
            _dag = _sel.getDagPath(0)
            self.dagPath = _dag
        except RuntimeError:
            # object's short name is not unique. Iterate through the dag until we find this mObject
            raise RuntimeError('Object short name is not unique')

        self.fnDagNode = om.MFnDagNode(self.dagPath)

        self._initialized = True

    def __repr__(self):
        return self.dagPath.fullPathName()

    def __str__(self):
        return self.dagPath.fullPathName()

    def __add__(self, other):
        return self.dagPath.fullPathName() + other

    def __radd__(self, other):
        return other + self.dagPath.fullPathName()

    # @property
    # def fnDependencyNode(self):
    #     try:
    #         _fnDependencyNode = om.MFnDependencyNode(self.mObject)
    #         return _fnDependencyNode
    #     except RuntimeError:
    #         raise RuntimeError('Given object type is not compatible')

    # @property
    # def fnDagNode(self):
    #     return om.MFnDagNode(self.dagPath)

    @property
    def name(self):
        return self.dagPath.fullPathName()

    @name.setter
    def name(self, value):
        self.fnDependencyNode.setName(value)

    @property
    def shortName(self):
        return self.dagPath.partialPathName()

    @shortName.setter
    def shortName(self, value):
        self.fnDependencyNode.setName(value)

    # @property
    # def dagPath(self):
    #     _sel = om.MSelectionList()
    #     # _fnDependencyNode = om.MFnDependencyNode(self.mObject)
    #     # TODO: this doesn't work with shortName duplicates in a scene
    #     try:
    #         _sel.add(self.fnDependencyNode.name())
    #         _dag = om.MDagPath()
    #         _sel.getDagPath(0, _dag)
    #         return _dag
    #     except RuntimeError:
    #         # object's short name is not unique. Iterate through the dag until we find this mObject
    #         raise RuntimeError('Object short name is not unique')

    def getParent(self):
        # return the Transform of the parent
        if self.dagPath.length() > 1:
            return DagNode(self.fnDagNode.parent(0))
        else:
            return None

    def setParent(self, newParent):
        if not newParent:
            raise ValueError(
                'Parenting to world not currently possible')  # if self.dagPath.length() > 1:  #     _currentParent = self.getParent()  #     while self.getParent():  #         _newParent = _currentParent.getParent()  #         self.setParent(_currentParent)  # else:  #     om.MGlobal.displayInfo('{0} is already a child of world'.format(self))

            # return
        elif not isinstance(newParent, DagNode):
            newParent = DagNode(newParent)

        _currentParent = self.getParent()
        if not _currentParent:
            newParent.fnDagNode.addChild(self.mObject)
        elif _currentParent and _currentParent.mObject != newParent.mObject:
            newParent.fnDagNode.addChild(self.mObject)
        else:
            om.MGlobal.displayWarning('{0} is already the parent of {1}'.format(newParent.shortName, self.shortName))

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
                _currentMObject = _itDag.currentNode()
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
    def worldRotation(self):
        quat = om.MQuaternion()
        self.fnTransform.getRotation(quat, om.MSpace.kWorld)
        return quat

    @worldRotation.setter
    def worldRotation(self, rotation):
        self.fnTransform.setRotation(rotation, om.MSpace.kWorld)

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
        if self.getParent():
            return self.worldPosition - self.getParent().worldPosition
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
            _dag.extendToShape(0)
            # check what the shape's type is
            _shapeMObj = _dag.node()
            if _shapeMObj.hasFn(om.MFn.kMesh):
                _mesh = Mesh(_shapeMObj)
                if not _mesh.fnDagNode.isIntermediateObject:
                    return _mesh
            elif _shapeMObj.hasFn(om.MFn.kNurbsCurve):
                _curve = Curve(_shapeMObj)
                if not _curve.fnDagNode.isIntermediateObject:
                    return _curve
            # TODO support more shape types
            else:
                return Shape(_shapeMObj)

        except RuntimeError:
            # no shape
            return None

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

    def lockAttr(self, attr):
        if self.fnDependencyNode.hasAttribute(attr):
            plug = self.findPlug(attr)
            plug.setLocked(True)

    def unlockAttr(self, attr):
        if self.fnDependencyNode.hasAttribute(attr):
            plug = self.findPlug(attr)
            plug.setLocked(False)

    def hideAttr(self, attr):
        if self.fnDependencyNode.hasAttribute(attr):
            plug = self.findPlug(attr)
            plug.setKeyable(False)

    def unhideAttr(self, attr):
        if self.fnDependencyNode.hasAttribute(attr):
            plug = self.findPlug(attr)
            plug.setKeyable(True)

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
    def __init__(self, seed):
        super(Shape, self).__init__(seed)

    @property
    def transform(self):
        # return this shape's transform
        _dag = om.MDagPath(self.dagPath)
        return DagNode(_dag.transform())


class Mesh(Shape):
    def __init__(self, seed):
        super(Mesh, self).__init__(seed)

    @property
    def fnMesh(self):
        try:
            _fnMesh = om.MFnMesh(self.mObject)
            return _fnMesh
        except RuntimeError:
            raise RuntimeError('Given object type is not compatible. Is the object a polygonal mesh?')

    def getSkinCluster(self):

        itDG = om.MItDependencyGraph(self.mObject, om.MFn.kSkinClusterFilter, om.MItDependencyGraph.kUpstream,
                                     om.MItDependencyGraph.kDepthFirst, om.MItDependencyGraph.kNodeLevel)

        if itDG.isDone():
            # No skin cluster. Are you sure you passed a mesh?
            return None

        skinClusterMObjArray = om.MObjectArray()

        while not itDG.isDone():
            currentNode = itDG.currentNode()
            skinClusterMObjArray.append(currentNode)

            itDG.next()

        # Return the first item in the array
        return SkinCluster(skinClusterMObjArray[0])


class Curve(Shape):
    def __init__(self, seed):
        super(Curve, self).__init__(seed)

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

    def setPoints(self, points, space='world', cvLimit=128):
        space = SPACES.get(space)
        if not space:
            raise ValueError('Unsupported space type \'{0}\' given.'.format(space))

        _points = om.MPointArray()
        _numCVs = self.fnNurbsCurve.numCVs()

        if isinstance(points, list):
            for i in xrange(len(points)):
                _points.append(om.MPoint(*points[i]))
            _lastPoint = _points[len(points) - 1]
            for j in xrange(len(points), cvLimit):
                _points.append(om.MPoint(_lastPoint))

        elif isinstance(points, om.MPointArray):
            _points = points
            # TODO: this isn't fully supported yet
            # if points.length() != _numCVs:
            #     raise ValueError('The number of points given does not match the number of CV points.')

        self.fnNurbsCurve.setCVs(_points, space)
        self.fnNurbsCurve.updateCurve()

    def setupBoundingBox(self):

        sceneBoundingBox = boundingBox.getSceneBoundingBox()

        if sceneBoundingBox.width() < 0.001:
            cmds.xform(self.shape + '.cv[0:]', scale=(1, 1, 1))
        else:
            cmds.xform(self.shape + '.cv[0:]', scale=(
                sceneBoundingBox.width() + .1, sceneBoundingBox.height() + .1, sceneBoundingBox.depth() + .1))

        cmds.xform(self.shape + '.cv[0:]', translation=boundingBox.getBoundingBoxCenter(sceneBoundingBox),
                   relative=True)


class LinearCurve(Curve):
    def __init__(self, seed, points, forceCvCount=False):
        if seed:
            super(LinearCurve, self).__init__(seed)
        else:
            om.MGlobal.clearSelectionList()
            _points = om.MPointArray()
            _knots = om.MDoubleArray()

            if not isinstance(points, om.MPointArray):
                for i in xrange(len(points)):
                    _points.append(om.MPoint(*points[i]))
                    _knots.append(i)

                if forceCvCount:
                    # Force the cv count to be the same on rig control curves so their shape can be easily changed
                    _lastPoint = _points[_points.length() - 1]
                    for j in range(len(points), forceCvCount):
                        # make all the remaining CVs equal to the same as the last point
                        _points.append(om.MPoint(_lastPoint))
                        _knots.append(j)
            else:
                _points = points

            _newCurveMObj = om.MFnNurbsCurve().create(_points, _knots, 1, om.MFnNurbsCurve.kOpen, False, False)
            super(LinearCurve, self).__init__(_newCurveMObj)

    def attachBorderCVsToTransform(self, startTransform, endTransform):
        if not self.getPoints().length() == 0:
            raise RuntimeError('This function can only be run on a curve with 2 points (a line).')

        # decompA = cmds.shadingNode('decomposeMatrix', asUtility=True, name=name + '_decompMatrixA')
        # decompB = cmds.shadingNode('decomposeMatrix', asUtility=True, name=name + '_decompMatrixB')
        # cmds.connectAttr(pointA + '.worldMatrix[0]', decompA + '.inputMatrix')
        # cmds.connectAttr(pointB + '.worldMatrix[0]', decompB + '.inputMatrix')
        #
        # cmds.connectAttr(decompA + '.outputTranslate', crvShape + '.controlPoints[0]')
        # cmds.connectAttr(decompB + '.outputTranslate', crvShape + '.controlPoints[1]')
        #
        # cmds.parent(crv, parentNode, a=1)
        # cmds.setAttr(crv + '.inheritsTransform', 0)
        # cmds.setAttr(crvShape + '.template', 1)
        #
        # cmds.xform(crv, translation=(0, 0, 0), a=1, ws=1)
        # cmds.xform(crv, rotation=(0, 0, 0), a=1, ws=1)
        #
        # cmds.select(cl=1)

        return


class SkinCluster(DependencyNode):
    def __init__(self, seed):
        super(SkinCluster, self).__init__(seed)

    @property
    def fnSkinCluster(self):
        return omAnim.MFnSkinCluster(self.mObject)

    @property
    def outputGeometry(self):
        outputGeometryArrayPlug = self.findPlug('outputGeometry')
        outputGeometryPlug = outputGeometryArrayPlug.elementByPhysicalIndex(0)
        connectedMeshes = outputGeometryPlug.connectedTo(False, True)
        # return the first connected mesh
        return Mesh(connectedMeshes[0].node())

    @property
    def influenceObjects(self):
        _influenceObjects = self.fnSkinCluster.influenceObjects()
        return _influenceObjects

    @property
    def influenceCount(self):
        return len(self.influenceObjects)

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
        _weights = om.MDoubleArray()

        if not components:
            components = om.MObject()
        else:
            assert isinstance(components, om.MObject)

        _outputGeometryDag = self.outputGeometry.dagPath

        # fails at Mesh.dagPath
        _weights = self.fnSkinCluster.getWeights(_outputGeometryDag, components, self.influenceIndices)

        return _weights

    def getWeightDictionary(self):
        '''Return the weight dictionary for the given skin cluster.
        Each influence's short name is followed by its vertex weights.'''

        weightDict = {}

        _weights = self.getWeights()
        _weights = list(_weights)
        _influenceIndices = self.influenceIndices
        _influenceObjects = self.influenceObjects

        numInfluences = self.influenceCount

        for i in xrange(numInfluences):
            # A single influence's weights is its column of the weight matrix
            weightDict[_influenceObjects[i].partialPathName()] = _weights[i:: numInfluences]

        return weightDict

    def setWeights(self, newWeights, components=None):
        if not components:
            components = om.MObject()
        else:
            assert isinstance(components, om.MObject)

        assert isinstance(newWeights, (om.MDoubleArray, list))

        print self.fnSkinCluster.setWeights(self.outputGeometry.dagPath, components, self.influenceIndices, newWeights)

    def pruneWeights(self, maxInfluence=4):
        """Sets the weights for each vertex to the average of its neighbors."""

        originalSel = om.MGlobal.getActiveSelectionList()

        sel = om.MSelectionList()
        sel.add(self.outputGeometry + '.vtx[:]')

        _dag = om.MDagPath()
        _dag, selectedComponents = sel.getComponent(0)
        meshTransform = DagNode(_dag.node())

        oldWeights = self.getWeights(components=selectedComponents)

        # newWeights just starts as a copy of oldWeights
        newWeights = om.MDoubleArray(oldWeights)

        # iterate over the selected verts
        itVerts = om.MItMeshVertex(meshTransform.dagPath, selectedComponents)
        i = 0
        numOverInfluenced = 0
        infCount = self.influenceCount

        while not itVerts.isDone():
            vertWeightSliceStart = i * infCount
            vertWeights = list(newWeights[vertWeightSliceStart: vertWeightSliceStart + infCount])
            # Filter is nearly instant.
            nonZeroCount = len(filter(lambda w: w > 0.0, vertWeights))

            if nonZeroCount > maxInfluence:
                numOverInfluenced += 1
                # makes the weights for the closest vertex equal to the outer vertex
                newWeights[vertWeightSliceStart: vertWeightSliceStart + infCount] = self.pruneVertexWeightList(
                    vertWeights, influenceCount=infCount, maxInfluence=maxInfluence)

            i += 1
            itVerts.next()

        if numOverInfluenced:
            self.setWeights(newWeights, components=selectedComponents)

        om.MGlobal.setActiveSelectionList(originalSel)

        om.MGlobal.displayInfo(
            'Pruned {0} over-influenced vertices from {1}.'.format(numOverInfluenced, meshTransform.shortName))

    def smoothWeights(self, components):
        raise RuntimeError('smoothWeights is not yet implemented')

    @classmethod
    def pruneVertexWeightList(cls, weights, influenceCount, maxInfluence=4, normalize=True):
        """Prunes the given list to have only four non-zero values"""

        sortedWeights = weights
        sortedWeights.sort(reverse=True)
        prunedWeights = [0.0] * influenceCount

        if maxInfluence > 1:
            for i in range(influenceCount):
                if i > (maxInfluence - 1):
                    prunedWeights[weights.index(sortedWeights[i])] = 0.0
                else:
                    prunedWeights[weights.index(sortedWeights[i])] = sortedWeights[i]
        else:
            prunedWeights[weights.index(sortedWeights[0])] = sortedWeights[0]

        if normalize:
            prunedWeightsSum = sum(prunedWeights)
            prunedWeights = [value / prunedWeightsSum for value in prunedWeights]

        return prunedWeights
