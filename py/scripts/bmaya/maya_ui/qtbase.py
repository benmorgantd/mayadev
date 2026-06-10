"""Base classes for qt widgets compatible with Python 3 and PySide6"""

import os
import ast

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from bmaya.core import log

# PySide6 fixes: QtCompat does not exist. Use QtUiTools for loading .ui files.
from PySide6 import QtWidgets, QtCore, QtUiTools
import shiboken6


def getMayaMainWindow():
    # Fix: shiboken6 method is case-sensitive (wrapInstance)
    return shiboken6.wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


def loadUiFile(designerFile, parent=None):
    """Helper replacement for the old QtCompat.load_ui"""
    loader = QtUiTools.QUiLoader()
    ui_file = QtCore.QFile(designerFile)
    if ui_file.open(QtCore.QFile.OpenModeFlag.ReadOnly):
        widget = loader.load(ui_file, parent)
        ui_file.close()
        return widget
    else:
        raise RuntimeError(f"Failed to open UI file: {designerFile}")


class SimpleWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None, designerFile=None, title="Simple Widget"):
        super(SimpleWindow, self).__init__(parent=parent)

        assert isinstance(title, str)
        self.title = title

        try:
            cmds.deleteUI(self.title)
        except RuntimeError:
            pass

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(self.title)

        if designerFile and isinstance(designerFile, str):
            if os.path.exists(designerFile):
                # Fix: Use native QUiLoader helper
                self.widget = loadUiFile(designerFile, self)
                self.setCentralWidget(self.widget)
            else:
                raise RuntimeError("Given Qt Designer file not in folder.")
        else:
            self.widget = QtWidgets.QWidget()
            self.mainLayout = QtWidgets.QVBoxLayout()
            self.widget.setLayout(self.mainLayout)
            self.setCentralWidget(self.widget)


class SimpleWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, designerFile=None, title="Simple Widget"):
        super(SimpleWidget, self).__init__(parent=parent)

        assert isinstance(title, str)
        self.title = title

        try:
            cmds.deleteUI(self.title)
        except RuntimeError:
            pass

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(self.title)

        if designerFile and isinstance(designerFile, str):
            if os.path.exists(designerFile):
                # Fix: Use native QUiLoader helper and place it inside a layout 
                # to prevent geometry/rendering dead zones in Maya custom panels.
                self.widget = loadUiFile(designerFile, self)
                layout = QtWidgets.QVBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(self.widget)
            else:
                raise RuntimeError("Given Qt Designer file not in folder.")


class Table(QtWidgets.QTableWidget):
    def __init__(self):
        super(Table, self).__init__()

        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.cellObjects = {}
        self.cellData = {}

    def translateToType(self, item):
        try:
            translated = ast.literal_eval(str(item))
            return translated
        except (ValueError, SyntaxError):
            return item

    def toJson(self, dictionary):
        jsonData = {}
        for key, value in dictionary.items():
            jsonData[key] = self.translateToType(value)
        return jsonData


class List(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super(List, self).__init__(parent)

        self.cellData = {}
        self.moduleLayouts = []

        self.setSpacing(1)
        self.setAlternatingRowColors(True)
        self.setMaximumHeight(200)

        self.setDragEnabled(False)
        self.setAcceptDrops(False)


class Tree(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super(Tree, self).__init__(parent)

        self.setAlternatingRowColors(True)
        self.setMaximumHeight(200)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)

        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)

    @property
    def items(self):
        iterator = QtWidgets.QTreeWidgetItemIterator(self)
        _items = []
        while iterator.value():
            _items.append(iterator.value())
            iterator += 1
        return _items

    @property
    def topLevelItems(self):
        _topLevelItems = []
        for i in self.items:
            if not i.parent():
                _topLevelItems.append(i)
        return _topLevelItems


class TreeItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, parent=None):
        super(TreeItem, self).__init__(parent)

        self.setFlags(self.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        self.setSizeHint(0, QtCore.QSize(50, 20))
        self.setFirstColumnSpanned(True)

        self.setText(0, "Tree Item")

    @property
    def parents(self):
        _parents = []
        item = self
        while item.parent():
            _parents.append(item.parent())
            item = item.parent() 
        return _parents

    @property
    def children(self):
        _children = []
        childCount = self.childCount()
        for i in range(childCount):
            _children.append(self.child(i))
        return _children

    @property
    def name(self):
        return str(self.text(0))


class DockableWidget(SimpleWidget):
    def __init__(self, parent=None, designerFile=None, title="rigManager"):
        super(DockableWidget, self).__init__(parent, designerFile, title)

    def dock(self, width=385, height=735):
        if cmds.workspaceControl(self.title, q=True, exists=True):
            cmds.workspaceControl(self.title, e=True, close=True)
            cmds.deleteUI(self.title, control=True)

        dockControl = cmds.workspaceControl(
            self.title,
            tabToControl=["AttributeEditor", -1],
            initialWidth=width,
            minimumWidth=True,
            initialHeight=height,
            widthProperty="preferred",
            label=self.title,
        )

        dockPtr = omui.MQtUtil.findControl(dockControl)
        dockWidget = shiboken6.wrapInstance(int(dockPtr), QtWidgets.QWidget)
        
        dockWidget.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Fix: Ensure safe extraction of loaded ui layout elements
        target_widget = self.widget if hasattr(self, 'widget') else self

        if dockWidget.layout():
            dockWidget.layout().addWidget(target_widget)
        else:
            layout = QtWidgets.QVBoxLayout(dockWidget)
            layout.addWidget(target_widget)

        cmds.evalDeferred(
            lambda *args: cmds.workspaceControl(dockControl, edit=True, restore=True)
        )


class Dialog(QtWidgets.QDialog):
    def __init__(self, parent=None, windowTitle="Dialog"):
        # Ensure we always pass the Maya main window as parent if none is provided
        # This keeps the dialog owned by Maya so it doesn't drop behind the main UI
        parent = parent or getMayaMainWindow()
        super(Dialog, self).__init__(parent)

        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        
        # Changed to Vertical Layout to cleanly support a message prompt on top 
        # and action buttons on the bottom.
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle(windowTitle)


class ConfirmDialog(Dialog):
    """Modal confirm dialog that pauses execution and returns a boolean result.
    
    Call "exec()" to show this modally and to get the result.
    """
    
    def __init__(self, message, parent=None, windowTitle="Confirm Dialog"):
        super(ConfirmDialog, self).__init__(parent=parent, windowTitle=windowTitle)

        # Message Label
        self.messageLabel = QtWidgets.QLabel(message)
        # Allows text wrapping if the message string is long
        self.messageLabel.setWordWrap(True) 
        self.messageLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.mainLayout.addWidget(self.messageLabel)

        # Horizontal layout button row
        self.btnLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.addLayout(self.btnLayout)

        self._yesBtn = QtWidgets.QPushButton("Yes")
        self._noBtn = QtWidgets.QPushButton("No")

        self.btnLayout.addWidget(self._yesBtn)
        self.btnLayout.addWidget(self._noBtn)

        self.setMinimumWidth(250)
        self.setMinimumHeight(80)

        # Connect slots
        self._yesBtn.clicked.connect(self.accept)
        self._noBtn.clicked.connect(self.reject)
    

def show_confirm_dialog(message="Are you sure?", windowTitle="Confirm"):
    '''Show a confirm dialog and return the user's choice.'''
    
    dialog = ConfirmDialog(message=message, windowTitle=windowTitle)
    return dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted


class ProgressWindow(SimpleWindow):
    windowSize = QtCore.QSize(350, 75)

    def __init__(self, parent=None, designerFile=None, title="Simple Widget"):
        super(ProgressWindow, self).__init__(
            parent=parent, designerFile=designerFile, title=title
        )

        self.progress = 0
        self.minProgress = 0
        self.maxProgress = 100

        self.statusTextWidget = QtWidgets.QLabel("Doing Something...")
        self.progressBarWidget = QtWidgets.QProgressBar()

        self.mainLayout.addWidget(self.statusTextWidget)
        self.mainLayout.addWidget(self.progressBarWidget)

        self.setFixedSize(self.windowSize)
        
        self.setWindowFlags(
            QtCore.Qt.WindowType.Drawer | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )

    def increment(self, value):
        self.progressBarWidget.setValue(self.progressBarWidget.value() + int(value))

    def setStatus(self, text):
        self.statusTextWidget.setText(text.replace("...", "") + "...")
        log.info(text)