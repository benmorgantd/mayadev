# our standard imports when using Qt.py
import maya.cmds as cmds
import maya.OpenMayaUI as omui
import os
from bmaya.lib.Qt import QtWidgets, QtGui, QtCore, QtCompat
import PoseStorage.modules.bm_poseStorage as bm_poseStorage
#reload(bm_poseStorage)

try:
  from shiboken import wrapInstance
except:
  from shiboken2 import wrapInstance

####################
# GLOBAL VARIABLES #
####################

SCRIPT_LOC = os.path.split(__file__)[0]
WINDOW_OBJECT = "PoseStorageUI"
WINDOW_TITLE = "Pose Storage UI"
MAIN_WINDOW_FILE = os.path.join(SCRIPT_LOC, "bm_pose_storage_ui_design.ui")

################
# Button Class #
################

class Button(object):
  def __init__(self, file_full_path):
    """Button objects are used for each Pose button that is added to our UI.

    :param file_full_path: The full path to the button's corresponding .pose file.
    """
    self.file_full_path = file_full_path
    btn_txt = os.path.basename(self.file_full_path)
    btn_txt = btn_txt.replace(".pose", "")
    self.btn = QtWidgets.QPushButton(btn_txt)
    self.btn.setStyleSheet("font-size: 9pt;font-weight: bold;color:#000000;background-color:#6b6b6b")
    self.btn.setToolTip("Click to snap to pose. \nCTRL+Click to blend in\nSHIFT+Click to blend out\nALT+Click to select the controls in the pose")

  def print_full_path(self):
    print self.file_full_path


################
# Window Class #
################

