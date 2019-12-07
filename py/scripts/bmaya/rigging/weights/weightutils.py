# skinCluster tools
import json

import maya.OpenMaya as om
import maya.OpenMayaAnim as omAnim
import maya.cmds as cmds

def getSkinClusterObj(dag):
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
        # get the MObject for that skinCluster node if there is one
        sel = om.MSelectionList()
        sel.add(skinClusterName[0])
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

    cstr = cmds.skinCluster(obeyMaxInfluences=True,
                            weightDistribution=2,
                            skinMethod=0,
                            normalizeWeights=1,
                            dropoffRate=3.0,
                            toSelectedBones=True)

    return cstr[0]

def quickSkin():

    sel = cmds.ls(selection=True)
    joints = cmds.ls(selection=True, type='joint')
    meshes = list(set(sel) - set(joints))

    for mesh in meshes:
        existingSkin = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
        
        if existingSkin:
            cmds.delete(existingSkin)
            print 'deleted ', existingSkin

        cmds.select(joints)
        cmds.select(mesh, add=True)

        cstr = cmds.skinCluster(joints, mesh, 
                                maximumInfluences=1,
                                obeyMaxInfluences=True,
                                weightDistribution=2,
                                skinMethod=0,
                                normalizeWeights=1,
                                dropoffRate=3.0,
                                toSelectedBones=True)

        cmds.setAttr(cstr[0] + '.maxInfluences', 4)