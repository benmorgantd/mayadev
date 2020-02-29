import maya.cmds as cmds
import os
import maya.OpenMaya as om

mod_string = "+ ReydaTools 1.0 MODULE_LOC"

def make_shelf():
  if cmds.shelfLayout("ReydaTools", p="ShelfLayout", ex=1):
    cmds.deleteUI("ReydaTools", layout=1)

  cmds.shelfLayout("ReydaTools", p="ShelfLayout")

def make_buttons():
  # blendshape combination system main menu
  cmds.shelfButton(p="ReydaTools",
                   iol="PKR",
                   c="import CharacterPicker.modules.character_picker_view as view\n##reload(view)\nview.show_ui()",
                   stp="python",
                   i="pythonFamily.png",
                   style="iconAndTextVertical")

def install():
  maya_app_dir = cmds.internalVar(userAppDir=1)
  try:
    # have the user browse for the package directory on their system
    package_dir = cmds.fileDialog2(okCaption="Set ReydaTools Folder",
                                   fileMode=3,
                                   caption="Browse to ReydaTools Folder")[0]
  except TypeError:
    # will happen if the user exits the file dialog
    om.MGlobal.displayError("Install of the ReydaTools module failed.")
    return

  # make the \modules directory if it doesn't already exist
  if not os.path.exists(os.path.join(maya_app_dir, "modules")):
    om.MGlobal.displayInfo("Making /modules directory in user's App Directory.")
    os.makedirs(os.path.join(maya_app_dir, "modules"))

  # create our mod file in the user's maya modules directory
  mod_file = open(os.path.join(maya_app_dir, "modules", "ReydaTools.mod"), "w+")

  write_str = mod_string.replace("MODULE_LOC", package_dir)
  # write the contents of our package file
  mod_file.write(write_str)
  mod_file.close()

  success_message = "Successfully installed the ReydaTools module.\n\nPlease restart Maya to finish installation."
  om.MGlobal.displayInfo(success_message)
  cmds.confirmDialog(title="Success", message=success_message)

  make_shelf()
  make_buttons()

install()


