import json

import maya.OpenMaya as om
import maya.OpenMayaAnim as omAnim
import maya.cmds as cmds
import maya.mel


def getSkinClusterName(dag):
    """A convenience function for finding the skinCluster deforming a mesh.
    params:
        dag (MDagPath): A MDagPath for the mesh we want to investigate.
    returns:
        skinCluster (str), skinClusterObj (MObject)
    """

    # gets the mesh's full name as a string
    meshName = dag.fullPathName()

    # useful one-liner for finding a skinCluster on a mesh
    skinClusterName = cmds.ls(cmds.listHistory(meshName), type="skinCluster")

    if len(skinClusterName):
        return skinClusterName[0]
    else:
        return None


def getSkinClusterObj(dag):
    """A convenience function for finding the skinCluster deforming a mesh.
    params:
        dag (MDagPath): A MDagPath for the mesh we want to investigate.
    returns:
        skinCluster (str), skinClusterObj (MObject)
    """

    skinClusterName = getSkinClusterName(dag)

    if skinClusterName:
        # get the MObject for that skinCluster node if there is one
        sel = om.MSelectionList()
        sel.add(skinClusterName)
        skinClusterObj = om.MObject()
        sel.getDependNode(0, skinClusterObj)

        return skinClusterObj

    else:
        return None


def getSkinClusterWeights(skinClusterObj, components=None):
    """Returns the weights from a skinCluster and any data necessary for setting
    the weights later down the road
    params:
        skinClusterObj (MObject) : The MObject for the skinCluster you want to get weights from
        components (MObject) : If given, the skinCluster will only gives weights for these verts
    """

    mFnSkinCluster = omAnim.MFnSkinCluster(skinClusterObj)

    # We can find the dag path for the object affected by the skinCluster this way.
    # This assumes the first index in the outputGeometry plug is what we want.
    # I've never run into a situation where that's not the case.
    dag = om.MDagPath()
    mFnSkinCluster.getPathAtIndex(0, dag)

    infObjects = om.MDagPathArray()
    # returns a list of the DagPaths of the joints affecting the mesh
    mFnSkinCluster.influenceObjects(infObjects)
    infCount = om.MScriptUtil(infObjects.length())
    infCountInt = infCount.asInt()
    # c++ utility needed for the get weights function
    infCountPtr = infCount.asUintPtr()

    infIndices = om.MIntArray()

    for i in range(0, infCountInt):
        infIndices.append(i)

    weights = om.MDoubleArray()

    if not components:
        components = om.MObject()

    mFnSkinCluster.getWeights(dag, components, weights, infCountPtr)

    return [weights, infIndices, infObjects]


def setSkinClusterWeights(skinClusterObj, influenceIndices, weights, components=None):
    """ needs API type arrays"""

    mFnSkinCluster = omAnim.MFnSkinCluster(skinClusterObj)

    dag = om.MDagPath()
    mFnSkinCluster.getPathAtIndex(0, dag)

    if not components:
        components = om.MObject()

    mFnSkinCluster.setWeights(dag, components, influenceIndices, weights)


def skin(joints, mesh):
    if not cmds.objExists(mesh):
        raise RuntimeError('Given mesh ' + mesh + ' does not exist in scene.')

    sceneJoints = cmds.ls(type="joint")

    for jnt in joints:
        if jnt not in sceneJoints:
            cmds.select(clear=True)
            cmds.joint(name=jnt)

    cmds.select(joints)
    cmds.select(mesh, add=True)

    cstr = cmds.skinCluster(obeyMaxInfluences=True, weightDistribution=2, skinMethod=0, normalizeWeights=1,
                            dropoffRate=3.0, toSelectedBones=True)

    return cstr[0]


def quickSkin():
    sel = cmds.ls(selection=True)
    joints = cmds.ls(selection=True, type='joint')
    meshes = list(set(sel) - set(joints))

    for mesh in meshes:
        existingSkin = cmds.ls(cmds.listHistory(mesh), type='skinCluster')

        if existingSkin:
            cmds.delete(existingSkin)
            print('deleted {}'.format(existingSkin))

        cmds.select(joints)
        cmds.select(mesh, add=True)

        cstr = cmds.skinCluster(joints, mesh, maximumInfluences=1, obeyMaxInfluences=True, weightDistribution=2,
                                skinMethod=0, normalizeWeights=1, dropoffRate=3.0, toSelectedBones=True)

        cmds.setAttr(cstr[0] + '.maxInfluences', 4)


