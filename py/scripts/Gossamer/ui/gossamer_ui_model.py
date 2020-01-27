# Gossamer UI Model

# our standard imports when using Qt.py
import maya.cmds as cmds
import maya.OpenMayaUI as omui
import maya.OpenMaya as om
import maya.mel as mel

import os
from lib.Qt import QtWidgets, QtGui, QtCore, QtCompat
import Gossamer.creator as creator
reload(creator)
import Gossamer.ui.custom_qt_classes as custom_qt_classes
reload(custom_qt_classes)

class GossamerModel(QtWidgets.QMainWindow):
  def __init__(self, window_title, window_object, designer_file, parent=None):
    # is a child of the QMainWindow class
    super(GossamerModel, self).__init__(parent)

    # Data from the qt designer file will held under the designer_ui variable
    self.gossamer_ui = QtCompat.load_ui(designer_file)
    self.pixmap_path = None
    self.picker_path = None

    # for Gossamer rigs
    self.creator = None

    # Sets the design from our designer file to be the one to use for QMainWindow
    self.setCentralWidget(self.gossamer_ui)
    # Set window flags using the inherited methods from QMainWindow
    self.setWindowTitle(window_title)
    self.setObjectName(window_object)
    self.resize(545, 715)

    self.setup_tree_widget()
    self.setup_file_menu()
    self.setup_buttons()

    # find any existing character nodes
    self.find_character_nodes()

    self.modules = []

    first_item = self.treewidget.itemAt(0, 0)
    if first_item:
      first_item.setSelected(True)
      self.treewidget.load_module_node(first_item.text(0))

  def setup_tree_widget(self):
    self.treewidget = custom_qt_classes.CustomTreeWidget()
    # self.gossamer_ui.gridLayout.addWidget(self.treewidget, 0, 0, 1, 1)
    
  def setup_file_menu(self):
    self.gossamer_ui.actionNew_Character.triggered.connect(lambda:self.add_character())

  def setup_buttons(self):
    # self.gossamer_ui.build_button.clicked.connect(lambda: self.build_controls())
    pass

  def add_character(self, charnode=None):
    if charnode:
      self.creator = creator.Creator(char_name=charnode.replace("_CharNode",""), charnode=charnode)
      self.creator.make_CharNode()
      self.treewidget.setHeaderLabel(charnode.replace("_CharNode",""))
      # load modules into tree view
      for module in cmds.listConnections("{0}.modules".format(self.get_charnode())):
        self.add_to_tree_view(module)

    else:
      # set character name with popup window
      cmds.promptDialog(message="Character Name:", text="NewCharacter1")
      name = cmds.promptDialog(query=True, text=True)
      self.creator = creator.Creator(char_name=name)
      self.creator.make_CharNode()
      self.treewidget.setHeaderLabel(name)
      self.add_to_tree_view("root_module")

  def get_charnode(self):
    return self.creator.charnode.node

  def build_module(self, module_type=None):
    if not module_type or module_type not in ["Root", "single_joint"]:
      om.MGlobal.displayError("Incorrect module type")
      return
    else:
      if module_type == "Root":
        # roots get directly made without any additional setup
        module = self.creator.make_Root()
        cmds.group("root", name="skeleton", parent=self.creator.charnode.top_node)
      # all other modules need additional information 
      # (joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow", child_of=False, constrained_to=False)
      elif module_type == "single_joint":
        # add Single Joint to setup stage
        pass
      self.add_to_tree_view(module.node)
    cmds.select(clear=True)

  def add_to_tree_view(self, node=None):
    self.treewidget.setColumnCount(1)
    widget = QtWidgets.QTreeWidgetItem(self.treewidget)
    widget.setText(0, node)

  def build_controls(self):
    for module in self.treewidget.selectedItems():
      self.build_module(self.get_module_type(module.text(0)))

  def get_module_type(self, module_node):
    return cmds.getAttr("{0}.type".format(module_node))

  def connect_controls(self):
    if self.creator:
      self.creator.connect_bind_joints()

  def find_character_nodes(self):
    for node in cmds.ls(type="network"):
      if "_CharNode" in node:
        self.add_character(charnode=node)

  def cleanup_house(self):
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))
    cmds.createDisplayLayer("root_cc_grp", name="ctrl")

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      cmds.setAttr(obj + ".sx", l=1, cb=0, k=0)
      cmds.setAttr(obj + ".sy", l=1, cb=0, k=0)
      cmds.setAttr(obj + ".sz", l=1, cb=0, k=0)

    cmds.select(cl=1)
