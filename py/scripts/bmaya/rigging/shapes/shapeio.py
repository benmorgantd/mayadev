import json

import maya.OpenMaya as om
import maya.cmds as cmds

from bmaya.core import fileio
from bmaya import mayanode


def save(cvsPath):
    cmds.select(cmds.ls("*_ctrl"))

    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    objIter = om.MItSelectionList(sel)

    shapeData = {}

    # get cv point data
    while not objIter.isDone():
        _mobj = om.MObject()
        objIter.getDependNode(_mobj)
        _ctrl = mayanode.DagNode(_mobj)

        points = _ctrl.shape.getPoints()
        pointArray = []

        for i in range(points.length()):
            pointArray.append([points[i].x, points[i].y, points[i].z])

        shapeData[str(_ctrl.shortName)] = pointArray

        # _ctrl.fnNurbs.updateCurve()

        objIter.next()

    fileio.versionFile(cvsPath)

    with open(cvsPath, "w+") as f:
        jsonData = json.dumps(shapeData, indent=4)
        f.write(jsonData)

    om.MGlobal.displayInfo("Shape data exported.")

    return shapeData


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
        _mobj = om.MObject()
        objIter.getDependNode(_mobj)
        _ctrl = mayanode.DagNode(_mobj)

        storedPoints = shapeData[str(_ctrl.shortName)]

        finalPoints = om.MPointArray()

        for point in storedPoints:
            finalPoints.append(*point)

        _ctrl.fnNurbsCurve.setPoints(finalPoints, space='world')

        objIter.next()

    cmds.select(cl=1)
    print ">>> Shape data loaded from " + cvsPath


def mirror(cvsPath):
    mirrorDirections = ["_L_", "_R_"]

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


def removeShapeData(cvsPath, controls=[]):
    """Remove the data for the given controls from the cv file"""

    shapeData = None

    with open(cvsPath, "r") as f:
        shapeData = json.load(f)

    modifiedShapeData = shapeData

    shapeDataKeys = modifiedShapeData.keys()

    for control in controls:
        if control in shapeDataKeys:
            modifiedShapeData.pop(control)

    fileio.versionFile(cvsPath)

    with open(cvsPath, "w+") as f:
        jsonData = json.dumps(modifiedShapeData, indent=4)
        f.write(jsonData)

    om.MGlobal.displayInfo("Shape data removed for {0}".format(controls))
