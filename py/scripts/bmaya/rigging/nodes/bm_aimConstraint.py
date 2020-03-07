import maya.OpenMaya as om
import maya.OpenMayaMPx as omMPx


class bmAimConstraint(omMPx.MPxConstraint):
    """Aim an object down an arbitrary with or without an up vector.
    
    Attributes:
        nodeId (MTypeId): The unique id for this node
        objectMatrix (MObject): The worldMatrix of the object you want driven
        targetObjectMatrix (MObject): The worldMatrix of the object to aim at
        upObjectMatrix (MObject): The matrix of the object to serve as the up vector
        offsetMatrix (MObject): The matrix of the object after connections get made
        downAxis (MObject): The axis to aim down
        upAxis (MObject): The axis to orient the up axis to
        rotateOrder (MObject): The rotate order to use in the euler conversion
        ouputRotate (MObject): The resulting euler rotation
    """

    ROTATION_ORDERS = [om.MEulerRotation.kXYZ, om.MEulerRotation.kYZX, 
                      om.MEulerRotation.kZXY, om.MEulerRotation.kXZY,
                      om.MEulerRotation.kYXZ, om.MEulerRotation.kZYX]

    nodeId = om.MTypeId(0x50218)

    # input attributes
    objectMatrix = om.MObject()
    upObjectMatrix = om.MObject()
    targetObjectMatrix = om.MObject()
    offsetMatrix = om.MObject()

    downAxis = om.MObject()
    upAxis = om.MObject()
    rotateOrder = om.MObject()
    upVectorType = om.MObject()

    # output attribute
    outputRotate = om.MObject()

    outputRotateX = om.MObject()
    outputRotateY = om.MObject()
    outputRotateZ = om.MObject()

    def compute(self, plug, dataBlock):
        """Maya calls your node's Mpxcompute() method when it determines that 
        one of your node's output attributes needs to be re-computed. """

        if plug != bmAimConstraint.outputRotate:
            return om.MStatus.kUnknownParameter

        objectMatrix = dataBlock.inputValue(bmAimConstraint.objectMatrix).asMatrix()
        upObjectMatrix = dataBlock.inputValue(bmAimConstraint.upObjectMatrix).asMatrix()
        targetObjectMatrix = dataBlock.inputValue(bmAimConstraint.targetObjectMatrix).asMatrix()
        offsetMatrix = dataBlock.inputValue(bmAimConstraint.offsetMatrix).asMatrix()

        downAxis = int(dataBlock.inputValue(bmAimConstraint.downAxis).asShort())
        upAxis = int(dataBlock.inputValue(bmAimConstraint.upAxis).asShort())
        rotateOrder = int(dataBlock.inputValue(bmAimConstraint.rotateOrder).asShort())
        upVectorType = int(dataBlock.inputValue(bmAimConstraint.upVectorType).asShort())

        # warn if axis are the same
        if downAxis == upAxis or downAxis == (upAxis-3) or (downAxis-3) == upAxis:
            om.MGlobal.displayWarning('The up and down axis are set to the same value.')
        
        objectVector = om.MTransformationMatrix(objectMatrix).getTranslation(om.MSpace.kWorld)
        upObjectVector = om.MTransformationMatrix(upObjectMatrix).getTranslation(om.MSpace.kWorld)
        aimObjectVector = om.MTransformationMatrix(targetObjectMatrix).getTranslation(om.MSpace.kWorld)

        U = (aimObjectVector - objectVector).normal()

        if upVectorType == 1:
            V = om.MGlobal.upAxis()
        elif upVectorType in [2,3,4]:
            # use the orientation of the chosen up object axis as the up vector
            util = om.MScriptUtil()
            V = []
            for column in range(3):
                V.append(util.getDoubleArrayItem(upObjectMatrix[upVectorType - 2], column))
            V = om.MVector(*V)
        else:
            V = (upObjectVector - objectVector).normal()
            
        W = (U ^ V).normal()
        V = (W ^ U).normal()

        M = [U.x, U.y, U.z, 0, 
             V.x, V.y, V.z, 0, 
             W.x, W.y, W.z, 0, 
             0, 0, 0, 1]

        baseMatrix = om.MMatrix()
        om.MScriptUtil.createMatrixFromList(M, baseMatrix)

        # for negative down axis, rotate 180y before reordering rows
        if downAxis in [3,4,5]:
            downAxis -= 3
            r180y = [-1,0,0,0,
                     0,1,0,0,
                     0,0,-1,0,
                     0,0,0,1]

            r180yMatrix = om.MMatrix()
            om.MScriptUtil.createMatrixFromList(r180y, r180yMatrix)
            baseMatrix = r180yMatrix * baseMatrix

        # for negative up axis, rotate 180x before reordering rows
        if upAxis in [3,4,5]:
            upAxis -=3
            r180x = [1,0,0,0,
                     0,-1,0,0,
                     0,0,-1,0,
                     0,0,0,1]

            r180xMatrix = om.MMatrix()
            om.MScriptUtil.createMatrixFromList(r180x, r180xMatrix)
            baseMatrix = r180xMatrix * baseMatrix
            

        # make a matrix R so that R*M is a reordering of the rows of M
        if downAxis == 0 and upAxis == 1:
            # x down y up
            R = [1,0,0,0,
                 0,1,0,0,
                 0,0,1,0,
                 0,0,0,1]
        elif downAxis == 0 and upAxis == 2:
            # x down z up
            R = [1,0,0,0,
                 0,0,-1,0,
                 0,1,0,0,
                 0,0,0,1]
        elif downAxis == 1 and upAxis == 0:
            # y down x up
            R = [0,1,0,0,
                 1,0,0,0,
                 0,0,-1,0,
                 0,0,0,1]
        elif downAxis == 1 and upAxis == 2:
            # y down z up
            R = [0,0,1,0,
                1,0,0,0,
                0,1,0,0,
                0,0,0,1]
        elif downAxis == 2 and upAxis == 0:
            # z down x up
            R = [0,1,0,0,
                0,0,1,0,
                1,0,0,0,
                0,0,0,1]
        elif downAxis == 2 and upAxis == 1:
            # z down y up
            R = [0,0,-1,0,
                0,1,0,0,
                1,0,0,0,
                0,0,0,1]
        else:
            # for when axis get set to the same value
            R = [1,0,0,0,
                0,1,0,0,
                0,0,1,0,
                0,0,0,1]
        

        reorderMatrix = om.MMatrix()
        om.MScriptUtil.createMatrixFromList(R, reorderMatrix)
        # reorder the initial matrix to use the desired down and up axis
        reorderedMatrix = reorderMatrix * baseMatrix

        # # offset the matrix by the original target object's matrix
        finalMatrix = offsetMatrix * reorderedMatrix

        euler = om.MTransformationMatrix(finalMatrix).eulerRotation()
        euler = euler.reorder(bmAimConstraint.ROTATION_ORDERS[rotateOrder])

        # Set output values
        hOutputX = dataBlock.outputValue(bmAimConstraint.outputRotateX)
        hOutputY = dataBlock.outputValue(bmAimConstraint.outputRotateY)
        hOutputZ = dataBlock.outputValue(bmAimConstraint.outputRotateZ)

        hOutputX.setMAngle(om.MAngle(euler.x))
        hOutputY.setMAngle(om.MAngle(euler.y))
        hOutputZ.setMAngle(om.MAngle(euler.z))

        dataBlock.setClean(plug)

        return

