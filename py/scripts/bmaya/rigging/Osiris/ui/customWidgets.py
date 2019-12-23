'''Custom widgets for rigBuilder'''

import ast
import uuid
import re
from collections import OrderedDict


from bmaya.lib.Qt import QtWidgets, QtGui, QtCore, QtCompat

from bmaya.core import qtbase
reload(qtbase)


class ModuleList(qtbase.List):
    def __init__(self, attributeContainer=None):
        super(ModuleList, self).__init__()

        self.cellData = {}
        self.moduleLayouts = []

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

            # get the current item instead and add it as a child. If nothing is selected, 
            # add it to the top node

            newMod = BuildListItem(modType=selectedModType, attributeContainer=self.attributeContainer)

            currentItem = self.buildList.currentItem()
            if currentItem:
                currentItem.addChild(newMod)
            else:
                self.buildList.addTopLevelItem(newMod)
            

class BuildList(qtbase.Tree):
    def __init__(self):
        super(BuildList, self).__init__()

        self.cellData = {}
        self.moduleLayouts = []

        self.setMaximumHeight(200)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QTreeWidget.DragDropMode.DragDrop)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

        self.contextMenu = BuildListContextMenu(buildList=self)
        self.contextMenu.hide()


    def mousePressEvent(self, event):
        self.clearSelection()

        QtWidgets.QTreeWidget.mousePressEvent(self, event)

        # check if it's a right click
        if event.button() == QtCore.Qt.RightButton:
            globalCursorPos = QtGui.QCursor().pos()
            self.contextMenu.move(globalCursorPos)
            self.contextMenu.show()

        listItem = self.currentItem()

        if not listItem:
            return

        self.hideAttrLayouts()
        
        listItem.attributeLayout.setVisible(True)

    def mouseDoubleClickEvent(self, event):
        currentItem = self.currentItem()
        if currentItem:
            currentItem.setExpanded(not currentItem.isExpanded())

    def loadList(self, buildData, attributeLayoutContainer):

        self.clear()

        def addChildren(modData, parent=None):
            modType = modData['modType']
            modName = modData['name']
            modChildren = modData['children']

            modData.pop('character')
            modData.pop('modType')
            modData.pop('name')
            modData.pop('children')

            listItem = BuildListItem(modType=modType, 
                                     attributeContainer=attributeLayoutContainer,
                                     customAttrs=modData)

            listItem.setText(0, str(modName))

            if not parent:
                 self.addTopLevelItem(listItem)

                 for child in modChildren:
                    addChildren(child, parent=listItem)

            else:
                parent.addChild(listItem)

                for child in modChildren:
                    addChildren(child, parent=listItem)
            
        for topLevelMod in buildData:
            addChildren(topLevelMod, parent=None)
        
    def getAllValues(self):

        attrData = []

        def getChildValues(mod):
            modAttrs = mod.values
            modAttrs['children'] = []

            for child in mod.children:
                modAttrs['children'].append(getChildValues(child))

            return modAttrs

        for mod in self.topLevelItems:
            if mod.children:
                attrData.append(getChildValues(mod))
            else:
                # top level item with no children
                modAttrs = mod.values
                modAttrs['children'] = []
                attrData.append(modAttrs)

        return attrData

    def hideAttrLayouts(self):
        
        for item in self.items:
            if item.attributeLayout:
                item.attributeLayout.setVisible(False)

    def renameItem(self):
        
        currentItem = self.currentItem()
        self.editItem(currentItem)

    def deleteItem(self):
        # delete the currently selected item
        currentItem = self.currentItem()
        currentItem.attributeLayout.setVisible(False)

        currentItemParent = currentItem.parent()

        currentItemParent.takeChild(currentItemParent.indexOfChild(currentItem))

        self.contextMenu.hide()

    def duplicateItem(self):
        
        # get the selection
        currentObject = self.currentItem()

        # copy the attributes over
        customAttrs = currentObject.values

        customAttrs.pop('character')
        customAttrs.pop('modType')
        customAttrs.pop('name')

        # create a new list item of the same type as the selection
        listItem = BuildListItem(modType=currentObject.modType, 
                                  attributeContainer=currentObject.attributeContainer,
                                  customAttrs=customAttrs)

        currentObjectParent = currentObject.parent()

        if currentObjectParent:
            currentObjectParent.addChild(listItem)
        else:
            self.addTopLevelItem(listItem)


class BuildListItem(qtbase.TreeItem):
    def __init__(self, modType, customAttrs=None, attributeContainer=None):
        super(BuildListItem, self).__init__()

        self.attributeContainer = attributeContainer
        self.modType = modType

        self.setText(0, self.modType)
    
        # Put attribute data inside of the build layout item
        self.customAttrs = customAttrs
        self.defaultAttrs = self.loadAttributeTemplates()

        if self.customAttrs:
            self.attributeLayout = AttributeLayout(parent=self.attributeContainer, 
                attributes=self.customAttrs)
        else:
            self.attributeLayout = AttributeLayout(parent=self.attributeContainer,
                attributes=self.defaultAttrs)

        self.attributeLayout.build()

    @property
    def values(self):
        attrValues = OrderedDict()

        for row in self.attributeLayout.rows:
            keyText = row[0].text()
            valueText = row[1].toJson()
            attrValues[keyText] = valueText

        attrValues['name'] = self.name
        attrValues['character'] = None
        attrValues['modType'] = self.modType

        return attrValues

    def loadAttributeTemplates(self):
        from bmaya.rigging import rigModules
        reload(rigModules)

        attrData = rigModules.MODULE_ARGS[self.modType]

        return attrData


class BuildListContextMenu(QtWidgets.QMenu):
    def __init__(self, buildList):
        super(BuildListContextMenu, self).__init__()

        renameAction = self.addAction('Rename')
        renameAction.triggered.connect(lambda: buildList.renameItem())

        deleteAction = self.addAction('Delete')
        deleteAction.triggered.connect(lambda: buildList.deleteItem())

        self.addSeparator()

        duplicateAction = self.addAction('Duplicate')
        duplicateAction.triggered.connect(lambda: buildList.duplicateItem())


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
                from bmaya.rigging.shapes import shapelib

                widget = QtWidgets.QComboBox()

                for shapeType in shapelib.Shape.types.keys():
                    widget.addItem(shapeType)

                widget.setCurrentIndex(widget.findText(self.defaultValue))

            elif self.attribute == 'solverType':
                import Osiris.lib.rigModules.IkChain as ikChain
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

