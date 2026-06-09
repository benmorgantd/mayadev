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

        fn_nurbs = om.MFnNurbsCurve(dag)

        # gets the cvs in world space

        fn_nurbs.getCVs(points, om.MSpace.kWorld)

        point_array = []

        for i in range(points.length()):

            point_array.append([points[i].x, points[i].y, points[i].z])

        shape_data[str(dag.partialPathName())] = point_array

        fn_nurbs.updateCurve()

        obj_iter.next()

    fileUtils.version_file(cvsPath)

    with open(cvsPath, "w+") as f:

        json_data = json.dumps(shape_data, indent=4)

        f.write(json_data)

    om.MGlobal.displayInfo("Shape data exported.")

    return shape_data


def load(cvsPath):

    shape_data = None

    with open(cvsPath, "r") as f:

        shape_data = json.load(f)

    scene = cmds.ls()

    cmds.select([obj for obj in shape_data.keys() if obj in scene])

    sel = om.MSelectionList()

    om.MGlobal.getActiveSelectionList(sel)

    obj_iter = om.MItSelectionList(sel)

    while not obj_iter.isDone():

        dag = om.MDagPath()

        obj_iter.getDagPath(dag)

        fn_nurbs = om.MFnNurbsCurve(dag)

        stored_points = shape_data[str(dag.partialPathName())]

        final_points = om.MPointArray()

        for point in stored_points:

            final_points.append(*point)

        fn_nurbs.setCVs(final_points, om.MSpace.kWorld)

        fn_nurbs.updateCurve()

        obj_iter.next()

    cmds.select(cl=1)

    log.info("Shape data loaded from " + cvsPath)


def mirror(cvsPath):
    mirror_directions = ["_L_", "_R_"]

    shape_data = None

    with open(cvsPath, "r") as f:

        shape_data = json.load(f)

    scene = cmds.ls()

    cmds.select(
        [
            obj
            for obj in shape_data.keys()
            if obj in scene and mirror_directions[0] in obj
        ]
    )

    sel = om.MSelectionList()

    om.MGlobal.getActiveSelectionList(sel)

    obj_iter = om.MItSelectionList(sel)

    while not obj_iter.isDone():

        dag = om.MDagPath()

        obj_iter.getDagPath(dag)

        dag_name = str(dag.partialPathName())

        sel = om.MSelectionList()

        mirror_name = nameUtils.replace(mirror_directions[0], mirror_directions[-1])

        if mirror_name in scene:

            sel.add(mirror_name)
            mirror_dag = om.MDagPath()

            sel.getDagPath(0, mirror_dag)

            fn_nurbs = om.MFnNurbsCurve(mirror_dag)

            point_array = shape_data[dag_name]

            final_point_array = om.MPointArray()

            for point in point_array:

                flipped_x = -1 * point[0]

                final_point_array.append(flipped_x, point[1], point[2])

            fn_nurbs.setCVs(final_point_array, om.MSpace.kWorld)

            fn_nurbs.updateCurve()

            shape_data[mirror_name] = final_point_array

            obj_iter.next()

        else:

            log.info("No mirror for control: " + dag_name)

            obj_iter.next()

    cmds.select(cl=1)

    log.info("CV data mirrored.")

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

    fileUtils.version_file(cvsPath)

    with open(cvsPath, "w+") as f:

        json_data = json.dumps(modified_shape_data, indent=4)

        f.write(json_data)

    om.MGlobal.displayInfo("Shape data removed for {0}".format(controls))
