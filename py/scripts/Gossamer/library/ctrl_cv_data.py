import maya.OpenMaya as om
import maya.cmds as cmds
import json
import os

# reads, writes, and mirrors control cv data shaped by the user using OpenMaya

SCRIPT_LOC = os.path.split(__file__)[0]
os.chdir(SCRIPT_LOC)

def store_cv_data(char_name):

  cmds.select(cmds.ls("*_cc"))

  sel = om.MSelectionList()
  om.MGlobal.getActiveSelectionList(sel)

  obj_iter = om.MItSelectionList(sel)

  dag_points = {}

  while not obj_iter.isDone():
    points = om.MPointArray()
    dag = om.MDagPath()
    obj_iter.getDagPath(dag)

    fnNurbs = om.MFnNurbsCurve(dag)

    fnNurbs.getCVs(points, om.MSpace.kWorld)
    
    point_array = []

    for i in range(points.length()):
      point_array.append([points[i].x,points[i].y,points[i].z]) 

    dag_points[str(dag.partialPathName())] = point_array

    fnNurbs.updateCurve()

    obj_iter.next()

  f = open("shape_data.json", "r")

  shape_data = json.load(f)

  f.close()

  shape_data[char_name] = dag_points
  json_text = json.dumps(shape_data, indent=2)

  f = open("shape_data.json", "w")
  f.write(json_text)
  f.close()

  om.MGlobal.displayInfo("Shape data exported to json format.")

  return dag_points

# data = store_cv_data("Reyda")

def set_cv_data(char_name):
  f = open("shape_data.json", "r")
  shape_data = json.load(f)
  cmds.select(clear=True)
  scene = cmds.ls()

  if char_name not in shape_data.keys():
    om.MGlobal.displayInfo("{0} doesn't have shape data stored.".format(char_name))
    return

  for obj in shape_data[char_name].keys():
    if obj in scene:
      cmds.select(obj, add=True)

  sel = om.MSelectionList()
  om.MGlobal.getActiveSelectionList(sel)

  obj_iter = om.MItSelectionList(sel)
  
  while not obj_iter.isDone():
    dag = om.MDagPath()
    obj_iter.getDagPath(dag)
    full_name = dag.fullPathName()

    fnNurbs = om.MFnNurbsCurve(dag)

    point_array = shape_data[char_name][str(dag.partialPathName())]

    final_point_array = om.MPointArray()

    for point in point_array:
      final_point_array.append(point[0], point[1], point[2])

    fnNurbs.setCVs(final_point_array, om.MSpace.kWorld)
    
    fnNurbs.updateCurve()

    obj_iter.next()

  cmds.select(cl=1)
  
  f.close()

# set_cv_data("Reyda")

def mirror_cv_data(char_name, mirror_mode=0):

  mirror_directions = ["LF", "RT"]

  f = open("shape_data.json", "r")
  shape_data = json.load(f)
  cmds.select([k for k in shape_data[char_name].keys() if mirror_directions[mirror_mode] in k])

  sel = om.MSelectionList()
  om.MGlobal.getActiveSelectionList(sel)

  obj_iter = om.MItSelectionList(sel)
  
  while not obj_iter.isDone():
    dag = om.MDagPath()
    obj_iter.getDagPath(dag)

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

      point_array = shape_data[char_name][str(dag.partialPathName())]

      final_point_array = om.MPointArray()

      for point in point_array:
        flipped_x = -1 * point[0]
        final_point_array.append(flipped_x, point[1], point[2])

      fnNurbs.setCVs(final_point_array, om.MSpace.kWorld)
      
      fnNurbs.updateCurve()

    obj_iter.next()

  cmds.select(cl=1)
  
  f.close()

# mirror_cv_data("SpiderBoss")