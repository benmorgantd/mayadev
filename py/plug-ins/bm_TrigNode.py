import maya.OpenMayaMPx as omMPx
import maya.OpenMaya as om
import math

"""
TrigNode v01.1 by Ben Morgan

Basic node for Maya that gets common trig functions into a single node. Designed for readability.

Based off of ideas from "Practical Maya Programming With Python" by Robert Galanakis
"""


# create our class that inherits from OpnMayaMPx.MPxNode
class TrigNode(omMPx.MPxNode):
    # give it a unique id
    id = om.MTypeId(0x00218)

    # declare our input attributes
    input = om.MObject()

    frequency = om.MObject()
    amplitude = om.MObject()
    sinCosOffset = om.MObject()

    # declare our output attributes
    outSin = om.MObject()
    outCos = om.MObject()
    outTan = om.MObject()

    outSec = om.MObject()
    outCsc = om.MObject()
    outCot = om.MObject()

    # outType will be an enum that allows the user to switch between output as radians and degrees
    outType = om.MObject()

    def compute(self, plug, data):
        if plug not in [TrigNode.outSin, TrigNode.outCos, TrigNode.outTan, TrigNode.outSec, TrigNode.outCsc,
                        TrigNode.outCot]:
            raise ValueError("kUnknownParameter")

        # get our input value from TrigNode.input as a float
        inputValue = data.inputValue(TrigNode.input).asFloat()

        # get if the user wants the output to be calculated as radians or degrees
        outTypeValue = data.inputValue(TrigNode.outType).asInt()

        frequencyValue = data.inputValue(TrigNode.frequency).asFloat()
        amplitudeValue = data.inputValue(TrigNode.amplitude).asFloat()
        sinCosOffsetValue = data.inputValue(TrigNode.sinCosOffset).asFloat()

        # get the trig results from our input values
        sinResult = amplitudeValue * math.sin(sinCosOffsetValue + frequencyValue * inputValue)
        cosResult = amplitudeValue * math.cos(sinCosOffsetValue + frequencyValue * inputValue)
        tanResult = amplitudeValue * math.sin(frequencyValue * inputValue)

        # we use copysign because modulus will give us numbers between 0 and 1 but we want the domain to be -1 to 1
        # sec and csc functions output values between -pi/2 and pi/2
        secResult = amplitudeValue * math.copysign(math.asin(frequencyValue * (abs(inputValue) % 1)),
                                                   inputValue)
        cscResult = amplitudeValue * math.copysign(math.acos(frequencyValue * (abs(inputValue) % 1)),
                                                   inputValue)
        # cot has a domain of all real numbers
        cotResult = amplitudeValue * math.atan(frequencyValue * inputValue)

        # create the handles for our output attributes
        sinHandle = data.outputValue(TrigNode.outSin)
        cosHandle = data.outputValue(TrigNode.outCos)
        tanHandle = data.outputValue(TrigNode.outTan)

        secHandle = data.outputValue(TrigNode.outSec)
        cscHandle = data.outputValue(TrigNode.outCsc)
        cotHandle = data.outputValue(TrigNode.outCot)

        # set the values for our output attributes as the user desires
        if outTypeValue == 1:
            sinHandle.setFloat(math.degrees(sinResult))
            cosHandle.setFloat(math.degrees(cosResult))
            tanHandle.setFloat(math.degrees(tanResult))

            secHandle.setFloat(math.degrees(secResult))
            cscHandle.setFloat(math.degrees(cscResult))
            cotHandle.setFloat(math.degrees(cotResult))
        else:
            sinHandle.setFloat(sinResult)
            cosHandle.setFloat(cosResult)
            tanHandle.setFloat(tanResult)

            secHandle.setFloat(secResult)
            cscHandle.setFloat(cscResult)
            cotHandle.setFloat(cotResult)

        data.setClean(plug)


def creator():
    # standard creator function for a Maya plugin
    return omMPx.asMPxPtr(TrigNode())


