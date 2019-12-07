import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
import maya.OpenMayaMPx as omMPx


class SimpleCollision(omMPx.MPxNode):
  """Computes a simple sphere to sphere collision between two transforms. 
  
  Attributes:
    node_id (MTypeId): The unique id for this node
    colliderMatrix (MObject): The worldMatrix of the object you want driven
    startMatrix (MObject): The worldMatrix representing the default position of the collision obj
    collisionRadius (MObject): The spherical radius of the collision object
    outputTranslate (MObject): The resulting position

  """

  # give it a unique id
  node_id = om.MTypeId(0x40224)

  # input attributes
  colliderMatrix = om.MObject()
  startMatrix = om.MObject()
  collisionRadius = om.MObject()

  # output attribute
  outputTranslate = om.MObject()

  def compute(self, plug, dataBlock):
    """Maya calls your node's MPxNode::compute() method when it determines that 
    one of your node's output attributes is out-of-date and needs to be re-computed. """

    # you clean plugs with the given dataBlock. That dataBlock needs to be an output
    if plug != SimpleCollision.outputTranslate and not plug.isChild():
      raise RuntimeError("kUnknownParameter")

    kColliderMatrix = dataBlock.inputValue(SimpleCollision.colliderMatrix).asMatrix()
    kStartMatrix = dataBlock.inputValue(SimpleCollision.startMatrix).asMatrix()
    kCollisionRadius = dataBlock.inputValue(SimpleCollision.collisionRadius).asDouble()

    # get the world-space vectors from each matrix
    colliderXformMatrix = om.MTransformationMatrix(kColliderMatrix)
    collider_vector = colliderXformMatrix.getTranslation(om.MSpace.kWorld)

    startXformMatrix = om.MTransformationMatrix(kStartMatrix)
    start_vector = startXformMatrix.getTranslation(om.MSpace.kWorld)

    # get the vector between the two as the vector from the start object to the collider
    vector_between = start_vector - collider_vector
    distance_between = vector_between.length()

    # check if it's within the collision radius plus the collider radius
    if distance_between < (kCollisionRadius):
      offset_factor = (kCollisionRadius - distance_between) / float(kCollisionRadius)
      final_vector = start_vector + (vector_between.normal() * (offset_factor))
    else:
      final_vector = start_vector

    hOutputTranslate = dataBlock.outputValue(SimpleCollision.outputTranslate)
    hOutputTranslate.set3Double(final_vector.x, final_vector.y, final_vector.z)

    dataBlock.setClean(plug)

def creator():
  # standard creator function for a Maya plugin
  return omMPx.asMPxPtr(SimpleCollision())

def initialize():
  # shortens OpenMaya attributes as variables for readability
  nAttr = om.MFnNumericAttribute()
  mAttr = om.MFnMatrixAttribute()

  # Input Attributes 

  # COLLIDER OBJECT MATRIX
  SimpleCollision.colliderMatrix = mAttr.create("colliderMatrix", "cm", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  SimpleCollision.addAttribute(SimpleCollision.colliderMatrix)

  # COLLISION OBJECT START MATRIX
  SimpleCollision.startMatrix = mAttr.create("startMatrix", "sm", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  SimpleCollision.addAttribute(SimpleCollision.startMatrix)

  # COLLISION RADIUS
  SimpleCollision.collisionRadius = nAttr.create("collisionRadius", "csr", om.MFnNumericData.kDouble, 1.0)
  nAttr.setKeyable(True)
  nAttr.setWritable(True)
  nAttr.setStorable(True)
  nAttr.setReadable(True)
  nAttr.setMin(0.01)
  SimpleCollision.addAttribute(SimpleCollision.collisionRadius)

  """ Output Attributes """
  SimpleCollision.outputTranslate = nAttr.create("outputTranslate", "ot", om.MFnNumericData.k3Double)
  nAttr.setKeyable(False)
  nAttr.setWritable(True)
  nAttr.setStorable(True)
  nAttr.setReadable(True)
  SimpleCollision.addAttribute(SimpleCollision.outputTranslate)

  SimpleCollision.attributeAffects(SimpleCollision.colliderMatrix, SimpleCollision.outputTranslate)
  SimpleCollision.attributeAffects(SimpleCollision.startMatrix, SimpleCollision.outputTranslate)
  SimpleCollision.attributeAffects(SimpleCollision.collisionRadius, SimpleCollision.outputTranslate)

def initializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
  try:
    plugin.registerNode("simpleCollision", SimpleCollision.node_id, creator, initialize)
  except:
    raise RuntimeError("Failed to register node")

def uninitializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj)
  try:
    plugin.deregisterNode(SimpleCollision.node_id)
  except:
    raise RuntimeError("Failed to register node")