def creator():
    # standard creator function for a Maya plugin
    return omMPx.asMPxPtr(bmAimConstraint())

def initialize():
    nAttr = om.MFnNumericAttribute()
    mAttr = om.MFnMatrixAttribute()
    eAttr = om.MFnEnumAttribute()
    uAttr = om.MFnUnitAttribute()

    ### Input Attributes ###

    # OBJECT MATRIX
    bmAimConstraint.objectMatrix = mAttr.create("objectMatrix", "om", om.MFnMatrixAttribute.kDouble)
    mAttr.setKeyable(True)
    mAttr.setWritable(True)
    mAttr.setStorable(True)
    mAttr.setReadable(True)
    bmAimConstraint.addAttribute(bmAimConstraint.objectMatrix)

    # AIM OBJECT MATRIX
    bmAimConstraint.targetObjectMatrix = mAttr.create("targetObjectMatrix", "tm", om.MFnMatrixAttribute.kDouble)
    mAttr.setKeyable(True)
    mAttr.setWritable(True)
    mAttr.setStorable(True)
    mAttr.setReadable(True)
    bmAimConstraint.addAttribute(bmAimConstraint.targetObjectMatrix)

    # UP OBJECT MATRIX
    bmAimConstraint.upObjectMatrix = mAttr.create("upObjectMatrix", "um", om.MFnMatrixAttribute.kDouble)
    mAttr.setKeyable(True)
    mAttr.setWritable(True)
    mAttr.setStorable(True)
    mAttr.setReadable(True)
    bmAimConstraint.addAttribute(bmAimConstraint.upObjectMatrix)

    # OFFSET MATRIX
    bmAimConstraint.offsetMatrix = mAttr.create("offsetMatrix", "off", om.MFnMatrixAttribute.kDouble)
    mAttr.setKeyable(True)
    mAttr.setWritable(True)
    mAttr.setStorable(True)
    mAttr.setReadable(True)
    bmAimConstraint.addAttribute(bmAimConstraint.offsetMatrix)

    # DOWN AXIS
    bmAimConstraint.downAxis = eAttr.create("downAxis", "down")
    eAttr.addField("x", 0)
    eAttr.addField("y", 1)
    eAttr.addField("z", 2)
    eAttr.addField("-x", 3)
    eAttr.addField("-y", 4)
    eAttr.addField("-z", 5)
    eAttr.setDefault("x")
    eAttr.setKeyable(True)
    eAttr.setWritable(True)
    eAttr.setStorable(True)
    eAttr.setReadable(True)
    bmAimConstraint.addAttribute(bmAimConstraint.downAxis)

    # DOWN AXIS
    bmAimConstraint.upAxis = eAttr.create("upAxis", "up")
    eAttr.addField("x", 0)
    eAttr.addField("y", 1)
    eAttr.addField("z", 2)
    eAttr.addField("-x", 3)
    eAttr.addField("-y", 4)
    eAttr.addField("-z", 5)
    eAttr.setDefault("y")
    eAttr.setKeyable(True)
    eAttr.setWritable(True)
    eAttr.setStorable(True)
    eAttr.setReadable(True)
    bmAimConstraint.addAttribute(bmAimConstraint.upAxis)

    # UP VECTOR TYPE
    bmAimConstraint.upVectorType = eAttr.create("upVectorType", "upType")
    eAttr.addField("object", 0)
    eAttr.addField("scene", 1)
    eAttr.addField("upObjectX", 2)
    eAttr.addField("upObjectY", 3)
    eAttr.addField("upObjectZ", 4)
    eAttr.setDefault("object")
    eAttr.setKeyable(True)
    eAttr.setWritable(True)
    eAttr.setStorable(True)
    eAttr.setReadable(True)
    bmAimConstraint.addAttribute(bmAimConstraint.upVectorType)

    # ROTATE ORDER
    bmAimConstraint.rotateOrder = eAttr.create("rotateOrder", "roo")
    eAttr.addField("xyz", 0)
    eAttr.addField("yzx", 1)
    eAttr.addField("zxy", 2)
    eAttr.addField("xzy", 3)
    eAttr.addField("yxz", 4)
    eAttr.addField("zyx", 5)
    eAttr.setDefault("xyz")
    eAttr.setKeyable(False)
    eAttr.setWritable(True)
    eAttr.setStorable(True)
    eAttr.setReadable(True)
    bmAimConstraint.addAttribute(bmAimConstraint.rotateOrder)

    ### Output Attributes ###
    
    # OUTPUT ROTATE
    bmAimConstraint.outputRotateX = uAttr.create('outputRotateX', 'ox', om.MFnUnitAttribute.kAngle)
    bmAimConstraint.outputRotateY = uAttr.create('outputRotateY', 'oy', om.MFnUnitAttribute.kAngle)
    bmAimConstraint.outputRotateZ = uAttr.create('outputRotateZ', 'oz', om.MFnUnitAttribute.kAngle)

    bmAimConstraint.outputRotate = nAttr.create('outputRotate', 'or', 
                                            bmAimConstraint.outputRotateX, 
                                            bmAimConstraint.outputRotateY, 
                                            bmAimConstraint.outputRotateZ)
    nAttr.setWritable(False)
    nAttr.setStorable(False)
    nAttr.setReadable(True)
    nAttr.setChannelBox(True)
    # add the attribute to the node
    bmAimConstraint.addAttribute(bmAimConstraint.outputRotate)

    # establish attributeAffects relationships so that the node knows when to compute
    bmAimConstraint.attributeAffects(bmAimConstraint.targetObjectMatrix, bmAimConstraint.outputRotate)
    bmAimConstraint.attributeAffects(bmAimConstraint.upObjectMatrix, bmAimConstraint.outputRotate)
    bmAimConstraint.attributeAffects(bmAimConstraint.downAxis, bmAimConstraint.outputRotate)
    bmAimConstraint.attributeAffects(bmAimConstraint.upAxis, bmAimConstraint.outputRotate)
    bmAimConstraint.attributeAffects(bmAimConstraint.rotateOrder, bmAimConstraint.outputRotate)
    bmAimConstraint.attributeAffects(bmAimConstraint.upVectorType, bmAimConstraint.outputRotate)
    bmAimConstraint.attributeAffects(bmAimConstraint.objectMatrix, bmAimConstraint.outputRotate)
    bmAimConstraint.attributeAffects(bmAimConstraint.offsetMatrix, bmAimConstraint.outputRotate)

