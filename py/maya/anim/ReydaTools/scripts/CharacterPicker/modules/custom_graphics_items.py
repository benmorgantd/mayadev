import maya.cmds as cmds
import maya.OpenMaya as om
import CharacterPicker.modules.rig_tools as rig_tools
reload(rig_tools)


from lib.Qt import QtWidgets, QtGui, QtCore

class CustomGraphicsScene(QtWidgets.QGraphicsScene):
  def __init__(self, parent=None, namespace=None, pixmap_path=None):
    super(CustomGraphicsScene, self).__init__(parent)

    self.namespace = namespace
    self.pixmap_path = pixmap_path
    # we need a dictionary that'll allow us to reference button objects with their text name
    self.button_count = 0
    self.buttons = {}

    self.selection_color = QtGui.QColor()
    self.selection_color.setRgbF(1, 1, 1, 0.85)
    self.selection_brush = QtGui.QBrush(self.selection_color)

    self.setup_menu()

    self.previous_object_selection = []

  def setup_menu(self):
    self.menu = QtWidgets.QMenu()
    self.menu.setTitle("Menu")

    # returns a QAction
    # toggle nurbs curve visibility
    toggle_curve_vis = self.menu.addAction("Toggle Controls")
    toggle_curve_vis.triggered.connect(lambda: self.toggle_nurbs())

    # Toggle Ik/Fk action
    toggle_ikfk = self.menu.addAction("Toggle IK/FK")
    toggle_ikfk.triggered.connect(lambda: self.toggle_ikfk())

    # separator
    self.menu.addSeparator()

    # Add Anim layer
    add_anim_layer = self.menu.addAction("Make Anim Layer from Selection")
    add_anim_layer.triggered.connect(lambda: self.add_anim_layer())

  def toggle_nurbs(self):
    panels = cmds.getPanel(type="modelPanel")
    for panel in panels:
      nurbs_vis = cmds.modelEditor(panel, query=True, nurbsCurves=True)
      cmds.modelEditor(panel, edit=True, nurbsCurves = not nurbs_vis)

    self.menu.hide()

  def add_anim_layer(self):
    anim_layer = cmds.animLayer("AnimLayer1", addSelectedObjects=True, override=True)
    self.menu.hide()

  def toggle_ikfk(self):
    rig_tools.toggle_ikfk()
    self.menu.hide()

  # todo: rewrite logic of selection method to include control select/deselect
  def select_buttons(self, selection, control_pressed, was_right_click, shift_pressed):
    if was_right_click:
      return

    namespace = self.namespace.currentText()

    if control_pressed or shift_pressed:
      new_selection = self.previous_object_selection
    else:
      new_selection = []

    sel_len = len(selection)

    if not sel_len:
      # clear selection if they click no buttons
      cmds.select(clear=True)
      for button_object in self.previous_object_selection:
        # reset button colors
        button_object.setBrush(button_object.color)
      self.previous_object_selection = []
      return
    else:
      for button_object in selection:
        if control_pressed and button_object in self.previous_object_selection:
          # remove it from the selection
          new_selection.remove(button_object)          
          # and reset its color
          button_object.setBrush(button_object.color)
        elif control_pressed and button_object not in self.previous_object_selection:
          # don't add it to the selection at all
          pass
        elif shift_pressed and button_object not in self.previous_object_selection:
          # append it to the selection
          button_object.setBrush(self.selection_brush)
          new_selection.append(button_object)
        else:
          # start a new selection
          button_object.setBrush(self.selection_brush)
          new_selection.append(button_object)

    new_maya_selection = []
    group_selection_objects = []

    for button_object in new_selection:
      if button_object.selection_type == "group":
        for button_name in button_object.button_selection_list:
          self.buttons[button_name].setBrush(self.selection_brush)
          new_maya_selection += self.buttons[button_name].selection_list
          group_selection_objects.append(self.buttons[button_name])
      else:
        new_maya_selection += button_object.selection_list

    for button in self.previous_object_selection:
      if button not in new_selection and button not in group_selection_objects:
        if not control_pressed and not shift_pressed:
          button.setBrush(button.color)

    cmds.select([namespace + obj for obj in new_maya_selection], replace=True)
    self.previous_object_selection = new_selection + group_selection_objects

  def drawBackground(self, painter, rect):
    pixmap = QtGui.QPixmap(self.pixmap_path)
    painter.drawPixmap(0, 0, pixmap.width(), pixmap.height(), pixmap)
    self.update()

  def mousePressEvent(self, event):
    QtWidgets.QGraphicsScene.mousePressEvent(self, event)

    self.menu.hide()

    # right click functionality 
    if event.button() == QtCore.Qt.RightButton:
      global_cursor_pos = QtGui.QCursor().pos()
      widget_space_cursor_pos = self.views()[0].mapFromGlobal(global_cursor_pos)
      self.menu.move(widget_space_cursor_pos)
      self.menu.show()

  def mouseReleaseEvent(self, event):

    QtWidgets.QGraphicsScene.mouseReleaseEvent(self, event)

    self.select_buttons(self.selectedItems(), 
                        QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier,
                        event.button() == QtCore.Qt.RightButton,
                        QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier)

