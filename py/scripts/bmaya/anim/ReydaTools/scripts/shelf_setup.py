# Reyda Shelf
import maya.cmds as cmds
import maya.OpenMaya as om

def make_shelf():
  if cmds.shelfLayout("ReydaTools", p="ShelfLayout", ex=1):
    cmds.deleteUI("ReydaTools", layout=1)

  cmds.shelfLayout("ReydaTools", p="ShelfLayout")

def make_buttons():
  # blendshape combination system main menu
  cmds.shelfButton(p="ReydaTools",
                   iol="PKR",
                   c="import CharacterPicker.modules.character_picker_view as view\nreload(view)\nview.show_ui()",
                   stp="python",
                   i="pythonFamily.png",
                   style="iconAndTextVertical")

  cmds.shelfButton(p="ReydaTools",
                   iol="POSE",
                   c="import PoseStorage.modules.bm_poseStorage_ui as ui\nui._show_ui()",
                   stp="python",
                   i="pythonFamily.png",
                   style="iconAndTextVertical")

  om.MGlobal.displayInfo("Reyda Tools shelf setup successful")

make_shelf()
make_buttons()