def bakeDeltaMushToSkinCluster(dag):
    cmds.select(clear=True)
    skinClusterObj = getSkinClusterObj(dag)
    fnMesh = om.MFnMesh(dag)

    originalWeights, infIndices, infObjects = getSkinClusterWeights(skinClusterObj)

    restPoints = om.MPointArray()
    # get rest pose vertex positions
    fnMesh.getPoints(restPoints, om.MSpace.kWorld)
    numVerts = restPoints.length()

    infCount = infObjects.length()

    deltaMush = \
    cmds.deltaMush(dag.fullPathName(), smoothingIterations=5, smoothingStep=0.5, pinBorderVertices=False, envelope=1,
                   after=True)[0]
    # makes the vertices keep their relative distances
    cmds.setAttr(deltaMush + '.distanceWeight', 1.0)

    deltaWeights = originalWeights
    # for i in range(originalWeights.length()):
    #     deltaWeights.append(0.0)

    gMainProgressBar = maya.mel.eval('$tmp = $gMainProgressBar')
    cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True,
                     status='Converting Delta Mush ...', maxValue=infCount)

    try:

        for influenceIndex in range(infCount):
            # move influence object one unit
            infName = infObjects[influenceIndex].partialPathName()

            # this is where the delta mush deformer stops "working"
            # the deformation made by this move isn't affected by the delta mush
            cmds.move(0, 1, 0, infName, preserveChildPosition=1, worldSpace=1, relative=1)

            # if we don't re-declare the fnMesh every time, the points don't update
            fnMesh = om.MFnMesh(dag)
            influencePointLocations = om.MPointArray()
            fnMesh.getPoints(influencePointLocations, om.MSpace.kWorld)

            for vertexIndex in range(influencePointLocations.length()):
                restDeltaDistance = influencePointLocations[vertexIndex].distanceTo(restPoints[vertexIndex])

                # after moving the joint, if the vertex moves, that joint has some influence on the mesh
                if restDeltaDistance > 0:
                    # set the weight for that vertex at that weight index to the distance
                    deltaWeights[(vertexIndex * infCount) + influenceIndex] = restDeltaDistance

            # cmds.refresh(currentView=True)

            cmds.move(0, -1, 0, infName, preserveChildPosition=1, worldSpace=1, relative=1)

            cmds.progressBar(gMainProgressBar, edit=True, step=1)

            # om.MGlobal.displayInfo('Delta Mush conversion at {:.2f}%'.format((influenceIndex / float(infCount)) * 100))

    except Exception as e:
        raise Exception(e)
    finally:
        cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    setSkinClusterWeights(skinClusterObj, infIndices, deltaWeights)

    cmds.select(dag.partialPathName())
    cmds.skinPercent(getSkinClusterName(dag), normalize=True)

    cmds.delete(deltaMush)

    om.MGlobal.displayInfo('Converted Delta Mush to skinCluster weights')


def pruneWeightList(weights, maxInfluence=4):
    """Prunes the given list to have only four non-zero values"""

    infCount = len(weights)
    sortedWeights = list(weights)
    sortedWeights.sort(reverse=True)
    weightIndexPair = []

    prunedWeights = [0.0] * infCount

    if maxInfluence > 1:
        for i in range(infCount):
            if i > (maxInfluence - 1):
                prunedWeights[weights.index(sortedWeights[i])] = 0.0
            else:
                prunedWeights[weights.index(sortedWeights[i])] = sortedWeights[i]
    else:
        prunedWeights[weights.index(sortedWeights[0])] = sortedWeights[0]

    # normalize the list
    prunedWeightsSum = sum(prunedWeights)
    normalizedWeights = [value / prunedWeightsSum for value in prunedWeights]

    return normalizedWeights