class PoseStorageUI(QtWidgets.QMainWindow):
  def __init__(self, parent=None):
    super(PoseStorageUI, self).__init__(parent)

    # Load the UI file
    self.MainWindowUI = QtCompat.load_ui(MAIN_WINDOW_FILE)
    # Sets our UI file widget to be the central widget of our QMainWindow object
    self.setCentralWidget(self.MainWindowUI)

    # create a pose master object for handling file io
    self.pose_master = bm_poseStorage.PoseMaster(root_dir=SCRIPT_LOC)

    # Set window flags
    self.setWindowFlags(QtCore.Qt.WindowType.Tool)
    self.setObjectName(WINDOW_OBJECT)
    self.setWindowTitle(WINDOW_TITLE)
    self.setWindowFlags(QtCore.Qt.Window)
    self.resize(335, 350)
    self.scroll_area_widgets = []
    self.MainWindowUI.destroyed.connect(lambda: self.on_exit_code())
    # Make connections for the contents of our window
    self.root_dir = os.path.join(SCRIPT_LOC, "..", "Poses")
    self.last_dir = self.root_dir

    self.make_connections()

    self.find_namespaces()

    self.refresh_ui()

  def make_connections(self):
    # some example connections using the buttons we made and named in QtDesigner.
    self.MainWindowUI.actionAdd_Pose.triggered.connect(lambda: self.add_pose())
    self.MainWindowUI.actionSet_Root_Directory.triggered.connect(lambda: self.set_root_dir())
    
    self.MainWindowUI.actionRefresh.triggered.connect(lambda: self.refresh_ui(clear_first=True))
    self.MainWindowUI.actionFlip_Face_Pose.triggered.connect(lambda: self.flip_pose(face=True))


  def find_namespaces(self):
    # find namespaces in current scene
    scene_namespaces = cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True)
    current_namespace = cmds.namespaceInfo(currentNamespace=True)
    i = 0

    self.MainWindowUI.namespace_txt.clear()
    self.MainWindowUI.namespace_txt.insertItem(i, ":")
    self.MainWindowUI.namespace_txt.setCurrentIndex(i)

    for namespace in scene_namespaces:
      if namespace not in ["UI", "shared"]:
        # append it to the dropdown menu
        self.MainWindowUI.namespace_txt.insertItem(i, namespace + ":")
        self.MainWindowUI.namespace_txt.setCurrentIndex(i)
      i += 1
    self.MainWindowUI.namespace_txt.setToolTip("Choose the namespace to use with this picker.\nWill automatically guess which one on startup.")

  def refresh_ui(self, clear_first=False):

    if clear_first:
      self.clear_ui()

    self.find_namespaces()

    def _read_pose_file(pose_obj):
      def do_it():
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        self.pose_master.read_pose(pose_name=pose_obj.file_full_path, 
                                   multiplier=self.MainWindowUI.multiplier_val.value(),
                                   namespace=self.get_namespace(),
                                   ctrl_pressed=modifiers == QtCore.Qt.ControlModifier,
                                   shift_pressed=modifiers == QtCore.Qt.ShiftModifier,
                                   alt_pressed=modifiers == QtCore.Qt.AltModifier)
      return do_it

    pose_folder_and_files = bm_poseStorage.list_poses(root_dir=self.root_dir)
    pose_objects = []

    for pose_folder in pose_folder_and_files:

      self.pose_master.load_poses(pose_folder)
      pose_folder_label = QtWidgets.QLabel(os.path.basename(pose_folder))
      pose_folder_label.setAlignment(QtCore.Qt.AlignCenter)
      pose_folder_label.setMaximumHeight(25)
      pose_folder_label.setStyleSheet("font-size: 11pt;font-weight: bold;color:#d3d3d3")
      self.MainWindowUI.poses_verticalLayout.addWidget(pose_folder_label)
      self.scroll_area_widgets.append(pose_folder_label)

      for pose_file in pose_folder_and_files[pose_folder]:
        pose_btn_object = Button(pose_file)
        pose_objects.append(pose_btn_object)
        if "LF" in pose_file or "lf" in pose_file:
          pose_btn_object.btn.setStyleSheet("font-size: 9pt; font-weight: bold; color:#000000; background-color:#6e78ea")
        elif "RT" in pose_file or "rt" in pose_file:
          pose_btn_object.btn.setStyleSheet("font-size: 9pt; font-weight: bold; color:#000000; background-color:#ea6e6e")
        else:
          pose_btn_object.btn.setStyleSheet("font-size: 9pt; font-weight: bold; color:#000000; background-color:#eaea6e")


        self.MainWindowUI.poses_verticalLayout.addWidget(pose_btn_object.btn)
        self.scroll_area_widgets.append(pose_btn_object.btn)
        pose_btn_object.btn.clicked.connect(_read_pose_file(pose_btn_object))


  def clear_ui(self):
    for widget in self.scroll_area_widgets:
      widget.hide()

  def get_namespace(self):
    namespace_txt = self.MainWindowUI.namespace_txt.currentText()
    if not namespace_txt:
      return ""
    else:
      return namespace_txt

  def add_pose(self):
    try:
      full_path = \
        cmds.fileDialog2(dir=self.last_dir, okCaption="Save", fileMode=0, caption="Save Pose File",
                 fileFilter="Pose Files (*.pose)")[0]
    except TypeError:
      return

    self.last_dir = full_path

    if len(cmds.ls(sl=1)) == 0:
      raise ValueError("Select every control you want to be shared to the pose file before adding pose.")

    self.pose_master.write_pose(pose_name=full_path, is_full_path=True)
    self.clear_ui()
    self.refresh_ui()

  def set_root_dir(self):
    try:
      self.root_dir = \
        cmds.fileDialog2(dir=self.root_dir, okCaption="Set Folder", fileMode=3, caption="Set Root Directory")[0]
    except TypeError:
      return

    self.clear_ui()
    self.refresh_ui()

  def flip_pose(self, face=True, search_replace=["LF_", "RT_"]):
    sel = cmds.ls(sl=1)
    if "RT_" in sel[0]:
      search_replace = ["RT_", "LF_"]

    cmds.select(clear=True)

    if face:
      attribute_mirrors = [1, 1, -1, -1, -1, 1]

      for ctrl in sel:
        if search_replace:
          mirror_control = ctrl.replace(search_replace[0], search_replace[1])
        else:
          mirror_control = ctrl
          if "jaw" in ctrl:
            attribute_mirrors = [-1, 1, 1, 1, -1, -1]
            
        cmds.select(mirror_control, add=True)
        k = 0

        for i in ["t", "r"]:
          for j in ["x", "y", "z"]:
            print "{0}.{1}{2}".format(mirror_control, i, j)
            cmds.setAttr("{0}.{1}{2}".format(mirror_control, i, j), (cmds.getAttr("{0}.{1}{2}".format(ctrl, i, j), time=cmds.currentTime(q=1))) * attribute_mirrors[k])
            k += 1
      


    
  @staticmethod
  def on_exit_code():
    # run this when the script is closed
    print("UI successfully closed\n")


#######################
# Maya Side Functions #
#######################

def _maya_delete_ui():
  """Delete existing UI in Maya"""
  if cmds.window(WINDOW_OBJECT, q=True, exists=True):
    cmds.deleteUI(WINDOW_OBJECT)  # Delete window


def _show_ui():
  # Launches the UI and ensures we don't get multiple instances of it.
  _maya_delete_ui()
  gui = PoseStorageUI(parent=wrapInstance(long(omui.MQtUtil.mainWindow()), QtWidgets.QWidget))
  gui.show()
