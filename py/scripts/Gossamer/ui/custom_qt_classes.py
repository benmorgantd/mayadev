# custom qt classes

from lib.Qt import QtWidgets, QtGui, QtCore, QtCompat
import maya.cmds as cmds

class CustomTreeWidget(QtWidgets.QTreeWidget):
  def __init__(self, parent=None):
    super(CustomTreeWidget, self).__init__(parent)

    self.setFocusPolicy(QtCore.Qt.FocusPolicy(0))
    self.setHeaderLabel("Character")

  def currentChanged(self, current, previous):
    # populate the list view with the contents of that selection
    if len(self.selectedItems()):
      module_node = self.selectedItems()[0].text(0)
      self.load_module_node(module_node)