def initialize():
    # shorten OpenMaya attributes as variables for readability
    nAttr = om.MFnNumericAttribute()
    eAttr = om.MFnEnumAttribute()
    kFloat = om.MFnNumericData.kFloat

    """ Input Attributes """

    # create our input attribute of type kFloat and a default value 0.0
    TrigNode.input = nAttr.create("input", "in", kFloat, 0.0)
    # input values should be keyable, storable, readable, and writable
    nAttr.setKeyable(True)
    nAttr.setStorable(True)
    nAttr.setReadable(True)
    nAttr.setWritable(True)
    # add our attribute to the node
    TrigNode.addAttribute(TrigNode.input)

    # create our frequency attribute. This controls the period of the functions
    TrigNode.frequency = nAttr.create("frequency", "f", kFloat, 1.0)
    nAttr.setKeyable(True)
    nAttr.setStorable(True)
    nAttr.setReadable(True)
    nAttr.setWritable(True)
    TrigNode.addAttribute(TrigNode.frequency)

    # create our amplitude attribute. This controls the... amplitude of the functions
    TrigNode.amplitude = nAttr.create("amplitude", "a", kFloat, 1.0)
    nAttr.setKeyable(True)
    nAttr.setStorable(True)
    nAttr.setReadable(True)
    nAttr.setWritable(True)
    TrigNode.addAttribute(TrigNode.amplitude)

    # create our offset attribute which can offset the values of the function and also serve as a driver
    TrigNode.sinCosOffset = nAttr.create("sinCosOffset", "off", kFloat, 0.0)
    nAttr.setKeyable(True)
    nAttr.setStorable(True)
    nAttr.setReadable(True)
    nAttr.setWritable(True)
    TrigNode.addAttribute(TrigNode.sinCosOffset)

    # outType is an enum attribute that the user can change between Radians (0) and Degrees (1)
    TrigNode.outType = eAttr.create("outType", "ot", 0)
    eAttr.addField("Radians", 0)
    eAttr.addField("Degrees", 1)
    eAttr.setKeyable(True)
    eAttr.setStorable(True)
    eAttr.setReadable(True)
    eAttr.setWritable(True)
    TrigNode.addAttribute(TrigNode.outType)

    """ Output Attributes """

    TrigNode.outSin = nAttr.create("outputSin", "outSin", kFloat, 0.0)
    # output attributes should only be readable
    nAttr.setKeyable(False)
    nAttr.setStorable(False)
    nAttr.setReadable(True)
    nAttr.setWritable(False)
    TrigNode.addAttribute(TrigNode.outSin)

    TrigNode.outCos = nAttr.create("outputCos", "outCos", kFloat, 0.0)
    nAttr.setKeyable(False)
    nAttr.setStorable(False)
    nAttr.setReadable(True)
    nAttr.setWritable(False)
    TrigNode.addAttribute(TrigNode.outCos)

    TrigNode.outTan = nAttr.create("outputTan", "outTan", kFloat, 0.0)
    nAttr.setKeyable(False)
    nAttr.setStorable(False)
    nAttr.setReadable(True)
    nAttr.setWritable(False)
    TrigNode.addAttribute(TrigNode.outTan)

    TrigNode.outSec = nAttr.create("outputSec", "outSec", kFloat, 0.0)
    # output attributes should only be readable
    nAttr.setKeyable(False)
    nAttr.setStorable(False)
    nAttr.setReadable(True)
    nAttr.setWritable(False)
    TrigNode.addAttribute(TrigNode.outSec)

    TrigNode.outCsc = nAttr.create("outputCsc", "outCsc", kFloat, 0.0)
    nAttr.setKeyable(False)
    nAttr.setStorable(False)
    nAttr.setReadable(True)
    nAttr.setWritable(False)
    TrigNode.addAttribute(TrigNode.outCsc)

    TrigNode.outCot = nAttr.create("outputCot", "outCot", kFloat, 0.0)
    nAttr.setKeyable(False)
    nAttr.setStorable(False)
    nAttr.setReadable(True)
    nAttr.setWritable(False)
    TrigNode.addAttribute(TrigNode.outCot)

    """ Establish attribute relationships """
    TrigNode.attributeAffects(TrigNode.input, TrigNode.outSin)
    TrigNode.attributeAffects(TrigNode.input, TrigNode.outCos)
    TrigNode.attributeAffects(TrigNode.input, TrigNode.outTan)
    TrigNode.attributeAffects(TrigNode.input, TrigNode.outSec)
    TrigNode.attributeAffects(TrigNode.input, TrigNode.outCsc)
    TrigNode.attributeAffects(TrigNode.input, TrigNode.outCot)

    TrigNode.attributeAffects(TrigNode.outType, TrigNode.outSin)
    TrigNode.attributeAffects(TrigNode.outType, TrigNode.outCos)
    TrigNode.attributeAffects(TrigNode.outType, TrigNode.outTan)
    TrigNode.attributeAffects(TrigNode.outType, TrigNode.outSec)
    TrigNode.attributeAffects(TrigNode.outType, TrigNode.outCsc)
    TrigNode.attributeAffects(TrigNode.outType, TrigNode.outCot)

    TrigNode.attributeAffects(TrigNode.frequency, TrigNode.outSin)
    TrigNode.attributeAffects(TrigNode.frequency, TrigNode.outCos)
    TrigNode.attributeAffects(TrigNode.frequency, TrigNode.outTan)
    TrigNode.attributeAffects(TrigNode.frequency, TrigNode.outSec)
    TrigNode.attributeAffects(TrigNode.frequency, TrigNode.outCsc)
    TrigNode.attributeAffects(TrigNode.frequency, TrigNode.outCot)

    TrigNode.attributeAffects(TrigNode.amplitude, TrigNode.outSin)
    TrigNode.attributeAffects(TrigNode.amplitude, TrigNode.outCos)
    TrigNode.attributeAffects(TrigNode.amplitude, TrigNode.outTan)
    TrigNode.attributeAffects(TrigNode.amplitude, TrigNode.outSec)
    TrigNode.attributeAffects(TrigNode.amplitude, TrigNode.outCsc)
    TrigNode.attributeAffects(TrigNode.amplitude, TrigNode.outCot)

    TrigNode.attributeAffects(TrigNode.sinCosOffset, TrigNode.outSin)
    TrigNode.attributeAffects(TrigNode.sinCosOffset, TrigNode.outCos)


def initializePlugin(obj):
    plugin = omMPx.MFnPlugin(obj, "Ben Morgan", "1.0", "Any")
    try:
        plugin.registerNode("trigNode", TrigNode.id, creator, initialize)
    except:
        raise RuntimeError("Failed to register node")


def uninitializePlugin(obj):
    plugin = omMPx.MFnPlugin(obj)
    try:
        plugin.deregisterNode(TrigNode.id)
    except:
        raise RuntimeError("Failed to register node")
