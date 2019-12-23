"""Base classes for qt widgets"""

import os
import ast

from bmaya.lib.Qt import QtWidgets, QtGui, QtCore, QtCompat

import maya.cmds as cmds
import maya.OpenMayaUI as omui


class SimpleWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None, designerFile=None, title='Simple Widget'):
        super(SimpleWindow, self).__init__(parent=parent)

        assert isinstance(title, basestring)
        self.title = title

        try:
            cmds.deleteUI(self.title)
        except RuntimeError:
            pass

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(self.title)

        if designerFile and isinstance(designerFile, basestring):
            if os.path.exists(designerFile):
                self.widget = QtCompat.load_ui(designerFile)
                self.widget.setParent(self)
            else:
                raise RuntimeError('Given Qt Designer file not in folder.')
        else:
            self.widget = QtWidgets.QWidget()
            self.mainLayout = QtWidgets.QVBoxLayout()
            self.widget.setLayout(self.mainLayout)
            self.setCentralWidget(self.widget)


class SimpleWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, designerFile=None, title='Simple Widget'):
        super(SimpleWidget, self).__init__(parent=parent)

        assert isinstance(title, basestring)
        self.title = title

        try:
            cmds.deleteUI(self.title)
        except RuntimeError:
            pass

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.setWindowTitle(self.title)

        if designerFile and isinstance(designerFile, basestring):
            if os.path.exists(designerFile):
                self.widget = QtCompat.load_ui(designerFile)
                self.widget.setParent(self)
            else:
                raise RuntimeError('Given Qt Designer file not in folder.')


class Table(QtWidgets.QTableWidget):
    def __init__(self):
        super(Table, self).__init__()

        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)

        self.cellObjects = {}
        self.cellData = {}

    def translateToType(self, item):
        try:
            translated = ast.literal_eval(str(item))
            return translated
        except ValueError:
            # item type is a string and didn't like getting translated
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

        self.setFlags(self.flags() | QtCore.Qt.ItemIsEditable)
        self.setSizeHint(0, QtCore.QSize(50,20))
        self.setFirstColumnSpanned(True)

        self.setText(0, 'Tree Item')

    @property
    def parents(self):
        _parents = []

        item = self

        while item.parent():
            _parents.append(item.parent())
        
        return _parents

    @property
    def children(self):
        _children = []
        # get child count
        childCount = self.childCount()

        for i in range(childCount):
            _children.append(self.child(i))

        return _children

    @property
    def name(self):
        return str(self.text(0))
                

class DockableWidget(SimpleWidget):
    def __init__(self, parent=None, designerFile=None, title='RigBuilder'):
        super(DockableWidget, self).__init__(parent, designerFile, title)


    def dock(self, width=385, height=735):

        dockControl = cmds.workspaceControl(
            self.title,
            tabToControl=["AttributeEditor", -1],
            initialWidth=width,
            minimumWidth=True,
            initialHeight=height,
            widthProperty="preferred",
            label=self.title)

        dockPtr = omui.MQtUtil.findControl(dockControl)
        dockWidget = QtCompat.wrapInstance(long(dockPtr), QtWidgets.QWidget)
        dockWidget.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        dockWidget.layout().addWidget(self.widget)

        cmds.evalDeferred(
            lambda *args: cmds.workspaceControl(
                dockControl,
                edit=True,
                restore=True
            )
        )


