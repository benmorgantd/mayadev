import json
import os

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

    with open(cvsPath, "r+") as f:

        jsonData = json.dumps(cvPoints, indent=4)

        f.write(jsonData)


    om.MGlobal.displayInfo("Shape data exported to json format.")
    print ">>> Shape data saved to " + cvsPath

    return cvPoints

def load(cvsPath):

    shapeData = None

    with open(cvsPath, "r+") as f:
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
    
def mirror(cvsPath, mirror_mode=0):

    mirror_directions = ["LF", "RT"]

    f = open("shapeData.json", "r")
    shapeData = json.load(f)
    cmds.select([k for k in shapeData[char_name].keys() if mirror_directions[mirror_mode] in k])

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    objIter = om.MItSelectionList(sel)
    
    while not objIter.isDone():
        dag = om.MDagPath()
        objIter.getDagPath(dag)

        sel = om.MSelectionList()
        mirror_exists=True

        try:
            sel.add(str(dag.partialPathName().replace(mirror_directions[mirror_mode],mirror_directions[mirror_mode - 1])))
        except RuntimeError:
            print "no mirror"
            mirror_exists = False

        if mirror_exists:
            mirror_dag = om.MDagPath()
            sel.getDagPath(0, mirror_dag)

            fnNurbs = om.MFnNurbsCurve(mirror_dag)

            pointArray = shapeData[char_name][str(dag.partialPathName())]

            final_pointArray = om.MPointArray()

            for point in pointArray:
                flipped_x = -1 * point[0]
                final_pointArray.append(flipped_x, point[1], point[2])

            fnNurbs.setCVs(final_pointArray, om.MSpace.kWorld)
            
            fnNurbs.updateCurve()

        objIter.next()

    cmds.select(cl=1)
    
    f.close()


#########################################
#########################################

def cvIO(mode="import"):
    if mode not in ["import","export","mirror"]:
        raise ValueError("Invalid mode for cvIO")
    
    import os
    
    from Osiris.lib.base.asset import Asset
    
    if cmds.objExists("*_CHAR"):
        for char in cmds.ls("*_CHAR"):
            
            rootDir = cmds.getAttr(char + ".rootDir")
            cvsDir = cmds.getAttr(char + ".cvsPath")
            
            if mode == "import":
                cvs.load(os.path.join(rootDir, cvsDir))
            elif mode == "export":
                Asset.versionFile(os.path.join(rootDir, cvsDir))
                cvs.save(os.path.join(rootDir, cvsDir))
            elif mode == "mirror":
                cvs.mirror(os.path.join(rootDir, cvsDir))
