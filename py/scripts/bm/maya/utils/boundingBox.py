import maya.OpenMaya as om

def getSceneBoundingBox():
    """Returns the bounding box around the DAGs in the scene"""

    sel = om.MSelectionList()

    boundingBox = om.MBoundingBox()

    itDag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kMesh)

    while not itDag.isDone():
        dag = om.MDagPath()
        itDag.getPath(dag)

        fnDag = om.MFnDagNode(dag)
        dagBoundingBox = fnDag.boundingBox()
        dagBoundingBox.transformUsing(dag.inclusiveMatrix())

        boundingBox.expand(dagBoundingBox)

        itDag.next()

    return boundingBox


def getBoundingBoxCenter(boundingBox):
    center = boundingBox.center()

    return [center.x, center.y, center.z]
