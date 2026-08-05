"""Custom widgets for rigManager"""

import ast

from PySide6 import QtWidgets, QtGui, QtCore

from bmaya.maya_ui import qtbase
from bmaya.maya.rigging.shapes import shapelib

import maya.cmds as cmds


class ModuleList(qtbase.List):
    def __init__(self, attributeContainer=None):
        super(ModuleList, self).__init__()
        self.cellData = {}
        self.moduleLayouts = []
        self.attributeContainer = attributeContainer

    def setBuildList(self, listWidget):
        self.buildList = listWidget

    def mouseDoubleClickEvent(self, event):
        super(ModuleList, self).mouseDoubleClickEvent(event)

        if self.buildList:
            currentRowIndex = self.currentRow()
            try:
                selectedModType = self.item(currentRowIndex).text()
            except AttributeError:
                return

            newMod = BuildTreeItem(
                modType=selectedModType, attributeContainer=self.attributeContainer
            )

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
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.setIndentation(15)

        self.contextMenu = BuildListContextMenu(buildList=self)
        self.contextMenu.hide()

    def mousePressEvent(self, event):
        self.clearSelection()
        super(BuildList, self).mousePressEvent(event)

        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # PySide6: globalPosition used for high-DPI scaling accuracy
            globalCursorPos = event.globalPosition().toPoint()
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
            modType = modData["modType"]
            modName = modData["name"]
            modChildren = modData["children"]

            # Fix: Safeguard pop operations with defaults to prevent KeyError
            modData.pop("character", None)
            modData.pop("modType", None)
            modData.pop("name", None)
            modData.pop("children", None)
            print(modData)

            listItem = BuildTreeItem(
                modType=modType,
                attributeContainer=attributeLayoutContainer,
                customAttrs=modData,
            )
            listItem.setText(0, str(modName))

            if not parent:
                self.addTopLevelItem(listItem)
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
            modAttrs["children"] = []
            for child in mod.children:
                modAttrs["children"].append(getChildValues(child))
            return modAttrs

        for mod in self.topLevelItems:
            if mod.children:
                attrData.append(getChildValues(mod))
            else:
                modAttrs = mod.values
                modAttrs["children"] = []
                attrData.append(modAttrs)

        return attrData

    def hideAttrLayouts(self):
        for item in self.items:
            if item.attributeLayout:
                item.attributeLayout.setVisible(False)

    def renameItem(self):
        currentItem = self.currentItem()
        if currentItem:
            self.editItem(currentItem)

    def disableItem(self):
        pass

    def deleteItem(self):
        currentItem = self.currentItem()
        if not currentItem:
            return

        currentItem.attributeLayout.setVisible(False)
        currentItemParent = currentItem.parent()

        if currentItemParent:
            currentItemParent.takeChild(currentItemParent.indexOfChild(currentItem))
        else:
            self.takeTopLevelItem(self.indexOfTopLevelItem(currentItem))

        try:
            cmds.delete(currentItem.name)
        except Exception:
            pass

        self.contextMenu.hide()

    def duplicateItem(self):
        currentObject = self.currentItem()
        if not currentObject:
            return

        customAttrs = currentObject.values
        customAttrs.pop("character", None)
        customAttrs.pop("modType", None)
        customAttrs.pop("name", None)

        listItem = BuildTreeItem(
            modType=currentObject.modType,
            attributeContainer=currentObject.attributeContainer,
            customAttrs=customAttrs,
        )

        currentObjectParent = currentObject.parent()
        if currentObjectParent:
            currentObjectParent.addChild(listItem)
        else:
            self.addTopLevelItem(listItem)


class BuildTreeItem(qtbase.TreeItem):
    def __init__(self, modType, customAttrs=None, attributeContainer=None, name=None):
        super(BuildTreeItem, self).__init__()

        self.attributeContainer = attributeContainer
        self.modType = modType

        self.setText(0, name if name else self.modType)

        self.customAttrs = customAttrs
        self.defaultAttrs = self.loadAttributeTemplates()

        attrs_to_use = self.customAttrs if self.customAttrs else self.defaultAttrs
        self.attributeLayout = AttributeLayout(
            parent=self.attributeContainer, attributes=attrs_to_use, modType=modType
        )
        self.attributeLayout.build()

    @property
    def values(self):
        attrValues = {}
        for row in self.attributeLayout.rows:
            keyText = row[0].text()
            valueText = row[1].toJson()
            attrValues[keyText] = valueText

        attrValues["name"] = self.name
        attrValues["character"] = None
        attrValues["modType"] = self.modType
        return attrValues

    def loadAttributeTemplates(self):
        from bmaya.maya.rigging import modules
        return modules.MODULE_ARGS[self.modType]


class BuildListContextMenu(QtWidgets.QMenu):
    def __init__(self, buildList):
        super(BuildListContextMenu, self).__init__()

        renameAction = self.addAction("Rename")
        renameAction.triggered.connect(lambda: buildList.renameItem())

        disableAction = self.addAction("Disable")
        disableAction.triggered.connect(lambda: buildList.disableItem())

        deleteAction = self.addAction("Delete")
        deleteAction.triggered.connect(lambda: buildList.deleteItem())

        self.addSeparator()

        duplicateAction = self.addAction("Duplicate")
        duplicateAction.triggered.connect(lambda: buildList.duplicateItem())


