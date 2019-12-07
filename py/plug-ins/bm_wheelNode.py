import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
import maya.OpenMayaMPx as omMPx
import math

# Custom Aim Constraint by Ben Morgan. Done for the Sony Bend Character TD test.
# With some help from the Pedro Bellini vimeo video: "Aim Transformation with the Maya API"


class WheelNode(omMPx.MPxNode):
  """Creates a node which allows for the ramped calculation of vector angles
  
  Attributes:
    node_id (MTypeId): The unique id for this node
    driverMatrix (MObject): The worldMatrix of the object you want driven
    outputRotate (MObject): The resulting position

  """

  # give it a unique id
  node_id = om.MTypeId(0x40223)

  # input attributes
  driverMatrix = om.MObject()
  previousDriverMatrix = om.MObject()
  previousRotate = om.MObject()
  forwardAxis = om.MObject()

  # output attribute
  outputRotate = om.MObject()
  outputRotateX = om.MObject()
  outputRotateY = om.MObject()
  outputRotateZ = om.MObject()

  unit_vectors = [om.MVector().xAxis, om.MVector().yAxis, om.MVector().zAxis]
  tau = math.pi * 2

  def compute(self, plug, dataBlock):
    """Maya calls your node's MPxNode::compute() method when it determines that 
    one of your node's output attributes is out-of-date and needs to be re-computed. """

    # you clean plugs with the given dataBlock. That dataBlock needs to be an output
    if plug != WheelNode.outputRotate:
      raise RuntimeError("kUnknownParameter")

    # Returns MDataHandles to the current values of the input and output attributes needed 
    # to recompute the dirty plug.
    kDriverMatrix = dataBlock.inputValue(WheelNode.driverMatrix).asMatrix()
    hPreviousDriverMatrix = dataBlock.inputValue(WheelNode.previousDriverMatrix)
    kPreviousDriverMatrix = hPreviousDriverMatrix.asMatrix()

    kDriverXform = om.MTransformationMatrix(kDriverMatrix)
    kDriverVector = kDriverXform.getTranslation(om.MSpace.kWorld)

    kPreviousDriverXform = om.MTransformationMatrix(kPreviousDriverMatrix)
    kPreviousDriverVector = kPreviousDriverXform.getTranslation(om.MSpace.kWorld)
    
    wheel_vector = (kDriverVector - kPreviousDriverVector).normal()

    # get the down vector
    kForwardAxis = dataBlock.inputValue(WheelNode.forwardAxis).asShort()
    kDriverXform.addTranslation(WheelNode.unit_vectors[kForwardAxis], om.MSpace.kObject)
    outVector = kDriverXform.getTranslation(om.MSpace.kWorld)
    downVector = (outVector - kDriverVector).normal()

    quat = om.MQuaternion(downVector, wheel_vector)
    euler_rotation = quat.asEulerRotation()

    # hPrevRotate = dataBlock.inputValue(WheelNode.previousRotate)
    # prev_rotate = hPrevRotate.asDouble3()
    # prev_rotate_euler = om.MEulerRotation(prev_rotate[0], prev_rotate[1], prev_rotate[2])
    # euler_sum = prev_rotate_euler + euler_rotation

    hOutputRotate = dataBlock.outputValue(WheelNode.outputRotate)
    hOutputRotate.set3Double(euler_rotation.x, euler_rotation.y, euler_rotation.z)

    hPreviousDriverMatrix.setMMatrix(kDriverMatrix)
    
    # hPrevRotate.set3Double(euler_sum.x, euler_sum.y, euler_sum.z)

    dataBlock.setClean(plug)

def creator():
  # standard creator function for a Maya plugin
  return omMPx.asMPxPtr(WheelNode())

def initialize():
  # shortens OpenMaya attributes as variables for readability
  nAttr = om.MFnNumericAttribute()
  cAttr = om.MFnCompoundAttribute()
  mAttr = om.MFnMatrixAttribute()
  uAttr = om.MFnUnitAttribute()
  eAttr = om.MFnEnumAttribute()

  # Input Attributes 

  # OBJECT MATRIX
  WheelNode.driverMatrix = mAttr.create("driverMatrix", "dm", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  WheelNode.addAttribute(WheelNode.driverMatrix)

  # PREVIOUS OBJECT MATRIX
  WheelNode.previousDriverMatrix = mAttr.create("previousDriverMatrix", "pdm", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(False)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  WheelNode.addAttribute(WheelNode.previousDriverMatrix)

  # PREVIOUS ROTATE
  WheelNode.previousRotate = cAttr.create("previousRotate", "pr")
  cAttr.setKeyable(False)
  cAttr.setWritable(True)
  cAttr.setStorable(True)
  cAttr.setReadable(True)

  WheelNode.previousRotateX = uAttr.create("previousRotateX", "prx", om.MAngle(0.0))
  WheelNode.previousRotateY = uAttr.create("previousRotateY", "pry", om.MAngle(0.0))
  WheelNode.previousRotateZ = uAttr.create("previousRotateZ", "prz", om.MAngle(0.0))

  cAttr.addChild(WheelNode.previousRotateX)
  cAttr.addChild(WheelNode.previousRotateY)
  cAttr.addChild(WheelNode.previousRotateZ)

  WheelNode.addAttribute(WheelNode.previousRotate)

  # FORWARD AXIS
  WheelNode.forwardAxis = eAttr.create("forwardAxis", "fa")
  eAttr.addField("x", 0)
  eAttr.addField("y", 1)
  eAttr.addField("z", 2)
  eAttr.setDefault("x")
  eAttr.setKeyable(True)
  eAttr.setWritable(True)
  eAttr.setStorable(True)
  eAttr.setReadable(True)
  # add our attribute to the node
  WheelNode.addAttribute(WheelNode.forwardAxis)

  """ Output Attributes """
  WheelNode.outputRotate = cAttr.create("outputRotate", "or")
  cAttr.setWritable(False)
  cAttr.setStorable(False)
  cAttr.setReadable(True)

  WheelNode.outputRotateX = uAttr.create("outputRotateX", "ox", om.MAngle(0.0))
  WheelNode.outputRotateY = uAttr.create("outputRotateY", "oy", om.MAngle(0.0))
  WheelNode.outputRotateZ = uAttr.create("outputRotateZ", "oz", om.MAngle(0.0))

  cAttr.addChild(WheelNode.outputRotateX)
  cAttr.addChild(WheelNode.outputRotateY)
  cAttr.addChild(WheelNode.outputRotateZ)
  WheelNode.addAttribute(WheelNode.outputRotate)

  WheelNode.attributeAffects(WheelNode.driverMatrix, WheelNode.outputRotate)

def initializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
  try:
    plugin.registerNode("wheel", WheelNode.node_id, creator, initialize)
  except:
    raise RuntimeError("Failed to register node")

def uninitializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj)
  try:
    plugin.deregisterNode(WheelNode.node_id)
  except:
    raise RuntimeError("Failed to register node")



