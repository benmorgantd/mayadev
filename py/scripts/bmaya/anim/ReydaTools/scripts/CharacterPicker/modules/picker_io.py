import json
import os
import maya.cmds as cmds
import CharacterPicker.modules.custom_graphics_items as custom_graphics_items
##reload(custom_graphics_items)

from bmaya.lib.Qt import QtWidgets, QtGui, QtCore

# save a picker data to a json file
def save_picker(scene_items, background_path=""):
  picker_dict = {}
  picker_dict["info"] = {"Version": 0.8, "Author":"Ben Morgan"}
  picker_dict["background"] = background_path
  picker_dict["buttons"] = {}

  # store all button data
  for i in range(0, len(scene_items)):
    button_dict = {}
    # QPos
    # button position is captured relative to the size of the QGraphicsView it's in
    button_pos = scene_items[i].scenePos()
    button_dict["position"] = [button_pos.x(), button_pos.y()]
    # QRect
    button_dict["rect"] = [scene_items[i].rect().width(), scene_items[i].rect().height()]
    # QBrush
    button_dict["color"] = scene_items[i].brush().color().getRgbF()
    # Selection List
    button_dict["selection"] = scene_items[i].selection_list
    button_dict["selection_type"] = scene_items[i].selection_type
    button_dict["button_selection_list"] = scene_items[i].button_selection_list
    picker_dict["buttons"][scene_items[i].name] = button_dict

  try:
    fullpath = cmds.fileDialog2(okCaption="Save",
                                fileMode=0,
                                fileFilter="Picker Files (*.pkr);;",
                                caption="Save Picker File",
                                startingDirectory=os.path.join(os.path.dirname(__file__), "..", "layouts"))[0]
  
  except:
    return

  with open(fullpath, "w") as outfile:
    json.dump(picker_dict, outfile, indent=2)

  return picker_dict

def load_picker(scene, fullpath=None):
  print os.path.split(__file__)[0]
  if not fullpath:
    try:
      # have the user navigate to the picker file
      fullpath = cmds.fileDialog2(okCaption="Open",
                                  fileMode=1,
                                  fileFilter="Picker Files (*.pkr);;",
                                  caption="Open Picker File",
                                  startingDirectory=os.path.join(os.path.dirname(__file__), "..", "layouts"))[0]
    except:
      return

  with open(fullpath, "r") as open_file:
    file_str = open_file.read()

  json_data = json.loads(file_str)

  return json_data, fullpath