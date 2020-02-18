import maya.OpenMaya as om
import maya.OpenMayaAnim as omAnim


def find_under_influenced_verts(max_influences=4):

  start_time = time.time()

  cmds.select(cmds.polyListComponentConversion(toVertex=True), replace=True)

  sel = om.MSelectionList()
  om.MGlobal.getActiveSelectionList(sel)

  available_verts = om.MSelectionList()

  obj_iter = om.MItSelectionList(sel)

  while not obj_iter.isDone():
    components = om.MObject()
    mesh_dag = om.MDagPath()
    obj_iter.getDagPath(mesh_dag, components)

    skin_cluster, skin_cluster_obj = find_skin_cluster(mesh_dag)

    if skin_cluster_obj:
      mFnSkinCluster = omAnim.MFnSkinCluster(skin_cluster_obj)
      inf_objects = om.MDagPathArray()
      mFnSkinCluster.influenceObjects(inf_objects)

      inf_count = om.MScriptUtil(inf_objects.length())
      inf_count_int = inf_count.asInt()
      inf_count_ptr = inf_count.asUintPtr()

      influence_indices = om.MIntArray()
      for i in range(0, inf_count_int):
        influence_indices.append(i)

      old_weights = om.MDoubleArray()

      mFnSkinCluster.getWeights(mesh_dag, components, old_weights, inf_count_ptr)

      new_weights = om.MDoubleArray()

      for i in range(0, old_weights.length(), inf_count_int):
        this_vertex_weights = old_weights[i:i + inf_count_int]
        this_vertex_num_influences = inf_count_int - list(this_vertex_weights).count(0.0)
        # here we could sort, prune, relax, etc
        
        if this_vertex_num_influences < max_influences:
          available_verts.add("{0}.vtx[{1}]".format(mesh_dag.fullPathName(), i))

    obj_iter.next()

  # option to not do this too
  om.MGlobal.setActiveSelectionList(available_verts)

  om.MGlobal.displayInfo("{0} greedy vertices pruned in {1} seconds.".format(available_verts.length(), time.time() - start_time))

# prune_influences(max_influences=3)