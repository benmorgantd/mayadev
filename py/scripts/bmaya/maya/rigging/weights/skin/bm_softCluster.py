import maya.api.OpenMaya as om
import maya.cmds as cmds


def softCluster():
    """
    :return: A cluster deformer with the same weights as the soft selection
    """
    # get our selection, rich selection, and a dag path
    sel = om.MSelectionList()

    try:
        softSel = om.MRichSelection()
        om.MGlobal.getRichSelection(softSel)
        softSel.getSelection(sel)
    except RuntimeError:
        raise RuntimeError("No components are selected")

    dag = om.MDagPath()
    sel.getDagPath(0, dag)

    # TODO: Find a better way of doing this using the API
    # Get the average location of our selection and store it as our cluster's
    # future pivot
    selLocs = cmds.xform(cmds.ls(sl=1), q=1, t=1, ws=1)
    selLen = float(len(selLocs[0::3]))
    selSums = [sum(selLocs[0::3]), sum(selLocs[1::3]), sum(selLocs[2::3])]
    selPivot = [selSums[0] / selLen, selSums[1] / selLen, selSums[2] / selLen]

    print dag.apiType()

    if dag.apiType() == 296:
        # mesh
        objIter = om.MItSelectionList(sel, om.MFn.kMeshVertComponent)
        componentType = "vtx"
    elif dag.apiType() == 267:
        # nurbs curve
        objIter = om.MItSelectionList(sel, om.MFn.kCurveCVComponent)
        componentType = "cv"
    elif dag.apiType() == 279:
        # lattice
        objIter = om.MItSelectionList(sel, om.MFn.kLatticeComponent)
        componentType = "pt"
    else:
        raise TypeError("Object type not supported.")

    # stores the strings that will be used for full component selection when
    # we make our cluster
    elemList = []
    # stores the weights for each selected component
    weights = om.MFloatArray()
    # store the index of each selected component
    indexList = om.MIntArray()
    # on lattices, stores an array of the triple-indexed strings representing
    # our indexes
    latticeIndexList = []
    # MObject initiated from DagPath that will be used by our MFnComponent
    # type functions
    components = om.MObject()

    # iterate through each selected mesh (there should only be one)
    while not objIter.isDone():
        # get the dag path of the current iter object
        objIter.getDagPath(dag, components)
        # if the apiType is a mesh or a nurbs curve:
        if dag.apiType() in [296, 267]:
            # function set for doing getting information from our selection.
            # Pass it the components object.
            fnComp = om.MFnSingleIndexedComponent(components)
            fnComp.getElements(indexList)
            # iterate though selection, add its weight influence to our weights
            # list
            for i in range(indexList.length()):
                if fnComp.hasWeights():
                    weights.append(fnComp.weight(i).influence())
                else:
                    weights.append(1)
                # append the string representing our selection to the elements
                # list
                elemList.append(
                    "%s.%s[%i]" %
                    (dag.full_pathName(), componentType, indexList[i]))
        # in the case that our object is a Lattice:
        elif dag.apiType() == 279:
            # int arrays that store the triple indexed data (a lattice has
            # points with 3D indexes)
            u = om.MIntArray()
            v = om.MIntArray()
            w = om.MIntArray()
            # make a function set so that we can get information from these
            # elements
            fnComp = om.MFnTripleIndexedComponent(components)
            fnComp.getElements(u, v, w)

            # iterate through selection, add its weight influence to our
            # weights list
            for i in range(u.length()):
                if fnComp.hasWeights():
                    weights.append(fnComp.weight(i).influence())
                else:
                    weights.append(1)
                # append a string that represents the 3D index for the current
                # lattice point
                latticeIndexList.append("[%i][%i][%i]" % (u[i], v[i], w[i]))
                # append the string representing our selection to the elements
                # list
                elemList.append(
                    "%s.pt[%i][%i][%i]" %
                    (dag.full_pathName(), u[i], v[i], w[i]))

        objIter.next()

    # TODO: Create cluster, set its geometry and weights using API
    # select all elements influenced by our soft selection and make our cluster
    cmds.select(elemList)
    cluster = cmds.cluster(n="softCluster#")
    cmds.xform(cluster[1], piv=selPivot)
    i = 0

    if dag.apiType() in [296, 267]:
        # set the weights on our cluster for mesh and nurbsCurve objects
        while i < weights.length():
            cmds.percent(
                cluster[0],
                "%s.%s[%i]" %
                (dag.full_pathName(),
                 componentType,
                 indexList[i]),
                v=weights[i])
            i += 1
    else:
        while i < weights.length():
            # set the weights on our cluster for lattices
            cmds.percent(
                cluster[0],
                "%s.pt%s" %
                (dag.full_pathName(),
                 latticeIndexList[i]),
                v=weights[i])
            i += 1

    return cluster
