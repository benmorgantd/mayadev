import maya.OpenMaya as om
import maya.OpenMayaMPx as omMPx
import math

# Custom Aim Constraint by Ben Morgan. Done for the Sony Bend Character TD test.
# With some help from the Pedro Bellini vimeo video: "Aim Transformation with the Maya API"


class QuatExtract(omMPx.MPxNode):
  """Creates a node which allows for the ramped calculation of vector angles
  
  Attributes:
    nodeId (MTypeId): The unique id for this node
    objectMatrix (MObject): The worldMatrix of the object you want driven
    targetObjectMatrix (MObject): The worldMatrix of the object you want to be the target
    outputRotate (MObject): The resulting Euler rotation
    unit_vectors (MObject): Hold the unit vectors used for calcultion.

  """

  # give it a unique id
  nodeId = om.MTypeId(0x40221)

  # input attributes
  objectMatrix = om.MObject()
  parentInverseMatrix = om.MObject()
  twistAxis = om.MObject()
  offset = om.MObject()
  multiplier = om.MObject()

  # output attribute
  outputAngle = om.MObject()

  doubleNull = om.MScriptUtil(0.0).asDouble()
  angleDefault = om.MAngle(0.0)
  shortValues = [om.MScriptUtil(0).asShort(), om.MScriptUtil(1).asShort(), om.MScriptUtil(2).asShort()]
  

  def compute(self, plug, dataBlock):
    """Maya calls your node's MPxNode::compute() method when it determines that 
    one of your node's output attributes is out-of-date and needs to be re-computed. """

    # you clean plugs with the given dataBlock. That dataBlock needs to be an output
    if plug != QuatExtract.outputAngle:
      raise RuntimeError("kUnknownParameter")

    # Returns MDataHandles to the current values of the input and output attributes needed 
    # to recompute the dirty plug.
    kObjectMatrix = dataBlock.inputValue(QuatExtract.objectMatrix).asMatrix()
    kParentInverseMatrix = dataBlock.inputValue(QuatExtract.parentInverseMatrix).asMatrix()

    kOffset = dataBlock.inputValue(QuatExtract.offset).asDouble()
    kOffset = kOffset * (math.pi / 180.0)

    matrix_sum = kObjectMatrix * kParentInverseMatrix
    xformMatrix = om.MTransformationMatrix(matrix_sum)
    quat = xformMatrix.rotation() 

    # Multi attributes are of type short
    kTwistAxis = dataBlock.inputValue(QuatExtract.twistAxis).asShort()
    
    if kTwistAxis == QuatExtract.shortValues[0]:    
      quat_x = om.MQuaternion(quat.x, QuatExtract.doubleNull, QuatExtract.doubleNull, quat.w)
      quat_euler = quat_x.asEulerRotation().x + kOffset

    elif kTwistAxis == QuatExtract.shortValues[1]:
      quat_y = om.MQuaternion(QuatExtract.doubleNull, quat.y, QuatExtract.doubleNull, quat.w)
      quat_euler = quat_y.asEulerRotation().y + kOffset

    elif kTwistAxis == QuatExtract.shortValues[2]:
      quat_z = om.MQuaternion(QuatExtract.doubleNull, QuatExtract.doubleNull, quat.z, quat.w)
      quat_euler = quat_z.asEulerRotation().z + kOffset


    hOutputAngleArray = dataBlock.outputArrayValue(QuatExtract.outputAngle)

    kLogicalIndex = plug.logicalIndex()
    hOutputAngleArray.jumpToElement(kLogicalIndex)
    hOutputAngle = hOutputAngleArray.outputValue()

    kMultiplier = dataBlock.inputValue(QuatExtract.multiplier).asDouble()

    quat_angle = om.MAngle(quat_euler * (kMultiplier ** om.MScriptUtil(kLogicalIndex).asDouble()))

    hOutputAngle.setMAngle(quat_angle)

    hOutputAngleArray.setClean()
    dataBlock.setClean(plug)

def creator():
  # standard creator function for a Maya plugin
  return omMPx.asMPxPtr(QuatExtract())

