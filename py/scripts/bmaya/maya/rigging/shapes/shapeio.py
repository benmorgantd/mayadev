import json


import maya.api.OpenMaya as om


import maya.cmds as cmds


from bmaya.core.util import fileUtils


from bmaya.maya.util import nameUtils


from bmaya.core import log


def save(cvsPath):

    cmds.select(cmds.ls("*_ctrl"))

    sel = om.MSelectionList()

    om.MGlobal.getActiveSelectionList(sel)

    obj_iter = om.MItSelectionList(sel)

    shape_data = {}

    # get cv point data

    while not obj_iter.isDone():

        points = om.MPointArray()

        dag = om.MDagPath()

        obj_iter.getDagPath(dag)

        fnNurbs = om.MFnNurbsCurve(dag)

        # gets the cvs in world space

        fnNurbs.getCVs(points, om.MSpace.kWorld)

        point_array = []

        for i in range(points.length()):

            point_array.append([points[i].x, points[i].y, points[i].z])

        shape_data[str(dag.partialPathName())] = point_array

        fnNurbs.updateCurve()

        obj_iter.next()

    fileUtils.versionFile(cvsPath)

    with open(cvsPath, "w+") as f:

        jsonData = json.dumps(shape_data, indent=4)

        f.write(jsonData)

    om.MGlobal.displayInfo("Shape data exported.")

    return shape_data


def load(cvsPath):

    shapeData = None

    with open(cvsPath, "r") as f:

        shapeData = json.load(f)

    scene = cmds.ls()

    cmds.select([obj for obj in shapeData.keys() if obj in scene])

    sel = om.MSelectionList()

    om.MGlobal.getActiveSelectionList(sel)

    obj_iter = om.MItSelectionList(sel)

    while not obj_iter.isDone():

        dag = om.MDagPath()

        obj_iter.getDagPath(dag)

        fn_nurbs = om.MFnNurbsCurve(dag)

        storedPoints = shapeData[str(dag.partialPathName())]

        finalPoints = om.MPointArray()

        for point in storedPoints:

            finalPoints.append(*point)

        fn_nurbs.setCVs(finalPoints, om.MSpace.kWorld)

        fn_nurbs.updateCurve()

        obj_iter.next()

    cmds.select(cl=1)

    log.info(">>> Shape data loaded from " + cvsPath)


def mirror(cvsPath):
    mirror_directions = ["_L_", "_R_"]

    shapeData = None

    with open(cvsPath, "r") as f:

        shapeData = json.load(f)

    scene = cmds.ls()

    cmds.select([obj for obj in shapeData.keys()

                if obj in scene and mirror_directions[0] in obj])

    sel = om.MSelectionList()

    om.MGlobal.getActiveSelectionList(sel)

    objIter = om.MItSelectionList(sel)

    while not objIter.isDone():

        dag = om.MDagPath()

        objIter.getDagPath(dag)

        dagName = str(dag.partialPathName())

        sel = om.MSelectionList()

        mirrorName = nameUtils.replace(
            mirror_directions[0], mirror_directions[-1])

        if mirrorName in scene:

            sel.add(mirrorName)

            mirrorDag = om.MDagPath()

            sel.getDagPath(0, mirrorDag)

            fnNurbs = om.MFnNurbsCurve(mirrorDag)

            point_array = shapeData[dagName]

            final_point_array = om.MPointArray()

            for point in point_array:

                flippedX = -1 * point[0]

                final_point_array.append(flippedX, point[1], point[2])

            fnNurbs.setCVs(final_point_array, om.MSpace.kWorld)

            fnNurbs.updateCurve()

            shapeData[mirrorName] = final_point_array

            objIter.next()

        else:

            log.info("No mirror for control: " + dagName)

            objIter.next()

    cmds.select(cl=1)

    log.info('CV data mirrored.')

    save(cvsPath)


def remove_shape_data(cvsPath, controls=[]):
    """Remove the data for the given controls from the cv file"""

    shape_data = None

    with open(cvsPath, "r") as f:

        shape_data = json.load(f)

    modified_shape_data = shape_data

    shape_data_keys = modified_shape_data.keys()

    for control in controls:

        if control in shape_data_keys:

            modified_shape_data.pop(control)

    fileUtils.versionFile(cvsPath)

    with open(cvsPath, "w+") as f:

        json_data = json.dumps(modified_shape_data, indent=4)

        f.write(json_data)

    om.MGlobal.displayInfo("Shape data removed for {0}".format(controls))
