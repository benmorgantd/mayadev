# sdk readwrite

import maya.cmds as cmds
import json
import os


def store_sdk_pose(driver=None, driver_attr=None):
  # get objects driven by that driver attribute
  driven_objects = cmds.setDrivenKey("{0}.{1}".format(driver, driver_attr), query=True, driven=True)

  print driven_objects

  """
  obj_keys = {}

  for obj in selection:
    key = {}
    for i in ["t","r"]:
      for j in ["x","y","z"]:
        key[i + j] = cmds.getAttr("{0}.{1}{2}".format(obj, i, j))
    obj_keys[obj] = key


  write_data = {"driver": driver, "driver_attr": driver_attr, "driver_val":cmds.getAttr("{0}.{1}".format(driver, driver_attr)), "obj_keys": obj_keys}

  f = open("sdk_data.json", "r")
  sdk_data = json.load(f)
  f.close()

  sdk_data[pose_name] = write_data
  json_text = json.dumps(sdk_data, indent=2)

  f = open("sdk_data.json", "w")
  f.write(json_text)
  f.close()
  """

store_sdk_pose(driver="browRegion_cc", driver_attr="LF_browLowerer")