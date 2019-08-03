import maya.OpenMaya as om
import maya.OpenMayaMPx as omMPx


class CustomAimConstraint(omMPx.MPxConstraint):
  # give it a unique id
  node_id = om.MTypeId(0x40218)

  # declare our input attributes
  inMatrix = om.MObject()
  inUpObject = om.MObject()

  # declare our output attributes
  outRotate = om.MObject()

  def compute(self, plug, dataBlock):
    """Maya calls your node's MPxNode::compute() method when it determines that one of your node's output attributes, or plugs, is out-of-date and needs to be re-computed. """

    # you clean plugs with the given dataBlock
    if plug.attribute() == CustomAimConstraint.outTranslateX:

      # returns MDataHandles to the current values of the input and output attributes needed 
      # to recompute the dirty plug
      inMatrixHandle = dataBlock.inputValue(CustomAimConstraint.inMatrix).asMatrix()
      outTranslateHandle = dataBlock.outputValue(CustomAimConstraint.outTranslateX)

      # no data must exist for our matrix handle since it's returning type 0
      mFn = om.MFnMatrixData(inMatrixHandle.data())

      # ***we have to get the Matrix from a SHAPE node, not a transform node
      inVector = mFn.transformation().getTranslation(om.MSpace.kWorld)

      outTranslateHandle.setDouble(inVector.x)

      dataBlock.setClean(plug)

def creator():
  # standard creator function for a Maya plugin
  return omMPx.asMPxPtr(CustomAimConstraint())


def initialize():
  # shorten OpenMaya attributes as variables for readability
  nAttr = om.MFnNumericAttribute()
  mAttr = om.MFnMatrixAttribute()

  """ Input Attributes """

  # create a matrix of doubles
  CustomAimConstraint.inMatrix = mAttr.create("inMatrix", "matrix")
  mAttr.setKeyable(True)
  mAttr.setStorable(True)
  mAttr.setReadable(True)
  # add our attribute to the node
  CustomAimConstraint.addAttribute(CustomAimConstraint.inMatrix)

  """ Output Attributes """
  CustomAimConstraint.outTranslateX = nAttr.create("outTranslateX", "ox", om.MFnNumericData.kDouble, 0.0)
  # input values should be keyable, storable, readable, and writable
  nAttr.setKeyable(False)
  nAttr.setStorable(False)
  nAttr.setReadable(True)
  nAttr.setWritable(False)
  # add our attribute to the node
  CustomAimConstraint.addAttribute(CustomAimConstraint.outTranslateX)

  CustomAimConstraint.attributeAffects(CustomAimConstraint.inMatrix, CustomAimConstraint.outTranslateX)

def initializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
  try:
    plugin.registerNode("bm_aimConstraint", CustomAimConstraint.node_id, creator, initialize)
  except:
    raise RuntimeError("Failed to register node")


def uninitializePlugin(obj):
  plugin = omMPx.MFnPlugin(obj)
  try:
    plugin.deregisterNode(CustomAimConstraint.node_id)
  except:
    raise RuntimeError("Failed to register node")
