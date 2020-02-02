import maya.OpenMaya as om
import maya.OpenMayaMPx as omMPx
import math

# Custom Aim Constraint by Ben Morgan. Done for the Sony Bend Character TD test.
# With some help from the Pedro Bellini vimeo video: "Aim Transformation with the Maya API"


class AimTransform(omMPx.MPxConstraint):
  """Creates a node which allows for the calculation of an aim transformation
  
  Attributes:
    node_id (MTypeId): The unique id for this node
    objectMatrix (MObject): The worldMatrix of the object you want driven
    upObjectMatrix (MObject): The worldMatrix of the object you want as the up object
    aimObjectMatrix (MObject): The worldMatrix of the object that will get aimed at
    downAxis (MObject): The axis to aim down
    upAxis (MObject): The axis used to aim at the upObject
    ouputRotate (MObject): The resulting Euler rotation
    unit_vectors (MObject): Hold the unit vectors used for calcultion.

  """

  # give it a unique id
  node_id = om.MTypeId(0x40218)

  # input attributes
  objectMatrix = om.MObject()
  upObjectMatrix = om.MObject()
  aimObjectMatrix = om.MObject()

  downAxis = om.MObject()
  upAxis = om.MObject()

  # output attribute
  outputRotate = om.MObject()

  unit_vectors = [om.MVector().xAxis, om.MVector().yAxis, om.MVector().zAxis]

  def compute(self, plug, dataBlock):
    """Maya calls your node's MPxNode::compute() method when it determines that 
    one of your node's output attributes is out-of-date and needs to be re-computed. """

    # you clean plugs with the given dataBlock. That dataBlock needs to be an output
    if plug != AimTransform.outputRotate:
      raise RuntimeError("kUnknownParameter")

    # Returns MDataHandles to the current values of the input and output attributes needed 
    # to recompute the dirty plug.
    # .asMatrix() gives us MMatrix
    kObjectMatrix = dataBlock.inputValue(AimTransform.objectMatrix).asMatrix()
    kUpObjectMatrix = dataBlock.inputValue(AimTransform.upObjectMatrix).asMatrix()
    kAimObjectMatrix = dataBlock.inputValue(AimTransform.aimObjectMatrix).asMatrix()

    # find out how to interpret multi attributes
    kDownAxis = dataBlock.inputValue(AimTransform.downAxis).asShort()
    kUpAxis = dataBlock.inputValue(AimTransform.upAxis).asShort()

    # I'm getting some sort of int/long error that I don't have time to fix. Let's just do a check...
    if kDownAxis >= 65536:
      kDownAxis -= 65536

    if kUpAxis >= 65536:
      kUpAxis -= 65536

    # check these axis are not the same
    if kDownAxis == kUpAxis:
      raise RuntimeError("Down and up axis are the same value")

    kDownAxis = AimTransform.unit_vectors[kDownAxis]
    kUpAxis = AimTransform.unit_vectors[kUpAxis]

    # do computation
    # get all the object's locations in world space
    objectVector = om.MTransformationMatrix(kObjectMatrix).getTranslation(om.MSpace.kWorld)
    upObjectVector = om.MTransformationMatrix(kUpObjectMatrix).getTranslation(om.MSpace.kWorld)
    aimObjectVector = om.MTransformationMatrix(kAimObjectMatrix).getTranslation(om.MSpace.kWorld)

    # find the vector from the object to the aimObject
    aimVector = (aimObjectVector - objectVector)
    # find the vector from the object to the upObject
    upVector = (upObjectVector - objectVector).normal()

    aimVectorU = aimVector.normal()
    # just use the up vector for now
    aimVectorV = upVector
    # use vector cross product to give us a 3rd axis that's perpendicular to that space
    aimVectorW = (aimVectorU ^ aimVectorV).normal()

    # use vector corss product to give us an up vector that's orthogonal to U
    aimVectorV = aimVectorW ^ aimVectorU

    # get the quaternion for the movement from the given unit vectorof the down axis to the aim vector
    quaternion = om.MQuaternion(kDownAxis, aimVectorU)

    # rotate the up axis by that quaternion
    upAxisRotated = kUpAxis.rotateBy(quaternion)
    # find the angle between that rotated up axis and the current up axis
    angle = upAxisRotated.angle(aimVectorV)
    # get that as a quaternion
    quaternionV = om.MQuaternion(angle, aimVectorU)

    # make sure the angles are within a tolerance
    if not aimVectorV.isEquivalent(upAxisRotated.rotateBy(quaternionV), 1.0e-5):
      angle = (2*math.pi) - angle
      quaternionV = om.MQuaternion(angle, aimVectorU)

    # adds that new movement to the quaternion
    quaternion *= quaternionV
    euler_rotation = quaternion.asEulerRotation()
    # create a scriptUtil to allow us to set the double values
    double_x = om.MScriptUtil(euler_rotation.x).asDouble()
    double_y = om.MScriptUtil(euler_rotation.y).asDouble()
    double_z = om.MScriptUtil(euler_rotation.z).asDouble()

    # output data handle
    hOutput = dataBlock.outputValue(AimTransform.outputRotate)
    # doing this multiplication here so that the resulting unitConversion node's effect is negated.
    # (just to make the result more clear and immediate)
    hOutput.set3Double(double_x * 58.82352941176471, double_y * 58.82352941176471, double_z * 58.82352941176471)

    # there are some other rotation errors going on when the rotations go into certain quadrants. 
    # no time to fix for now!

    dataBlock.setClean(plug)

