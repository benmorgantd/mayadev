
# our standard imports when using Qt.py
import maya.cmds as cmds
import maya.OpenMayaUI as omui
import maya.OpenMaya as om
import maya.mel as mel

import os
from bmaya.lib.Qt import QtWidgets, QtGui, QtCore, QtCompat

import CharacterPicker.modules.custom_graphics_items as graphics_items
#reload(graphics_items)

import CharacterPicker.modules.picker_io as picker_io
#reload(picker_io)


class PickerModel(QtWidgets.QMainWindow):
  def __init__(self, window_title, window_object, designer_file, parent=None):
    # is a child of the QMainWindow class
    super(PickerModel, self).__init__(parent)

    self.locked = False

    # Data from the qt designer file will held under the designer_ui variable
    self.designer_ui = QtCompat.load_ui(designer_file)
    self.pixmap_path = None
    self.picker_path = None

    # for Gossamer rigs
    self.charnode = None

    self.button_id = 1

    # Sets the design from our designer file to be the one to use for QMainWindow
    self.setCentralWidget(self.designer_ui)
    # variable used to launch a color picker window. Needs to be declared outside of the function or else it will be 
    # deleted immediately after it's created
    self.color_dialog = QtWidgets.QColorDialog()
    # Set window flags using the inherited methods from QMainWindow
    self.setWindowTitle(window_title)
    self.setObjectName(window_object)
    self.resize(550, 725)
    self.tab_scenes = []
    self.tab_views = []

    # Make connections for the contents of our window
    self.setup_button_connections()
    self.setup_menu_connections()
    self.find_namespaces()
    self.look_for_charnode()

  def setup_button_connections(self):
    self.designer_ui.resizeButton.clicked.connect(lambda: self.scale_buttons())
    self.designer_ui.heightInput.valueChanged.connect(lambda: self.scale_buttons())
    self.designer_ui.widthInput.valueChanged.connect(lambda: self.scale_buttons())
    self.designer_ui.lockButton.clicked.connect(lambda: self.toggle_lock())

  def setup_menu_connections(self):
    # File
    self.designer_ui.actionSave_Layout.triggered.connect(lambda: self.save_picker_data())
    self.designer_ui.actionOpen_Layout.triggered.connect(lambda: self.load_picker_data())
    # Window
    self.designer_ui.actionLower_Opacity.triggered.connect(lambda: self.toggle_opacity())
    self.designer_ui.actionToggle_Toolbar.triggered.connect(
                     lambda: self.designer_ui.toolLayout.setVisible(not self.designer_ui.toolLayout.isVisible()))
    self.designer_ui.actionLoad_Background.triggered.connect(lambda: self.load_background())
    # Align
    self.designer_ui.actionLeft_Edges.triggered.connect(lambda: self.align_buttons(edge="left"))
    self.designer_ui.actionTop_Edges.triggered.connect(lambda: self.align_buttons(edge="top"))
    # Distribute
    self.designer_ui.actionHorizontally.triggered.connect(lambda: self.distribute_buttons(direction="horizontally"))
    self.designer_ui.actionVertically.triggered.connect(lambda: self.distribute_buttons(direction="vertically"))
    # Button
    self.designer_ui.actionAdd.triggered.connect(lambda: self.make_button(multi_mode=False))
    self.designer_ui.actionAdd_Group.triggered.connect(lambda: self.make_button(multi_mode=True))
    self.designer_ui.actionChange_Color.triggered.connect(lambda: self.change_button_color())
    self.designer_ui.actionRemove.triggered.connect(lambda: self.remove_buttons())

  def find_namespaces(self):
    # find namespaces in current scene
    scene_namespaces = cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True)
    current_namespace = cmds.namespaceInfo(currentNamespace=True)
    i = 1
    for namespace in scene_namespaces:
      if namespace not in ["UI", "shared"]:
        # append it to the dropdown menu
        self.designer_ui.namespaceComboBox.insertItem(i, namespace + ":")
        if "Face" not in namespace:
          # dirty fix for not using the face namespace when the face rig is referenced in
          self.designer_ui.namespaceComboBox.setCurrentIndex(i)
        i += 1
    self.designer_ui.namespaceComboBox.setToolTip("Choose the namespace to use with this picker.\nWill automatically guess which one on startup.")
    
  def make_button(self, multi_mode=False):
    width = float(self.designer_ui.widthInput.value())
    height = float(self.designer_ui.heightInput.value())

    selection = cmds.ls(selection=True)

    if multi_mode:
      selected_button_names = []
      for button_name in self.current_scene().buttons:
        # for whatever reason, shift selecting doesn't correctly update the scene's selected items list. 
        # therefore, to find the items that we currently have selected, we need to see if they have the 
        # selection brush applied to them... Not a great system, but idunno..
        if self.current_scene().buttons[button_name].brush() == self.current_scene().selection_brush:
          selected_button_names.append(button_name)

      button = graphics_items.CustomRect(width, height, 
                                         selection_list=selection, 
                                         selection_type="group", 
                                         button_selection_list=selected_button_names,
                                         color=None,
                                         name="button_{0}".format(self.button_id))

      self.current_scene().addItem(button)
      self.current_scene().buttons["button_{0}".format(self.button_id)] = button
      self.button_id += 1
    else:
      if not self.designer_ui.actionUse_Screenspace.isChecked():
        x = 0
        y = 0
        i = 0
        sel = cmds.ls(selection=True, showNamespace=True)
        while i < len(sel):
          obj = sel[i]
          namespace = sel[i + 1] + ":"
          world_pos = cmds.xform(obj, q=1, t=1, ws=1)
          if world_pos[0] > -1 and world_pos[0] < 1:
            color = 1
          elif world_pos[0] > 1:
            color = 2
          elif world_pos[0] < 1:
            color = 0

          button = graphics_items.CustomRect(width, height, x, y, 
                                            selection_list=[obj.replace(namespace,"")], 
                                            color=color, 
                                            name="button_{0}".format(self.button_id))
          x += 35
          if x > 400:
            x = 0
            y += 35

          self.current_scene().addItem(button)
          self.current_scene().buttons["button_{0}".format(self.button_id)] = button
          self.button_id += 1
          i += 2
      else:
        self.make_buttons_using_screenspace()

  def look_for_charnode(self):
    for obj in cmds.ls(type="network"):
      if "_CharNode" in obj:
        self.charnode = obj
        break

    if self.charnode:
      om.MGlobal.displayInfo("Found CharNode {0}.".format(self.charnode))

      try:
        # look for the picker path attribute on the CharNode
        self.picker_path = cmds.getAttr("{0}.pickerPath".format(self.charnode), asString=True)
      except ValueError:
        # attribute hasn't been added yet
        cmds.addAttr(self.charnode, longName="pickerPath", dataType="string", usedAsFilename=True)

      if self.picker_path and os.path.isfile(self.picker_path):
        self.load_picker_data(self.picker_path)

  # Button Functions
  def remove_buttons(self):
    for button in self.current_scene().selectedItems():
      self.current_scene().removeItem(button)

  def scale_buttons(self):
    width = float(self.designer_ui.widthInput.value())
    height = float(self.designer_ui.heightInput.value())

    for button in self.current_scene().selectedItems():
      button.setRect(0, 0, width, height)

  def align_buttons(self, edge="left"):
    if edge == "left":
      selected_items = self.current_scene().selectedItems()
      if len(selected_items):
        edge = selected_items[-1].scenePos().x()
        for i in range(0, len(selected_items) - 1):
          selected_items[i].setX(edge)

    elif edge == "top":
      selected_items = self.current_scene().selectedItems()
      if len(selected_items):
        edge = selected_items[-1].scenePos().y()
        for i in range(0, len(selected_items) - 1):
          selected_items[i].setY(edge)

  def distribute_buttons(self, direction="horizontally"):
    selected_items = self.current_scene().selectedItems()

    if direction == "horizontally":
      if len(selected_items) > 2:
        start_x = selected_items[0].scenePos().x()
        end_x = selected_items[-1].scenePos().x()
        num_divisions = len(selected_items) - 1
        spacing_length = (end_x - start_x) / float(num_divisions)
        for i in range(1, len(selected_items) - 1):
          selected_items[i].setX(start_x + (spacing_length * i))

    elif direction == "vertically":
      if len(selected_items) > 2:
        start_y = selected_items[0].scenePos().y()
        end_y = selected_items[-1].scenePos().y()
        num_divisions = len(selected_items) - 1
        spacing_length = (end_y - start_y) / float(num_divisions)
        for i in range(1, len(selected_items) - 1):
          selected_items[i].setY(start_y + (spacing_length * i))

  def toggle_lock(self):
    # moving into locked position
    if not self.locked:
      for button in self.current_scene().items():
        button.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.designer_ui.lockButton.setText("Unlock")
        self.locked = True
        self.designer_ui.menuAlign.setEnabled(0)
        self.designer_ui.menuDistribute.setEnabled(0)
        self.designer_ui.resizeButton.setEnabled(0)
        self.designer_ui.toolLayout.setVisible(0)
        self.designer_ui.actionToggle_Toolbar.setChecked(0)
    # moving into unlocked position
    else:
      for button in self.current_scene().items():
        button.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.designer_ui.lockButton.setText("Lock")
        self.locked = False
        self.designer_ui.menuAlign.setEnabled(1)
        self.designer_ui.menuDistribute.setEnabled(1)
        self.designer_ui.resizeButton.setEnabled(1)
        self.designer_ui.toolLayout.setVisible(1)
        self.designer_ui.actionToggle_Toolbar.setChecked(1)

  def change_button_color(self):
    
    # use a QColorDialog to choose the color to change the selected buttons to
    chosen_color = self.color_dialog.getColor()
    for button in self.current_scene().selectedItems():
      button.setBrush(chosen_color)
      button.color = chosen_color

  def toggle_opacity(self):
    if self.designer_ui.actionLower_Opacity.isChecked():
      self.setWindowOpacity(.75)
    else:
      self.setWindowOpacity(1)

  def current_scene(self):
    current_tab = self.designer_ui.tabWidget.currentIndex()
    current_scene = self.tab_scenes[current_tab]
    return current_scene

  def current_view(self):
    current_tab = self.designer_ui.tabWidget.currentIndex()
    current_view = self.tab_views[current_tab]
    return current_view

  def save_picker_data(self):
    picker_io.save_picker(self.current_scene().items(), background_path=self.current_scene().pixmap_path)

  def load_picker_data(self, fullpath=None):
    picker_data, picker_path = picker_io.load_picker(self, fullpath)
    pixmap_path = picker_data["background"]

    # pixmap
    # a QGraphicsScene holds the data for what's displayed in a QGraphicsView
    scene = graphics_items.CustomGraphicsScene(parent=None, namespace=self.designer_ui.namespaceComboBox, pixmap_path=pixmap_path)
    view = graphics_items.CustomGraphicsView(parent=None, designer_ui=self.designer_ui, scene=scene)
    view.setToolTip("Ben's Hot Tips:\n+ Right-Click me for a sweet menu\n+ Hold Spacebar to pan\n+ Mouse-Wheel zooms\n+ Ctrl-Left Click to select/deselect.\n+ Try click & drag!")
    # add the view to the layout from our designer file
    self.designer_ui.tabWidget.addTab(view, os.path.basename(picker_path).replace(".pkr",""))
    self.tab_scenes.append(scene)
    self.tab_views.append(view)

    self.designer_ui.tabWidget.setCurrentIndex(len(self.tab_views) - 1)

    if self.charnode:
      cmds.setAttr("{0}.pickerPath".format(self.charnode), picker_path, type="string")
      om.MGlobal.displayInfo("Mapped loaded picker path to rig.")

    if not picker_data:
      return

    self.current_scene().pixmap_path = pixmap_path

    # should clear our picker first
    for index in picker_data["buttons"]:
      button = picker_data["buttons"][index]
      button_position = button["position"]
      button_color = QtGui.QColor()
      button_color.setRgbF(*button["color"])
      selection_list = button["selection"]
      button_selection_list = button["button_selection_list"]
      selection_type = button["selection_type"]
      button_rect = button["rect"]

      button = graphics_items.CustomRect(width=button_rect[0], 
                                      height=button_rect[1], 
                                      x=button_position[0], 
                                      y=button_position[1], 
                                      selection_list=selection_list, 
                                      selection_type=selection_type,
                                      button_selection_list=button_selection_list,
                                      color=button_color,
                                      name=index)
      
      self.current_scene().buttons[index] = button
      self.current_scene().addItem(button)
      self.button_id += 1

    self.locked = False
    self.toggle_lock()
    om.MGlobal.displayInfo("Loaded character picker from:\n# {0}".format(picker_path))

  def load_background(self):
    # have the user navigate to an image file
    imagepath = cmds.fileDialog2(okCaption="Load",
                                fileMode=1,
                                caption="Load Image File",
                                startingDirectory=os.path.join(os.path.dirname(__file__), "..", "background_images"))
    if imagepath:
      self.current_scene().pixmap_path = imagepath[0]

  def make_buttons_using_screenspace(self):
    width = float(self.designer_ui.widthInput.value())
    height = float(self.designer_ui.heightInput.value())
    active_view = omui.M3dView.active3dView()
    # get screen resolution
    destop_widget = QtWidgets.QDesktopWidget()
    screen_width = destop_widget.width()
    screen_height = destop_widget.height()

    viewport_x = om.MScriptUtil().asIntPtr()
    viewport_y = om.MScriptUtil().asIntPtr()
    active_view.getScreenPosition(viewport_x, viewport_y)
    viewport_x = om.MScriptUtil(viewport_x).asInt()
    viewport_y = om.MScriptUtil(viewport_y).asInt()

    center = self.current_view().sceneRect().center()

    i = 0
    sel = cmds.ls(selection=True, showNamespace=True)
    while i < len(sel):
      obj = sel[i]
      namespace = sel[i + 1] + ":"
      # get the world position of each selected object
      # from http://around-the-corner.typepad.com/adn/2012/08/convert-maya-world-coordinates-to-screen-coordinates.html
      world_pos = cmds.xform(obj, q=1, t=1, ws=1)

      if world_pos[0] > -1 and world_pos[0] < 1:
        color = 1
      elif world_pos[0] > 1:
        color = 2
      elif world_pos[0] < 1:
        color = 0

      # get the active 3d view
      # make an MPoint out of that world position
      world_point = om.MPoint(world_pos[0], world_pos[1], world_pos[2])

      # the worldToView method needs short objects, so we'll use an MScriptUtil class to give us one
      screen_pos_x = om.MScriptUtil().asShortPtr()
      screen_pos_y = om.MScriptUtil().asShortPtr()
      # use the active 3d view to convert the world position to port space
      active_view.worldToView(world_point, screen_pos_x, screen_pos_y)
      # get the data from the shorts and add to them the lefthand corner of the viewport.
      # this should put that pixel into screen space
      screen_pos_x = om.MScriptUtil(screen_pos_x).asShort() + viewport_x
      screen_pos_y = om.MScriptUtil(screen_pos_y).asShort() + viewport_y

      # make a QPoint from the screen coordinates
      screen_point = QtCore.QPoint(screen_pos_x, screen_pos_y)
      widget_point = self.current_view().mapFromGlobal(screen_point)
      # now it's coming in upsidte down! So we just have to mirror it across the center axis of our view
      # that'd be the origin minus half it's height
      # but it's a movement, so we subtract that vector from the original location

      button = graphics_items.CustomRect(width=width, 
                                        height=height, 
                                        x=widget_point.x(), 
                                        y= widget_point.y() - ((widget_point.y() - center.y()) * 2.0), 
                                        selection_list=[obj.replace(namespace, "")], 
                                        color=color,
                                        name="button_{0}".format(self.button_id))

      self.current_scene().addItem(button)
      self.current_scene().buttons["button_{0}".format(self.button_id)] = button
      self.button_id += 1
      i += 2

  # Events
  def keyPressEvent(self, event):
    # space to pan
    if event.key() == 32:
      self.current_view().setDragMode(QtWidgets.QGraphicsView.DragMode(1))
    # switch manipulator contexts within widget
    # w
    elif event.key() == 87:
      mel.eval("TranslateToolWithSnapMarkingMenu;")
      mel.eval("dR_TranslateToolMarkingMenuPopDown;")
    # e
    elif event.key() == 69:
      mel.eval("RotateToolWithSnapMarkingMenu;")
      mel.eval("dR_RotateToolMarkingMenuPopDown;")
    # r
    elif event.key() == 82:
      mel.eval("ScaleToolWithSnapMarkingMenu;")
      mel.eval("dR_ScaleToolMarkingMenuPopDown;")
    # q
    elif event.key() == 81:
      mel.eval("SelectToolOptionsMarkingMenu;")
      mel.eval("dR_SelectToolMarkingMenuPopDown;")
    # s
    elif event.key() == 83:
      current_anim_layer = cmds.treeView("AnimLayerTabanimLayerEditor", query=True, selectItem=True)
      if current_anim_layer:
        # make sure it doesn't key attributes on the shape node below so that the new Arnold shape 
        # attributes on Nurbs don't get keyed.
        cmds.setKeyframe(cmds.ls(selection=True), shape=False, animLayer=current_anim_layer[0])
      else:
        cmds.setKeyframe(cmds.ls(selection=True), shape=False)
    # undo (ctrl + z)
    elif event.key() == 90 and QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
      cmds.undo()

  def keyReleaseEvent(self, event):
    # space to pan
    if event.key() == 32:
      self.current_view().setDragMode(QtWidgets.QGraphicsView.DragMode(2))