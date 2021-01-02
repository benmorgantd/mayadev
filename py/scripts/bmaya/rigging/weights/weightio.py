# weights

import json
import os
from xml.etree import ElementTree

import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.core import fileio
from bmaya import mayanode

def getJointsFromXML(weightsDir):
  tree = ElementTree.parse(weightsDir)
  root = tree.getroot()

  joints = []

  for child in root:
    if child.tag == "weights":
      joints.append(child.attrib["source"])

  return joints


def save(weightsDir):
    # Saves each selected object to a file in the given directory
    # with its name.

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)
    
    itSel = om.MItSelectionList(sel)

    if not os.path.exists(weightsDir):
        os.makedirs(weightsDir)

    while not itSel.isDone():
        current_mobj = om.MObject()
        itSel.getDependNode(current_mobj)
        meshTransform = mayanode.DagNode(current_mobj)

        skinCluster = meshTransform.shape.getSkinCluster()

        filename = os.path.join(weightsDir, meshTransform + '.weights')
        if os.path.exists(filename):
            # version the file
            fileio.versionFile(filename)

        if skinCluster:
            # exports by vertex index. Changes to the vert order will break this
            # with the new 'format' argument, this might not be backwards compatible... - _-
            cmds.deformerWeights(meshTransform + ".weights", deformer=skinCluster,
                                 export=True, path=weightsDir, method="index")
        else:
            print meshTransform + ' has no skin cluster to save.'
            itSel.next()

        print "Saved weights for {}".format(meshTransform)

        itSel.next()

def load(weightsPath):
    """Tries to load a single weights file onto a matching item in the scene"""

    if not os.path.exists(weightsPath):
        raise ValueError("Given weights path doesn't exist")

    if not weightsPath.endswith('.weights'):
        raise ValueError('Given file must be in .weights format')

    objName = os.path.basename(weightsPath).replace(".weights", "")
    weightsDirname = os.path.dirname(weightsPath)

    if not cmds.objExists(objName):
        om.MGlobal.displayInfo("{0} does not exist in scene.".format(objName))
        return

    meshTransform = mayanode.DagNode(objName)

    print 'Loading weights for <' + meshTransform + '> ...'
    
    # look for and delete old clusters if they exist
    existingSkinCluster = meshTransform.shape.getSkinCluster()

    if existingSkinCluster:
        cmds.delete(existingSkinCluster)

    jointList = getJointsFromXML(weightsPath)

    cmds.select(cl=1)

    for jnt in jointList:
        if not cmds.objExists(jnt):
            newJnt = cmds.joint(name=jnt)
            cmds.select(cl=1)

    cmds.select(jointList)
    cmds.select(meshTransform, add=True)

    # add the skin cluster
    # Add in options to load from previous saved skin cluster's settings since
    # we may not want 4 max influences or linear blending
    newCluster = cmds.skinCluster(weightDistribution=1, obeyMaxInfluences=False, toSelectedBones=True, skinMethod=0,
                                  bindMethod=1)

    cmds.deformerWeights("{0}.weights".format(meshTransform), im=True, path=weightsDirname,
                        ignoreName=True, method="index", deformer=newCluster[0])
    cmds.select(meshTransform)
    cmds.skinPercent(newCluster[0], normalize=True)
    om.MGlobal.displayInfo("Loaded skinCluster weights onto {0}".format(meshTransform))

    print ">>> Weight data loaded from {0}".format(weightsPath)



