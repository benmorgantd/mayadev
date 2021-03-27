# Use the new api
import maya.OpenMaya as om
import maya.OpenMayaMPx as omMPx
import math


##############################
# Sin Node class declaration #
##############################

# create a new class that inherits attributes from the om.MpxNode class.
class SinNode(omMPx.MPxNode):
    def __init__(self):
        om.MPxNode.__init__(self)
        # Create a unique id for this node
        self.id = om.MTypeId(0x00000123)

        # Input attributes
        self.aInput1 = om.MObject()

        # Output attributes
        self.aOutput1 = om.MObject()

    # The main guts of our node
    def compute(self, plug, data):
        if plug == self.aOutput1:
            dataHandle = data.inputValue(self.aInput1)
            inputFloat = dataHandle.asFloat()
            result = math.sin(inputFloat)
            outputHandle = data.outputValue(self.aOutput1)
            outputHandle.setFloat(result)
            data.setClean(plug)
            return om.MStatus.kSuccess
        else:
            return om.MStatus.kUnknownParameter


def creator():
    return omMPx.asMPxPtr(SinNode())


def initialize():
    nAttr = om.MFnNumericAttribute()

    # Create input attributes
    SinNode.aInput1 = nAttr.create("input", "in", om.MFnNumericData.kFloat, 0.0)
    nAttr.setKeyable(True)
    nAttr.setStorable(True)
    nAttr.setReadable(True)
    nAttr.setWritable(True)
    SinNode.addAttributes(SinNode.aInput1)

    # Create output attributes
    SinNode.aOutput1 = nAttr.create("output", "out", om.MFnNumericData.kFloat, 0.0)
    nAttr.setKeyable(False)
    nAttr.setStorable(False)
    nAttr.setReadable(True)
    nAttr.setWritable(False)
    SinNode.addAttributes(SinNode.aOutput1)

    # Make our attributes communicate with each other
    SinNode.attributeAffects(SinNode.aInput1, SinNode.aOutput1)


def initializePlugin(obj):
    plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
    try:
        plugin.registerNode("sinNode", SinNode.id, creator, initialize)
    except:
        raise RuntimeError("Failed to register node")


def uninitializePlugin(obj):
    plugin = omMPx.MFnPlugin(obj)
    try:
        plugin.deregisterNode(SinNode.kPluginNodeId)
    except:
        raise RuntimeError("Failed to register node")
