"""Purpose:

Methods for working with bounding boxes in maya. These are used by various components to perform common

tasks that involve bounding boxes, such as framing the scene, etc.
"""

import maya.api.OpenMaya as om


def get_scene_bounding_box():
    """Returns the bounding box around the DAGs in the scene"""

    sel = om.MSelectionList()

    bounding_box = om.MBoundingBox()

    it_dag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kMesh)

    while not it_dag.isDone():

        dag = om.MDagPath()

        it_dag.getPath(dag)

        fn_dag = om.MFnDagNode(dag)

        dag_bounding_box = fn_dag.boundingBox()

        dag_bounding_box.transformUsing(dag.inclusiveMatrix())

        bounding_box.expand(dag_bounding_box)

        it_dag.next()

    return bounding_box


def get_bounding_box_center(bounding_box):

    center = bounding_box.center()

    return [center.x, center.y, center.z]
