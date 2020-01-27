# weights

import json
import os
from xml.etree import ElementTree

import maya.cmds as cmds
import maya.OpenMaya as om

from . import weightutils

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
        dag = om.MDagPath()
        itSel.getDagPath(dag)

        dagName = str(dag.partialPathName())

        skin = cmds.ls(cmds.listHistory(dagName), type='skinCluster') or []

        if skin:
            # exports by vertex index. Changes to the vert order will break this
            # with the new 'format' argument, this might not be backwards compatible... - _-
            cmds.deformerWeights("{0}.weights".format(dagName), deformer=skin[0],
                                 export=True, format='XML', path=weightsDir, method="index")

        print "Saved weights for {}".format(dagName)

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
        raise ValueError("<{0}.weights> doesn't have a matching object in scene.".format(objName))
    
    # look for and delete old clusters if they exist
    existingSkinCluster = cmds.ls(cmds.listHistory(objName), type="skinCluster") or []

    if existingSkinCluster:
        cmds.delete(existingSkinCluster)

    jointList = getJointsFromXML(weightsPath)

    cmds.select(jointList)
    cmds.select(objName, add=True)

    # add the skin cluster
    newCluster = cmds.skinCluster(maximumInfluences=4,
                                 weightDistribution=1,
                                 obeyMaxInfluences=True,
                                 toSelectedBones=True,
                                 skinMethod=0,
                                 bindMethod=1)

    cmds.deformerWeights("{0}.weights".format(objName), im=True, path=weightsDirname, 
                        ignoreName=True, format='XML', method="index", deformer=newCluster[0])
    cmds.select(objName)
    cmds.skinPercent(newCluster[0], normalize=True)
    om.MGlobal.displayInfo("Loaded skinCluster weights onto {0}".format(objName))

    print ">>> Weight data loaded from {0}".format(weightsPath)



