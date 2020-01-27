# gossamer ui view

# our standard imports when using Qt.py
import maya.cmds as cmds
import maya.OpenMayaUI as omui
import Gossamer.ui.gossamer_ui_model as model 
reload(model)
import os

from lib.Qt import QtWidgets

try:
  from shiboken import wrapInstance
except:
  from shiboken2 import wrapInstance

def delete_ui(window_object):
  """Delete existing UI in Maya"""
  
  if cmds.window(window_object, query=True, exists=True):
    cmds.deleteUI(window_object)

def show_ui():
  # Launches the UI and ensures we don't get multiple instances of it.
  window_object = "GossamerRigWindow"
  delete_ui(window_object)
  ui = model.GossamerModel(window_title = "Gossamer Rigging Window",
                             window_object = window_object,
                             designer_file = os.path.join(os.path.split(__file__)[0], "gossamer_design.ui"),
                             parent=wrapInstance(long(omui.MQtUtil.mainWindow()), QtWidgets.QWidget))
  ui.show()