class CustomLineEdit(QtWidgets.QLineEdit):
    def __init__(self, text, parent=None):
        super(CustomLineEdit, self).__init__(parent)
        self.defaultValue = text
        self.setText(self.defaultValue)
        self.contextMenu = LineEditMenu(self)
        self.contextMenu.hide()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            globalCursorPos = event.globalPosition().toPoint()
            self.contextMenu.move(globalCursorPos)
            self.contextMenu.show()
        else:
            super(CustomLineEdit, self).mousePressEvent(event)

    def replaceWithSelection(self):
        sel = cmds.ls(sl=True)
        if sel:
            if len(sel) == 1:
                self.setText(sel[0])
            else:
                self.setText(str([str(obj) for obj in sel]))

    def resetToDefault(self):
        self.setText(self.defaultValue)


class LineEditMenu(QtWidgets.QMenu):
    def __init__(self, lineEdit):
        super(LineEditMenu, self).__init__()
        replaceWithSelection = self.addAction("Replace With Selection")
        replaceWithSelection.triggered.connect(lambda: lineEdit.replaceWithSelection())

        resetAction = self.addAction("Reset To Default")
        resetAction.triggered.connect(lambda: lineEdit.resetToDefault())


class AttributeLayoutValue(object):
    def __init__(self, attribute, defaultValue):
        self.attribute = attribute
        self.valueType = type(defaultValue)
        self.defaultValue = defaultValue
        self.widget = self.build()
        self.widget.setMinimumHeight(25)
        
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.widget.setSizePolicy(sizePolicy)

    def build(self):
        if self.attribute == "side":
            widget = QtWidgets.QComboBox()
            widget.addItems(["L", "M", "R"])
            widget.setCurrentText(self.defaultValue)
        elif self.attribute == "alignWorld":
            widget = QtWidgets.QComboBox()
            widget.addItems(["None", "True", "False"])
            if isinstance(self.defaultValue, bool):
                widget.setCurrentText("True" if self.defaultValue else "False")
            else:
                widget.setCurrentText("None")
        elif self.valueType in [str]:
            if self.attribute in ["shapeType", "offsetShapeType"]:
                widget = QtWidgets.QComboBox()
                controlTypeData = shapelib.get_control_type_data()
                for shapeType in controlTypeData.keys():
                    widget.addItem(shapeType)
                widget.setCurrentIndex(widget.findText(self.defaultValue))
            else:
                widget = CustomLineEdit(self.defaultValue)
        elif self.valueType is bool:
            widget = QtWidgets.QCheckBox()
            widget.setChecked(self.defaultValue)
        else:
            widget = CustomLineEdit(str(self.defaultValue))
        return widget

    def translateToType(self, item):
        try:
            return ast.literal_eval(str(item))
        except (ValueError, SyntaxError):
            return item

    def toJson(self):
        if isinstance(self.widget, QtWidgets.QComboBox):
            return self.translateToType(self.widget.currentText())
        elif isinstance(self.widget, QtWidgets.QLineEdit):
            return self.translateToType(self.widget.text())
        elif isinstance(self.widget, QtWidgets.QCheckBox):
            return self.translateToType(self.widget.isChecked())


class AttributeLayout(QtWidgets.QWidget):
    def __init__(self, parent=None, attributes=None, modType=None):
        super(AttributeLayout, self).__init__()
        self.attributes = attributes
        self.rows = []
        self.layout = QtWidgets.QGridLayout()
        self.layout.setVerticalSpacing(5)
        self.setLayout(self.layout)
        self.modType = modType

        if parent:
            parent.addWidget(self)

    def build(self):
        row = 0

        typeLabel = QtWidgets.QLabel(f'Type: {self.modType}')
        self.layout.addWidget(typeLabel)
        row = 1

        def addAttr(attribute, value, row_idx):
            attrWidget = QtWidgets.QLabel(attribute)
            val_wrapper = AttributeLayoutValue(
                attribute=attribute, defaultValue=self.attributes[attribute]
            )
            self.layout.addWidget(attrWidget, row_idx, 0)
            self.layout.addWidget(val_wrapper.widget, row_idx, 1)
            self.rows.append([attrWidget, val_wrapper])

        commonAttrs = ["start_joint", "end_joint", "parent", "side", "mirror", "shapeType"]
        modAttrs = list(self.attributes.keys())
        moduleCommonAttrs = [attr for attr in commonAttrs if attr in modAttrs]

        for attribute in moduleCommonAttrs:
            addAttr(attribute, self.attributes[attribute], row)
            row += 1

        moduleUncommonAttrs = [attr for attr in modAttrs if attr not in moduleCommonAttrs]
        for attribute in moduleUncommonAttrs:
            addAttr(attribute, self.attributes[attribute], row)
            row += 1

        verticalSpacer = QtWidgets.QSpacerItem(
            1, 1, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding
        )
        self.layout.addItem(verticalSpacer, row, 0)
        self.setVisible(False)