class CustomGraphicsView(QtWidgets.QGraphicsView):
  def __init__(self, parent=None, designer_ui=None, scene=None):
    # is a child of the QMainWindow class
    super(CustomGraphicsView, self).__init__(parent)

    self.designer_ui = designer_ui
    self.scene = scene
    self.scene.menu.setParent(self)
    self.scene.menu.hide()
    self.setDragMode(QtWidgets.QGraphicsView.DragMode(2))
    # no scroll bars
    self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy(1))
    self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy(1))
    self.setFocusPolicy(QtCore.Qt.NoFocus)

    if self.scene:
      self.setScene(self.scene)

  def wheelEvent(self, event, zoom_delta=0.15):
    # ctrl+scroll to zoom
    delta = event.delta()

    if delta > 0:
      self.scale(1 + zoom_delta, 1 + zoom_delta)
    else:
      self.scale(1 - zoom_delta, 1 - zoom_delta)

class CustomRect(QtWidgets.QGraphicsRectItem):
  def __init__(self, width, height, x=0, y=0, parent=None, selection_list=[], color=None, selection_type="single", name="button_1", button_selection_list=[]):
    super(CustomRect, self).__init__(parent)

    self.name = name
    self.selection_list = []
    self.selection_type = selection_type
    self.button_selection_list = button_selection_list

    if selection_type == "single":
      self.selection_list = selection_list
    elif selection_type == "group" and len(self.button_selection_list):
      pass
    else:
      om.MGlobal.displayError("Incorrect selection type. Accepts ['single', 'group']")
      return
    self.start_loc = None
    if len(self.selection_list):
      self.setToolTip("+ {0}".format("\n+ ".join(self.selection_list)))
    else:
      self.setToolTip("Selects a group of buttons.")
    self.color = QtGui.QColor()


    if color == 0:
      # red
      self.color.setRgbF(249/255.0, 51/255.0, 51/255.0, 1)
    elif color == 1:
      # yellow
      self.color.setRgbF(249/255.0, 223/255.0, 51/255.0, 1)
    elif color == 2:
      # blue
      self.color.setRgbF(51/255.0, 114/255.0, 249/255.0, 1)
    elif color == 3:
      # green
      self.color.setRgbF(51/255.0, 249/255.0, 97/255.0, 1)
    elif color == None:
      # gray
      self.color.setRgbF(164/255.0, 171/255.0, 171/255.0, 1)
    else:
      self.color = color

    brush = QtGui.QBrush(self.color)
    self.setBrush(brush)

    self.setRect(0, 0, width, height)
    self.setPos(x,y)

    self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
    self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)