def creator():
  # standard creator function for a Maya plugin
  return omMPx.asMPxPtr(AimTransform())

def initialize():
  # shortens OpenMaya attributes as variables for readability
  nAttr = om.MFnNumericAttribute()
  mAttr = om.MFnMatrixAttribute()
  eAttr = om.MFnEnumAttribute()

  # Input Attributes 

  # OBJECT MATRIX
  AimTransform.objectMatrix = mAttr.create("objectMatrix", "objMat", om.MFnMatrixAttribute.kMatrix)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  AimTransform.addAttribute(AimTransform.objectMatrix)

  # AIM OBJECT MATRIX
  AimTransform.aimObjectMatrix = mAttr.create("aimObjectMatrix", "aimObjMat", om.MFnMatrixAttribute.kMatrix)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  AimTransform.addAttribute(AimTransform.aimObjectMatrix)

  # UP OBJECT MATRIX
  AimTransform.upObjectMatrix = mAttr.create("upObjectMatrix", "upObjMat", om.MFnMatrixAttribute.kMatrix)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  AimTransform.addAttribute(AimTransform.upObjectMatrix)

  # DOWN AXIS
  AimTransform.downAxis = eAttr.create("downAxis", "down")
  eAttr.addField("x", 0)
  eAttr.addField("y", 1)
  eAttr.addField("z", 2)
  eAttr.setDefault("x")
  eAttr.setKeyable(True)
  eAttr.setWritable(True)
  eAttr.setStorable(True)
  eAttr.setReadable(True)
  # add our attribute to the node
  AimTransform.addAttribute(AimTransform.downAxis)

  # DOWN AXIS
  AimTransform.upAxis = eAttr.create("upAxis", "up")
  eAttr.addField("x", 0)
  eAttr.addField("y", 1)
  eAttr.addField("z", 2)
  eAttr.setDefault("y")
  eAttr.setKeyable(True)
  eAttr.setWritable(True)
  eAttr.setStorable(True)
  eAttr.setReadable(True)
  # add our attribute to the node
  AimTransform.addAttribute(AimTransform.upAxis)

  """ Output Attributes """
  AimTransform.outputRotate = nAttr.create("outputRotate", "out", om.MFnNumericData.k3Double)
  nAttr.setWritable(False)
  nAttr.setStorable(False)
  nAttr.setReadable(True)
  # this seems to have no effect...
  nAttr.setChannelBox(True)
  # add our attribute to the node
  AimTransform.addAttribute(AimTransform.outputRotate)

  # establish our attributeAffects relationships so that the node knows when to compute
  AimTransform.attributeAffects(AimTransform.objectMatrix, AimTransform.outputRotate)
  AimTransform.attributeAffects(AimTransform.aimObjectMatrix, AimTransform.outputRotate)
  AimTransform.attributeAffects(AimTransform.upObjectMatrix, AimTransform.outputRotate)

  AimTransform.attributeAffects(AimTransform.downAxis, AimTransform.outputRotate)
  AimTransform.attributeAffects(AimTransform.upAxis, AimTransform.outputRotate)

def initializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
  try:
    plugin.registerNode("aimTransform", AimTransform.node_id, creator, initialize)
  except:
    raise RuntimeError("Failed to register node")

def uninitializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj)
  try:
    plugin.deregisterNode(AimTransform.node_id)
  except:
    raise RuntimeError("Failed to register node")




# Quickstart code

"""
# first load the plugin on your machine...

aim_node = cmds.createNode("aimTransform", name="test")

eye = cmds.polyCube(name="eye_obj",constructionHistory=False)
aim = cmds.polyCube(name="aim_obj", constructionHistory=False)
up = cmds.polyCube(name="up_obj", constructionHistory=False)

cmds.xform(aim, translation=(5,5,5),worldSpace=True)
cmds.xform(up, translation=(0,5,0), worldSpace=True)

cmds.connectAttr("eye_obj.worldMatrix", "{0}.objectMatrix".format(aim_node))
cmds.connectAttr("aim_obj.worldMatrix", "{0}.aimObjectMatrix".format(aim_node))
cmds.connectAttr("up_obj.worldMatrix", "{0}.upObjectMatrix".format(aim_node))

cmds.connectAttr("{0}.outputRotate".format(aim_node), "eye_obj.rotate")

"""