"""Base classes"""
import os
import ast

from lib.Qt import QtWidgets, QtGui, QtCore, QtCompat
from . import wrappers

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


class DockableWidget(QtWidgets.QWidget):
    label = 'Rig Builder'

    def __init__(self, parent=None):
        super(DockableWidget, self).__init__(parent)

        self.setWindowTitle(self.label)

        designPath = os.path.join(os.path.dirname(__file__), 'widget.ui')
        self.widget = QtCompat.load_ui(designPath)
        self.widget.setParent(self)

    @classmethod
    def show(cls):
        wrappers.Dock(cls, show=True)


