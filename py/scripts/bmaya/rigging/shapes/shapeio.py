import json

import maya.OpenMaya as om
import maya.cmds as cmds

def save(cvsPath):

    cmds.select(cmds.ls("*_ctrl"))

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    objIter = om.MItSelectionList(sel)

    cvPoints = {}

    # get cv point data
    while not objIter.isDone():
        points = om.MPointArray()
        dag = om.MDagPath()
        objIter.getDagPath(dag)

        fnNurbs = om.MFnNurbsCurve(dag)

        # gets the cvs in world space
        fnNurbs.getCVs(points, om.MSpace.kWorld)
        
        pointArray = []

        for i in range(points.length()):
            pointArray.append([points[i].x,points[i].y,points[i].z]) 

        cvPoints[str(dag.partialPathName())] = pointArray

        fnNurbs.updateCurve()

        objIter.next()

    with open(cvsPath, "w+") as f:
        jsonData = json.dumps(cvPoints, indent=4)
        f.write(jsonData)


    om.MGlobal.displayInfo("Shape data exported to json format.")
    print ">>> Shape data saved to " + cvsPath

    return cvPoints

def load(cvsPath):

    shapeData = None

    with open(cvsPath, "r") as f:
        shapeData = json.load(f)

    scene = cmds.ls()

    cmds.select([obj for obj in shapeData.keys() if obj in scene])

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    objIter = om.MItSelectionList(sel)
    
    while not objIter.isDone():
        dag = om.MDagPath()
        objIter.getDagPath(dag)
        full_name = dag.fullPathName()

        fnNurbs = om.MFnNurbsCurve(dag)

        storedPoints = shapeData[str(dag.partialPathName())]

        finalPoints = om.MPointArray()

        for point in storedPoints:
            finalPoints.append(*point)

        fnNurbs.setCVs(finalPoints, om.MSpace.kWorld)
        
        fnNurbs.updateCurve()

        objIter.next()

    cmds.select(cl=1)
    print ">>> Shape data loaded from " + cvsPath
    
def mirror(cvsPath):

    mirrorDirections = ["L", "R"]

    shapeData = None

    with open(cvsPath, "r") as f:
        shapeData = json.load(f)

    scene = cmds.ls()
    cmds.select([obj for obj in shapeData.keys() if obj in scene and mirrorDirections[0] in obj])

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    objIter = om.MItSelectionList(sel)
    
    while not objIter.isDone():
        dag = om.MDagPath()
        objIter.getDagPath(dag)
        dagName = str(dag.partialPathName())

        sel = om.MSelectionList()

        mirrorName = dagName.replace(mirrorDirections[0], mirrorDirections[-1])

        if mirrorName in scene:
            sel.add(mirrorName)

            mirrorDag = om.MDagPath()
            sel.getDagPath(0, mirrorDag)

            fnNurbs = om.MFnNurbsCurve(mirrorDag)

            pointArray = shapeData[dagName]

            finalPointArray = om.MPointArray()

            for point in pointArray:
                flippedX = -1 * point[0]
                finalPointArray.append(flippedX, point[1], point[2])

            fnNurbs.setCVs(finalPointArray, om.MSpace.kWorld)
            
            fnNurbs.updateCurve()

            shapeData[mirrorName] = finalPointArray

            objIter.next()
        else:
            print "No mirror for control: " + dagName
            objIter.next()

    
    cmds.select(cl=1)

    print('CV data mirrored.')

    save(cvsPath)    

#########################################
#########################################

# def cvIO(mode="import"):
#     if mode not in ["import","export","mirror"]:
#         raise ValueError("Invalid mode for cvIO")
    
#     import os
    
#     from Osiris.lib.base.asset import Asset
    
#     if cmds.objExists("*_CHAR"):
#         for char in cmds.ls("*_CHAR"):
            
#             rootDir = cmds.getAttr(char + ".rootDir")
#             cvsDir = cmds.getAttr(char + ".cvsPath")
            
#             if mode == "import":
#                 cvs.load(os.path.join(rootDir, cvsDir))
#             elif mode == "export":
#                 Asset.versionFile(os.path.join(rootDir, cvsDir))
#                 cvs.save(os.path.join(rootDir, cvsDir))
#             elif mode == "mirror":
#                 cvs.mirror(os.path.join(rootDir, cvsDir))
