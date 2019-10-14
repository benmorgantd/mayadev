# weights

import json
import os

import maya.cmds as cmds
import maya.OpenMaya as om

from . import weightutils

def save(weightsDir):
    # Saves each selected object to a file in the given directory
    # with its name.

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)
    
    itSel = om.MItSelectionList(sel)

    while not itSel.isDone():
        dag = om.MDagPath()
        itSel.getDagPath(dag)

        skinClusterObj = weightutils.getSkinClusterObj(dag)

        if skinClusterObj:
            weights, infIndices, infObjects = weightutils.getSkinClusterWeights(skinClusterObj)

            infObjectNames = []
            # maya's MDoubleArray can easily be cast into a regular list so json can read it
            weights = list(weights)

            for i in range(0, infObjects.length()):
                infObjectNames.append(str(infObjects[i].partialPathName()))

            jsonData = {"weights": list(weights), 
                        "influenceObjects": infObjectNames,
                        "influenceIndices": list(infIndices)}

            dagName = str(dag.partialPathName())

            weightsPath = os.path.join(weightsDir, (dagName + ".weights"))

            if not os.path.exists(weightsPath):
                os.mkdir(os.path.split(weightsPath)[0])

            with open(weightsPath, "w") as f:
                json.dump(jsonData, f, indent=4)

            print "Saved weights for {}".format(dagName)


        itSel.next()

def load(weightsPath):
    """Tries to load a single weights file onto a matching item in the scene"""

    if not os.path.exists(weightsPath):
        raise ValueError("Given weights path doesn't exist")

    objName = os.path.basename(weightsPath).replace(".weights", "")

    if objName not in cmds.ls():
        raise ValueError("<{0}.weights> doesn't have a matching object in scene.".format(objName))

    sel = om.MSelectionList()
    sel.add(objName)
    dag = om.MDagPath()
    sel.getDagPath(0, dag)

    existingSkinCluster = cmds.ls(cmds.listHistory(dag.partialPathName()), type="skinCluster") or list()

    if existingSkinCluster:
        cmds.delete(existingSkinCluster)

    weightData = None

    # get the data from the weight file for this mesh
    with open(weightsPath, "r") as f:
        weightData = json.load(f)

    # create a new skinCluster
    weightutils.skin(weightData["influenceObjects"], 
                     dag.partialPathName())

    skinClusterObj = weightutils.getSkinClusterObj(dag)

    # we need to convert the json data back to API arrays
    infArray = om.MIntArray()
    weightArray = om.MDoubleArray()

    for index in weightData["influenceIndices"]:
        infArray.append(index)

    for weightValue in weightData["weights"]:
        weightArray.append(weightValue)

    weightutils.setSkinClusterWeights(skinClusterObj,
                                      infArray,
                                      weightArray)

    print ">>> Weight data loaded from {0}".format(weightsPath)



