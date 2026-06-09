# bm_smooth_skinned_curve
import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.OpenMayaAnim as omAnim
import maya.mel

# smooth skinned nurbs curve weights using a moving average method


def find_skin_cluster(dag):

    mesh_name = dag.full_pathName()

    skin_cluster = cmds.ls(cmds.listHistory(mesh_name), type="skinCluster")

    if len(skin_cluster) > 0:
        sel = om.MSelectionList()
        sel.add(skin_cluster[0])
        skin_cluster_obj = om.MObject()
        sel.getDependNode(0, skin_cluster_obj)

        return skin_cluster[0], skin_cluster_obj

    else:
        return None, None


# right now the effect is pretty strong. Let's see how we can make a
# multiplier for that.


def smooth_weights(curve=None, smooth_strength=0.25):

    # before we get our selection, convert our selection to CVs
    # this has to be done with a MEL command I guess

    if not curve:
        return

    maya.mel.eval("SelectCurveCVsAll;")

    # first get the selection
    sel = om.MGlobal.getActiveSelectionList()
    dag = om.MDagPath()
    components = om.MObject()

    sel.getDagPath(0, dag, components)

    # get the amount of CVs on the curve
    fnCurve = om.MFnNurbsCurve(dag)
    num_cvs = fnCurve.numCVs()

    # no, MFnSkinCluster needs the MObject of the skinCluster on the curve
    # we've written this before...
    skin_cluster, skin_cluster_obj = find_skin_cluster(dag)

    # hack to maybe this undoable
    cmds.skinPercent(skin_cluster, normalize=True)

    fnSkin = omAnim.MFnSkinCluster(skin_cluster_obj)

    # get the weights first
    inf_objects = om.MDagPathArray()
    fnSkin.influenceObjects(inf_objects)

    inf_count = om.MScriptUtil(inf_objects.length())
    num_influences = inf_count.asInt()
    inf_count_ptr = inf_count.asUintPtr()

    influence_indices = om.MIntArray()
    for i in range(0, num_influences):
        influence_indices.append(i)

    old_weights = om.MDoubleArray()

    fnSkin.getWeights(dag, components, old_weights, inf_count_ptr)

    new_weights = om.MDoubleArray()

    # first set our first CV's weights to what it was before
    for i in range(num_influences):
        new_weights.append(old_weights[i])

    # now do our moving average method starting at CV index 1 and ending at CV index num_cvs - 2
    # (second CV to second to last CV)
    for i in range(1, num_cvs - 1):
        # get the weights of the neighboring CVs. That's at index (i-1) *
        # num_influences to i * num_influences
        left_cv_weights = old_weights[(i - 1) * num_influences : i * num_influences]
        this_cv_weights = old_weights[i * num_influences : (i + 1) * num_influences]
        right_cv_weights = old_weights[
            (i + 1) * num_influences : (i + 2) * num_influences
        ]

        # we're just converting our MDoubleArray to another type of list now.
        # So just skip that!
        avg_weight_vector = []

        u = 0
        for u in range(num_influences):
            avg_weight_vector.append(
                (left_cv_weights[u] + this_cv_weights[u] + right_cv_weights[u]) / 3.0
            )

        # set this cv's weights to the average weight vector (will need to
        # double check this is normalized)
        for num in avg_weight_vector:
            new_weights.append(num)

    # and set our last CV's weights to what it was before
    last_cv_weight_slice = old_weights[
        (num_cvs - 2) * num_influences : (num_cvs - 1) * num_influences
    ]

    for weight in last_cv_weight_slice:
        new_weights.append(weight)

    # now let's go through both the old and new weight lists one more time and make a third list.
    # this list will be weighted based on the user's smooth_strength multiplier

    # where 0 is fully the old weights and 1 is fully the new weights
    weighted_list = om.MDoubleArray()
    for i in range(old_weights.length()):
        weighted_weight = (1 - smooth_strength) * old_weights[i] + (
            (smooth_strength) * new_weights[i]
        )
        weighted_list.append(weighted_weight)

    # set our new weights on the curve
    fnSkin.setWeights(
        dag, components, influence_indices, weighted_list, False, old_weights
    )


# smooth_weights(curve=cmds.ls(sl=1), smooth_strength=.25)