def initialize():
  # shortens OpenMaya attributes as variables for readability
  nAttr = om.MFnNumericAttribute()
  mAttr = om.MFnMatrixAttribute()
  uAttr = om.MFnUnitAttribute()
  eAttr = om.MFnEnumAttribute()
  rAttr = om.MRampAttribute()

  # Input Attributes 

  # OBJECT MATRIX
  QuatExtract.objectMatrix = mAttr.create("objectMatrix", "objMat", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  QuatExtract.addAttribute(QuatExtract.objectMatrix)

  # TARGET OBJECT MATRIX
  QuatExtract.parentInverseMatrix = mAttr.create("parentInverseMatrix", "parentInvMat", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  QuatExtract.addAttribute(QuatExtract.parentInverseMatrix)

  # TWIST AXIS
  QuatExtract.twistAxis = eAttr.create("twistAxis", "twist")
  eAttr.addField("x", 0)
  eAttr.addField("y", 1)
  eAttr.addField("z", 2)
  eAttr.setDefault("x")
  eAttr.setKeyable(True)
  eAttr.setWritable(True)
  eAttr.setStorable(True)
  eAttr.setReadable(True)
  # add our attribute to the node
  QuatExtract.addAttribute(QuatExtract.twistAxis)

  # OFFSET VALUE
  QuatExtract.offset = nAttr.create("offset", "off", om.MFnNumericData.kDouble, 0.0)
  nAttr.setKeyable(True)
  nAttr.setWritable(True)
  nAttr.setStorable(True)
  nAttr.setReadable(True)
  QuatExtract.addAttribute(QuatExtract.offset)

  # MULTIPLIER VALUE
  QuatExtract.multiplier = nAttr.create("multiplier", "mult", om.MFnNumericData.kDouble, 0.80)
  nAttr.setKeyable(True)
  nAttr.setWritable(True)
  nAttr.setStorable(True)
  nAttr.setReadable(True)
  QuatExtract.addAttribute(QuatExtract.multiplier)


  """ Output Attributes """
  QuatExtract.outputAngle = uAttr.create("outputAngle", "oa", QuatExtract.angleDefault)
  uAttr.setWritable(False)
  uAttr.setStorable(False)
  uAttr.setReadable(True)
  uAttr.setChannelBox(True)
  uAttr.setArray(True)
  # add our attribute to the node
  QuatExtract.addAttribute(QuatExtract.outputAngle)

  # establish our attributeAffects relationships so that the node knows when to compute
  QuatExtract.attributeAffects(QuatExtract.objectMatrix, QuatExtract.outputAngle)
  QuatExtract.attributeAffects(QuatExtract.parentInverseMatrix, QuatExtract.outputAngle)
  QuatExtract.attributeAffects(QuatExtract.twistAxis, QuatExtract.outputAngle)
  QuatExtract.attributeAffects(QuatExtract.offset, QuatExtract.outputAngle)
  QuatExtract.attributeAffects(QuatExtract.multiplier, QuatExtract.outputAngle)


def initializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
  try:
    plugin.registerNode("quatExtract", QuatExtract.nodeId, creator, initialize)
  except:
    raise RuntimeError("Failed to register node")

def uninitializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj)
  try:
    plugin.deregisterNode(QuatExtract.nodeId)
  except:
    raise RuntimeError("Failed to register node")



"""
cmds.loadPlugin(r"D:/Documents/Google Drive/Maya/bmTools/scripts/Nodes/bm_quatExtract.py")

joints = []
cubes = []

for i in range(-50,50, 3):
    for j in range(-50,50, 3):
        quat = cmds.createNode("quatExtract", name="quatExtract_01")
        
        joint1 = cmds.joint(p=(i, 0,j + 1))
        joint2 = cmds.joint(p=(2 + i,0, j + 1))
        cmds.select(cl=1)
        joints.append(joint1)
        cube = cmds.polyCube(ch=0)
        cubes.append(cube[0])
        cmds.xform(cube, t=(i + 2, 1, j + 1), ws=1)
        
        
        cmds.connectAttr(joint2 + ".worldMatrix", quat + ".objectMatrix")
        cmds.connectAttr(joint2 + ".parentInverseMatrix", quat + ".parentInverseMatrix")
        
        cmds.connectAttr(quat + ".ot", cube[0] + ".rx")
        
cmds.group(cubes)
cmds.group(joints)

"""
"""
cmds.loadPlugin(r"D:/Documents/Google Drive/Maya/bmTools/scripts/Nodes/bm_quatExtract.py")
quat = cmds.createNode("quatExtract", name="quatExtract_01")
        
joint1 = cmds.joint(p=(0, 0, 0))
joint2 = cmds.joint(p=(2,0, 0))
cmds.select(cl=1)
cube = cmds.polyCube(ch=0)
cmds.xform(cube, t=(0, 0, 2), ws=1)


cmds.connectAttr(joint2 + ".worldMatrix", quat + ".objectMatrix")
cmds.connectAttr(joint2 + ".parentInverseMatrix", quat + ".parentInverseMatrix")

cmds.connectAttr(quat + ".ot", cube[0] + ".rx")
"""