def initializePlugin(obj):
    plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
    try:
        plugin.registerNode("bm_aimConstraint", bmAimConstraint.nodeId, creator, initialize)
    except:
        raise RuntimeError("Failed to register node")

def uninitializePlugin(obj):
    plugin = omMPx.MFnPlugin(obj)
    try:
        plugin.deregisterNode(bmAimConstraint.nodeId)
    except:
        raise RuntimeError("Failed to register node")

"""
obj = cmds.spaceLocator(name='obj')[0]
cmds.setAttr(obj + '.rotateOrder', 3)
target = cmds.spaceLocator(name='target')[0]
up = cmds.spaceLocator(name='up')[0]
cmds.xform(target, t=(5,0,0))
cmds.xform(up, t=(0,5,0))

cmds.loadPlugin(r"your_directory_path\bm_aimConstraint.py")
obj = cmds.spaceLocator(name='obj')[0]
cmds.setAttr(obj + '.rotateOrder', 3)
target = cmds.spaceLocator(name='target')[0]
up = cmds.spaceLocator(name='up')[0]
cmds.xform(target, t=(5,0,0))
cmds.xform(up, t=(0,5,0))
cmds.setAttr(obj + '.displayLocalAxis',1)
cmds.setAttr(target + '.displayLocalAxis',1)
cmds.setAttr(up + '.displayLocalAxis',1)
n = cmds.createNode('bm_aimConstraint')
cmds.connectAttr(obj + '.worldMatrix[0]', n + '.objectMatrix')
cmds.connectAttr(target + '.worldMatrix[0]', n + '.targetObjectMatrix')
cmds.connectAttr(up + '.worldMatrix[0]', n + '.upObjectMatrix')
cmds.setAttr(n + '.rotateOrder', cmds.getAttr(obj + '.rotateOrder'))
cmds.connectAttr(n + '.outputRotate', obj + '.rotate')
"""
