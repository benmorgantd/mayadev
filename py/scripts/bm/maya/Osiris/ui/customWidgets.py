'''Custom widgets for rigBuilder'''

import ast

from lib.Qt import QtWidgets, QtGui, QtCore, QtCompat

from . import base
reload(base)


class ModuleList(base.List):
    def __init__(self, attributeContainer=None):
        super(ModuleList, self).__init__()

        self.attributeContainer = attributeContainer

    def setBuildList(self, listWidget):
        self.buildList = listWidget

    def mouseDoubleClickEvent(self, event):
        QtWidgets.QListWidget.mouseDoubleClickEvent(self, event)

        if self.buildList:
            currentRowIndex = self.currentRow()

            try:
                selectedModType = self.item(currentRowIndex).text()
            except AttributeError:
                # no row selected
                return

            currentRow = self.buildList.currentRow()

            newMod = BuildListItem(modType=selectedModType, attributeContainer=self.attributeContainer)
            self.buildList.addItem(newMod)


###########################


class BuildList(base.List):
    def __init__(self):
        super(BuildList, self).__init__()

        self.setMaximumHeight(200)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QListWidget.DragDropMode.DragDrop)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

        
    def getAllValues(self):

        attrData = []

        for i in range(self.count()):
            modAtRow = self.item(i)
            modType = modAtRow.modType
            modName = modAtRow.text()

            modAttrs = modAtRow.getValues()

            modAttrs['modType'] = modType
            modAttrs['name'] = modName
            modAttrs['character'] = None

            # todo: could check the values of what we're saving here

            attrData.append(modAttrs)

        return attrData


    def mousePressEvent(self, event):
        QtWidgets.QListWidget.mousePressEvent(self, event)


        listItem = self.item(self.currentRow())

        for i in range(self.count()):
            itemAtRow = self.item(i)
            if itemAtRow.attributeLayout:
                itemAtRow.attributeLayout.setVisible(False)

        listItem.attributeLayout.setVisible(True)

    def mouseDoubleClickEvent(self, event):
        QtWidgets.QListWidget.mouseDoubleClickEvent(self, event)

        currentItem = self.item(self.currentRow())

        self.editItem(currentItem)


class BuildListItem(QtWidgets.QListWidgetItem):
    def __init__(self, modType, customAttrs=None, attributeContainer=None):
        super(BuildListItem, self).__init__()

        self.attributeContainer = attributeContainer

        self.modType = modType

        self.setText(self.modType)
        self.setFlags(self.flags() | QtCore.Qt.ItemIsEditable)
        self.setSizeHint(QtCore.QSize(50,25))

        # Put attribute data inside of the build layout item! 
        self.customAttrs = customAttrs
        self.defaultAttrs = self.loadAttributeTemplates()

        if self.customAttrs:
            self.attributeLayout = AttributeLayout(parent=self.attributeContainer, 
                attributes=self.customAttrs)
        else:
            self.attributeLayout = AttributeLayout(parent=self.attributeContainer,
                attributes=self.defaultAttrs)

        self.attributeLayout.build()

    def loadAttributeTemplates(self):
        from .. import rigMods
        reload(rigMods)

        attrData = rigMods._MODULE_ARGS[self.modType]

        return attrData

    def getValues(self):

        attrLayout = self.attributeLayout.layout

        attrValues = {}

        for row in self.attributeLayout.rows:
            keyText = row[0].text()

            valueText = row[1].toJson()

            attrValues[keyText] = valueText


        attrValues['name'] = self.text()
        attrValues['character'] = None
        attrValues['modType'] = self.modType

        return attrValues

        # get the values of all the widgets in the attribute layout


###########################


class AttributeLayoutValue(object):

    def __init__(self, attribute, defaultValue):

        self.attribute = attribute
        # can be bool, string, label, list, dict
        self.valueType = type(defaultValue)
        self.defaultValue = defaultValue
        self.widget = self.build()
        self.widget.setMinimumHeight(25)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, 
                                            QtWidgets.QSizePolicy.Fixed)
        self.widget.setSizePolicy(sizePolicy)

    def build(self):
        """Build widget based off of type"""

        if self.valueType in [unicode, str]:
            
            if self.attribute == 'side':
                widget = QtWidgets.QComboBox()
                widget.addItem('L')
                widget.addItem('R')
                widget.addItem('C')
                widget.addItem('None')

                widget.setCurrentIndex(widget.findText(self.defaultValue))

            elif self.attribute == 'shapeType':
                import Osiris.lib.tools.shapes.lib as shapeLib

                widget = QtWidgets.QComboBox()

                for shapeType in shapeLib.Shape.types.keys():
                    widget.addItem(shapeType)

                widget.setCurrentIndex(widget.findText(self.defaultValue))

            elif self.attribute == 'solverType':
                import Osiris.lib.rigMods.IkChain as ikChain
                reload(ikChain)

                widget = QtWidgets.QComboBox()

                for solverType in ikChain.IkChain.solverTypes:
                    widget.addItem(solverType)

                widget.setCurrentIndex(widget.findText(self.defaultValue))

            else:
                widget = QtWidgets.QLineEdit(self.defaultValue)

        elif self.valueType is bool:
            widget = QtWidgets.QCheckBox()
            widget.setChecked(self.defaultValue)

        elif self.valueType is dict:
            widget = QtWidgets.QLineEdit(str(self.defaultValue))

        else:
            widget = QtWidgets.QLineEdit(str(self.defaultValue))

        return widget

    def translateToType(self, item):
        try:
            translated = ast.literal_eval(str(item))
            return translated
        except ValueError:
            # item type is a string and didn't like getting translated
            return item

    def toJson(self):

        if isinstance(self.widget, QtWidgets.QComboBox):
            return self.translateToType(self.widget.currentText())

        elif isinstance(self.widget, QtWidgets.QLineEdit):
            return self.translateToType(self.widget.text())

        elif isinstance(self.widget, QtWidgets.QCheckBox):
            return self.translateToType(self.widget.isChecked())



class AttributeLayout(QtWidgets.QWidget):
    def __init__(self, parent=None, attributes=None):
        super(AttributeLayout, self).__init__()

        # each row has a QHBoxLayout filled with a QLabel and AttributeLayoutValue item
        self.attributes = attributes
        self.rows = []
        self.layout = QtWidgets.QGridLayout()
        self.layout.setVerticalSpacing(5)
        self.setLayout(self.layout)

        if parent:
            parent.addWidget(self)

    def build(self):

        row = 0
        
        for attribute, value in self.attributes.items():
            # create a new table widget item
            attrWidget = QtWidgets.QLabel(attribute)
            # makes the key not editable
            value = AttributeLayoutValue(attribute=attribute, defaultValue=self.attributes[attribute])

            self.layout.addWidget(attrWidget, row, 0)
            self.layout.addWidget(value.widget, row, 1)

            self.rows.append([attrWidget, value])

            row += 1

        verticalSpacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.layout.addItem(verticalSpacer, row, 0)

        self.setVisible(False)