def pruneSkinWeights(maxInfluence=4):
    """Sets the weights for each vertex to the average of its neighbors."""

    originalSel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(originalSel)

    cmds.select(cmds.polyListComponentConversion(toVertex=True))

    # get the selected mesh and components
    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    if not sel.length():
        return

    selectedComponents = om.MObject()
    dag = om.MDagPath()
    sel.getDagPath(0, dag, selectedComponents)

    dag.extendToShape()

    if dag.apiType() != 296:
        om.MGlobal.displayError("Selection must be a polygon mesh.")
        return

    # get the skin cluster object
    skinCluster = getSkinClusterName(dag)
    skinClusterObj = getSkinClusterObj(dag)

    cmds.skinPercent(skinCluster, pruneWeights=0.005)

    mFnSkinCluster = omAnim.MFnSkinCluster(skinClusterObj)
    infObjects = om.MDagPathArray()
    # returns a list of the DagPaths of the joints affecting the mesh
    mFnSkinCluster.influenceObjects(infObjects)
    infCountUtils = om.MScriptUtil(infObjects.length())
    # c++ utility needed for the get/set weights functions
    infCountPtr = infCountUtils.asUintPtr()
    infCount = infCountUtils.asInt()
    influenceIndices = om.MIntArray()
    # create an MIntArray that just counts from 0 to infCount
    for i in range(0, infCount):
        influenceIndices.append(i)

    oldWeights = om.MDoubleArray()
    # don't use the selectedComponents MObject we made since we want to get the weights for each vertex
    # on this mesh, not just the selected one
    emptyObj = om.MObject()
    mFnSkinCluster.getWeights(dag, selectedComponents, oldWeights, infCountPtr)

    # newWeights just starts as a copy of oldWeights
    newWeights = om.MDoubleArray(oldWeights)

    # iterate over the selected verts
    itVerts = om.MItMeshVertex(dag, selectedComponents)
    i = 0
    numOverInfluenced = 0

    while not itVerts.isDone():
        thisVertWeightIndex = i * infCount
        vertWeights = list(newWeights[thisVertWeightIndex: thisVertWeightIndex + infCount])

        nonZeroCount = 0

        for w in range(len(vertWeights)):
            if vertWeights[w] > 0.0:
                nonZeroCount += 1

        if nonZeroCount > maxInfluence:
            numOverInfluenced += 1
            # makes the weights for the closest vertex equal to the outer vertex
            newWeights[thisVertWeightIndex: thisVertWeightIndex + infCount] = pruneWeightList(vertWeights, maxInfluence)

        i += 1
        itVerts.next()

    # set weights all at once
    if numOverInfluenced:
        mFnSkinCluster.setWeights(dag, selectedComponents, influenceIndices, newWeights, True, oldWeights)

    om.MGlobal.setActiveSelectionList(originalSel)

    om.MGlobal.displayInfo(
        'Pruned {0} over-influenced vertices from {1}.'.format(numOverInfluenced, dag.partialPathName()))

    return [mFnSkinCluster, dag, selectedComponents, influenceIndices, oldWeights, False, oldWeights]


def getSkinClusterWeightDict(skinClusterObj):
    '''Return the weight dictionary for the given skin cluster'''

    weights, influenceIndices, influenceObjects = getSkinClusterWeights(skinClusterObj)

    # A single influence's weights is its column of the weight matrix

    weightDict = {}
    numInfluences = influenceIndices.length()

    for i in range(numInfluences):
        weightDict[influenceObjects[i].partialPathName()] = weights[i:: numInfluences]

    return weightDict


def getSkinClusterObjFromShape(shape):
    sel = om.MSelectionList()
    sel.add(shape)
    mobj = om.MObject()
    sel.getDependNode(0, mobj)

    itDG = om.MItDependencyGraph(mobj, om.MFn.kSkinClusterFilter, om.MItDependencyGraph.kUpstream,
                                 om.MItDependencyGraph.kDepthFirst, om.MItDependencyGraph.kNodeLevel)

    if itDG.isDone():
        # No skin cluster. Are you sure you passed a mesh?
        return None

    skinClusterMObjArray = om.MObjectArray()

    while not itDG.isDone():
        currentNode = itDG.currentItem()
        skinClusterMObjArray.append(currentNode)

        itDG.next()

    # Return the first item in the array
    return skinClusterMObjArray[0]
