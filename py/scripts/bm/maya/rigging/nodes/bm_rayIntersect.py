import maya.OpenMaya as om
import maya.OpenMayaMPx as omMPx
import math

# Custom Aim Constraint by Ben Morgan. Done for the Sony Bend Character TD test.
# With some help from the Pedro Bellini vimeo video: "Aim Transformation with the Maya API"


class RayIntersect(omMPx.MPxNode):
  """Creates a node which allows for the ramped calculation of vector angles
  
  Attributes:
    node_id (MTypeId): The unique id for this node
    objectMatrix (MObject): The worldMatrix of the object you want driven
    targetObjectMatrix (MObject): The worldMatrix of the object you want to be the target
    downAxis (MObject): The axis to aim down
    outputPoint (MObject): The resulting position
    unit_vectors (MObject): Hold the unit vectors used for calcultion.

  """

  # give it a unique id
  node_id = om.MTypeId(0x40222)

  # input attributes
  objectMatrix = om.MObject()
  downAxis = om.MObject()
  inMesh = om.MObject()
  normalOffset = om.MObject()

  # output attribute
  outputPoint = om.MObject()

  unit_vectors = [om.MVector().xAxis, om.MVector().yAxis, om.MVector().zAxis]
  tolerance = om.MScriptUtil(1.0e-10).asDouble()

  def compute(self, plug, dataBlock):
    """Maya calls your node's MPxNode::compute() method when it determines that 
    one of your node's output attributes is out-of-date and needs to be re-computed. """

    # you clean plugs with the given dataBlock. That dataBlock needs to be an output
    if plug != RayIntersect.outputPoint and plug.isChild() == False:
      raise RuntimeError("kUnknownParameter")

    # Returns MDataHandles to the current values of the input and output attributes needed 
    # to recompute the dirty plug.
    kObjectMatrix = dataBlock.inputValue(RayIntersect.objectMatrix).asMatrix()
    # Multi attributes are of type short
    kDownAxis = dataBlock.inputValue(RayIntersect.downAxis).asShort()
    kNormalOffset = dataBlock.inputValue(RayIntersect.normalOffset).asDouble()

    # get all the object's locations in world space
    xformMatrix = om.MTransformationMatrix(kObjectMatrix)
    objectVector = xformMatrix.getTranslation(om.MSpace.kWorld)
    xformMatrix.addTranslation(RayIntersect.unit_vectors[kDownAxis], om.MSpace.kObject)
    outVector = xformMatrix.getTranslation(om.MSpace.kWorld)
    downVector = outVector - objectVector

    # If worldMesh is attached, asMeshTransformed() allows world space information to be given
    kInMesh = dataBlock.inputValue(RayIntersect.inMesh).asMeshTransformed()
    try:
      fnMesh = om.MFnMesh(kInMesh)
    except RuntimeError:
      # in mesh is null (hasn't been connected yet)
      return

    ray_source = om.MPoint(objectVector.x, objectVector.y, objectVector.z)
    intersect_points = om.MPointArray()
    poly_ids = om.MIntArray()

    # find the interesection point 
    fnMesh.intersect(ray_source, downVector, intersect_points, RayIntersect.tolerance, om.MSpace.kWorld, poly_ids)

    hOutputPoint = dataBlock.outputValue(RayIntersect.outputPoint)

    if intersect_points.length():
      # only continue with calculations if there was an intersection
      if kNormalOffset != 0.0:
        # find the closest_normal at that point and offset the vector by the offset multiplier
        closest_normal = om.MVector()
        # NOTE: doesn't take into account transforms on the mesh's transform node
        fnMesh.getClosestNormal(intersect_points[0], closest_normal, om.MSpace.kWorld)

        closest_normal = closest_normal.normal()

        offset_point = intersect_points[0] + (closest_normal.normal() * kNormalOffset)
        # set the point to the offset value
        hOutputPoint.set3Double(om.MScriptUtil(offset_point.x).asDouble(),
                                om.MScriptUtil(offset_point.y).asDouble(),
                                om.MScriptUtil(offset_point.z).asDouble())
      else:
        hOutputPoint.set3Double(om.MScriptUtil(intersect_points[0].x).asDouble(),
                                om.MScriptUtil(intersect_points[0].y).asDouble(),
                                om.MScriptUtil(intersect_points[0].z).asDouble())

    dataBlock.setClean(plug)

def creator():
  # standard creator function for a Maya plugin
  return omMPx.asMPxPtr(RayIntersect())

def initialize():
  # shortens OpenMaya attributes as variables for readability
  nAttr = om.MFnNumericAttribute()
  mAttr = om.MFnMatrixAttribute()
  eAttr = om.MFnEnumAttribute()
  tAttr = om.MFnTypedAttribute()
  uAttr = om.MFnUnitAttribute()

  # Input Attributes 

  # OBJECT MATRIX
  RayIntersect.objectMatrix = mAttr.create("objectMatrix", "objMat", om.MFnMatrixAttribute.kDouble)
  mAttr.setKeyable(True)
  mAttr.setWritable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  RayIntersect.addAttribute(RayIntersect.objectMatrix)

  # DOWN AXIS
  RayIntersect.downAxis = eAttr.create("downAxis", "down")
  eAttr.addField("x", 0)
  eAttr.addField("y", 1)
  eAttr.addField("z", 2)
  eAttr.setDefault("x")
  eAttr.setKeyable(True)
  eAttr.setWritable(True)
  eAttr.setStorable(True)
  eAttr.setReadable(True)
  # add our attribute to the node
  RayIntersect.addAttribute(RayIntersect.downAxis)

  # IN MESH
  RayIntersect.inMesh = tAttr.create("inMesh", "in", om.MFnData.kMesh)
  # set only to storable
  eAttr.setKeyable(True)
  eAttr.setWritable(True)
  eAttr.setStorable(True)
  eAttr.setReadable(True)
  # add our attribute to the node
  RayIntersect.addAttribute(RayIntersect.inMesh)

  # NORMAL OFFSET
  RayIntersect.normalOffset = nAttr.create("normalOffset", "off", om.MFnNumericData.kDouble)
  nAttr.setKeyable(True)
  nAttr.setWritable(True)
  nAttr.setStorable(True)
  nAttr.setReadable(True)
  # add our attribute to the node
  RayIntersect.addAttribute(RayIntersect.normalOffset)

  """ Output Attributes """
  RayIntersect.outputPoint = nAttr.create("outputPoint", "op", om.MFnNumericData.k3Double)
  nAttr.setWritable(False)
  nAttr.setStorable(False)
  nAttr.setReadable(True)
  # add our attribute to the node
  RayIntersect.addAttribute(RayIntersect.outputPoint)

  # establish our attributeAffects relationships so that the node knows when to compute
  RayIntersect.attributeAffects(RayIntersect.objectMatrix, RayIntersect.outputPoint)
  RayIntersect.attributeAffects(RayIntersect.downAxis, RayIntersect.outputPoint)
  RayIntersect.attributeAffects(RayIntersect.inMesh, RayIntersect.outputPoint)
  RayIntersect.attributeAffects(RayIntersect.normalOffset, RayIntersect.outputPoint)

def initializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
  try:
    plugin.registerNode("rayIntersect", RayIntersect.node_id, creator, initialize)
  except:
    raise RuntimeError("Failed to register node")

def uninitializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj)
  try:
    plugin.deregisterNode(RayIntersect.node_id)
  except:
    raise RuntimeError("Failed to register node")



