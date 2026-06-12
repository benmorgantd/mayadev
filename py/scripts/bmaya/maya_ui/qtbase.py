"""Base classes for qt widgets compatible with Python 3 and PySide6"""

import os
import ast

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from bmaya.core import log, progressmanager

# PySide6 Fix: QtCompat removed. Use QtUiTools for loading designer layouts.
from PySide6 import QtWidgets, QtCore, QtUiTools, QtGui
import shiboken6


def get_maya_main_window():
    # Python 3: long() removed, use int()
    return shiboken6.wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


def loadUiFile(designerFile, parent=None):
    """Helper replacement for the old QtCompat.load_ui layout stream"""
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
                self.widget = loadUiFile(designerFile, self)
                layout = QtWidgets.QVBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(self.widget)
                self.setLayout(layout)
            else:
                raise RuntimeError("Given Qt Designer file not in folder.")


class Table(QtWidgets.QTableWidget):
    def __init__(self):
        super(Table, self).__init__()

        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        
        # PySide6 Scoped Enums
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.cellObjects = {}
        self.cellData = {}

    def translateToType(self, item):
        try:
            return ast.literal_eval(str(item))
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

        target_widget = self.widget if hasattr(self, 'widget') else self

        if dockWidget.layout():
            dockWidget.layout().addWidget(target_widget)
        else:
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(target_widget)
            dockWidget.setLayout(layout)

        cmds.evalDeferred(
            lambda *args: cmds.workspaceControl(dockControl, edit=True, restore=True)
        )


class Dialog(QtWidgets.QDialog):
    def __init__(self, parent=None, windowTitle="Dialog"):
        parent = parent or get_maya_main_window()
        super(Dialog, self).__init__(parent)

        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.setWindowTitle(windowTitle)


class ConfirmDialog(Dialog):
    """Modal confirm dialog that pauses execution and returns a boolean result."""
    def __init__(self, message, parent=None, windowTitle="Confirm Dialog"):
        super(ConfirmDialog, self).__init__(parent=parent, windowTitle=windowTitle)

        self.messageLabel = QtWidgets.QLabel(message)
        self.messageLabel.setWordWrap(True) 
        self.messageLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.mainLayout.addWidget(self.messageLabel)

        self.btnLayout = QtWidgets.QHBoxLayout()
        self.btnLayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.mainLayout.addLayout(self.btnLayout)

        self._yesBtn = QtWidgets.QPushButton("Yes")
        self._noBtn = QtWidgets.QPushButton("No")
        self._yesBtn.setFixedWidth(80)
        self._noBtn.setFixedWidth(80)

        self.btnLayout.addWidget(self._yesBtn)
        self.btnLayout.addWidget(self._noBtn)

        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        self._yesBtn.clicked.connect(self.accept)
        self._noBtn.clicked.connect(self.reject)


class ProgressWindow(SimpleWindow):
    windowSize = QtCore.QSize(350, 75)

    def __init__(self, parent=None, designerFile=None, title="Progress Tracker"):
        super(ProgressWindow, self).__init__(
            parent=parent, designerFile=designerFile, title=title
        )

        # UI Initialization
        self.statusTextWidget = QtWidgets.QLabel("Ready...")
        self.progressBarWidget = QtWidgets.QProgressBar()
        self.progressBarWidget.setRange(0, 100)

        self.mainLayout.addWidget(self.statusTextWidget)
        self.mainLayout.addWidget(self.progressBarWidget)

        self.setFixedSize(self.windowSize)
        self.setWindowFlags(
            QtCore.Qt.WindowType.Drawer | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )

        # Connect to Singleton
        self.manager = progressmanager.ProgressManager()
        self.manager.register_callback(self.refresh_ui)

        # Polling fallback timer (just in case callbacks drop during aggressive loops)
        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_ui)
        self.poll_timer.start(100)  # Check every 100ms

        # Initial Sync
        self.refresh_ui()

    def refresh_ui(self) -> None:
        """Syncs the Qt widgets to the current state of the pure python singleton."""
        if not self.manager.active:
            if self.isVisible():
                self.hide()  # Or self.hide() depending on reuse preference
            return

        if not self.isVisible():
            self.show()

        # Update Progress Bar Range and Value
        if self.progressBarWidget.maximum() != self.manager.max_value:
            self.progressBarWidget.setMaximum(self.manager.max_value)
        
        self.progressBarWidget.setValue(self.manager.current_value)

        # Update Status Text
        clean_text = self.manager.status_text.replace("...", "") + "..."
        if self.statusTextWidget.text() != clean_text:
            self.statusTextWidget.setText(clean_text)
            log.info(self.manager.status_text)
            
        # Force Maya UI to draw updates during tight execution loops
        QtWidgets.QApplication.processEvents()


class PythonSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    """Provides fundamental Python syntax highlighting for the embedded script editor."""

    def __init__(self, parent: QtGui.QTextDocument | None = None) -> None:
        super().__init__(parent)
        self.rules = []

        # Keyword styling
        keyword_format = QtGui.QTextCharFormat()
        keyword_format.setForeground(QtGui.QColor("#CC7832"))
        keyword_format.setFontWeight(QtGui.QFont.Weight.Bold)
        keywords = [
            "and", "as", "assert", "async", "await", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda", "None",
            "nonlocal", "not", "or", "pass", "raise", "return", "True", "try",
            "while", "with", "yield"
        ]
        for word in keywords:
            pattern = QtCore.QRegularExpression(rf"\b{word}\b")
            self.rules.append((pattern, keyword_format))

        # Builtins / Functions styling
        builtin_format = QtGui.QTextCharFormat()
        builtin_format.setForeground(QtGui.QColor("#8888C6"))
        pattern = QtCore.QRegularExpression(r"\b(print|exec|eval|len|range|str|int|dict|list|set|tuple)\b")
        self.rules.append((pattern, builtin_format))

        # String styling
        string_format = QtGui.QTextCharFormat()
        string_format.setForeground(QtGui.QColor("#6A8759"))
        self.rules.append((QtCore.QRegularExpression(r'".*?"'), string_format))
        self.rules.append((QtCore.QRegularExpression(r"'.*?'"), string_format))

        # Comment styling
        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(QtGui.QColor("#808080"))
        comment_format.setFontItalic(True)
        self.rules.append((QtCore.QRegularExpression(r"#.*"), comment_format))

    def highlightBlock(self, text: str) -> None:
        """Applies formatting rules across the text block contextually."""
        for pattern, text_format in self.rules:
            expression = QtCore.QRegularExpression(pattern)
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), text_format)