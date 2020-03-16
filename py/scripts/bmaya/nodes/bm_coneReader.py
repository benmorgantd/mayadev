import maya.OpenMaya as om
import maya.OpenMayaMPx as omMPx
import math


class ConeReader(omMPx.MPxNode):
  """Creates a node which allows for the ramped calculation of vector angles
  
  Attributes:
    nodeId (MTypeId): The unique id for this node
    objectMatrix (MObject): The worldMatrix of the object you want driven
    targetObjectMatrix (MObject): The worldMatrix of the object you want to be the target
    downAxis (MObject): The axis to aim down
    outputValue (MObject): The resulting Euler rotation
    unitVectors (MObject): Hold the unit vectors used for calcultion.

  """

  # give it a unique id
  nodeId = om.MTypeId(0x40219)

  # input attributes
  objectMatrix = om.MObject()
  targetObjectMatrix = om.MObject()
  coneAngle = om.MObject()
  downAxis = om.MObject()

  # output attribute
  outputValue = om.MObject()

  unitVectors = [om.MVector().xAxis, om.MVector().yAxis, om.MVector().zAxis]

  def compute(self, plug, dataBlock):
    """Maya calls your node's MPxNode::compute() method when it determines that 
    one of your node's output attributes is out-of-date and needs to be re-computed. """

    # you clean plugs with the given dataBlock. That dataBlock needs to be an output
    if plug != ConeReader.outputValue:
      raise RuntimeError("kUnknownParameter")

    # Returns MDataHandles to the current values of the input and output attributes needed 
    # to recompute the dirty plug.
    # .asMatrix() gives us MMatrix
    kObjectMatrix = dataBlock.inputValue(ConeReader.objectMatrix).asMatrix()
    kTargetObjectMatrix = dataBlock.inputValue(ConeReader.targetObjectMatrix).asMatrix()

    kConeAngle = dataBlock.inputValue(ConeReader.coneAngle).asDouble()

    # Multi attributes are of type short
    kDownAxis = dataBlock.inputValue(ConeReader.downAxis).asShort()

    kDownAxis = ConeReader.unitVectors[kDownAxis]

    # get all the object's locations in world space
    xformMatrix = om.MTransformationMatrix(kObjectMatrix)
    objectVector = xformMatrix.getTranslation(om.MSpace.kWorld)
    xformMatrix.addTranslation(kDownAxis, om.MSpace.kObject)
    outVector = xformMatrix.getTranslation(om.MSpace.kWorld)
    downVector = outVector - objectVector

    xformMatrix = om.MTransformationMatrix(kTargetObjectMatrix)
    targetObjectVector = xformMatrix.getTranslation(om.MSpace.kWorld)
    objectToTargetVector = targetObjectVector - objectVector

    # get the angle between the two
    angle = downVector.angle(objectToTargetVector) * 57.296

    if angle >= kConeAngle:
      value = 0.0
    else:
      value = 1 - ((angle) / float(kConeAngle))
    
    hOutputValue = dataBlock.outputValue(ConeReader.outputValue)
    # doing this multiplication here so that the resulting unitConversion node's effect is negated.
    # (just to make the result more clear and immediate)
    hOutputValue.setDouble(value)

    dataBlock.setClean(plug)

def creator():
  # standard creator function for a Maya plugin
  return omMPx.asMPxPtr(ConeReader())

def initialize():
  # shortens OpenMaya attributes as variables for readability
  nAttr = om.MFnNumericAttribute()
  mAttr = om.MFnMatrixAttribute()
  eAttr = om.MFnEnumAttribute()

  # Input Attributes 

  # OBJECT MATRIX
  ConeReader.objectMatrix = mAttr.create("objectMatrix", "objMat", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  ConeReader.addAttribute(ConeReader.objectMatrix)

  # TARGET OBJECT MATRIX
  ConeReader.targetObjectMatrix = mAttr.create("targetObjectMatrix", "targetMat", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  ConeReader.addAttribute(ConeReader.targetObjectMatrix)

  # DOWN AXIS
  ConeReader.downAxis = eAttr.create("downAxis", "down")
  eAttr.addField("x", 0)
  eAttr.addField("y", 1)
  eAttr.addField("z", 2)
  eAttr.setDefault("x")
  eAttr.setKeyable(True)
  eAttr.setWritable(True)
  eAttr.setStorable(True)
  eAttr.setReadable(True)
  # add our attribute to the node
  ConeReader.addAttribute(ConeReader.downAxis)

  # MaxAngle
  ConeReader.coneAngle = nAttr.create("coneAngle", "angle", om.MFnNumericData.kDouble, 45.0)
  nAttr.setKeyable(True)
  nAttr.setWritable(True)
  nAttr.setStorable(True)
  nAttr.setReadable(True)
  # add our attribute to the node
  ConeReader.addAttribute(ConeReader.coneAngle)

  """ Output Attributes """
  ConeReader.outputValue = nAttr.create("outputValue", "out", om.MFnNumericData.kDouble)
  nAttr.setWritable(False)
  nAttr.setStorable(False)
  nAttr.setReadable(True)
  # add our attribute to the node
  ConeReader.addAttribute(ConeReader.outputValue)

  # establish our attributeAffects relationships so that the node knows when to compute
  ConeReader.attributeAffects(ConeReader.objectMatrix, ConeReader.outputValue)
  ConeReader.attributeAffects(ConeReader.targetObjectMatrix, ConeReader.outputValue)
  ConeReader.attributeAffects(ConeReader.downAxis, ConeReader.outputValue)
  ConeReader.attributeAffects(ConeReader.coneAngle, ConeReader.outputValue)

def initializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
  try:
    plugin.registerNode("coneReader", ConeReader.nodeId, creator, initialize)
  except:
    raise RuntimeError("Failed to register node")

def uninitializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj)
  try:
    plugin.deregisterNode(ConeReader.nodeId)
  except:
    raise RuntimeError("Failed to register node")



