import os
import json
from functools import partial

from . import assetCreator
import maya.cmds as cmds

from PySide6 import QtWidgets, QtCore

from bmaya.core import log
import bmaya.maya.constants
from bmaya.maya_ui import qtbase
from bmaya.core.progressmanager import ProgressManager
from bmaya.core.util import fileUtils
from bmaya.maya.asset import asset
from . import customWidgets

from bmaya.maya.rigging.base import rig
from bmaya.maya.rigging import buildio

from bmaya.maya_ui.qtbase import ProgressWindow


class RigManager(qtbase.DockableWidget):
    def __init__(self, parent=None, designerFile=None, title="Rig Manager"):
        super(RigManager, self).__init__(parent, designerFile, title)

        self.parent = parent
        self.buildData = None
        self.menu = QtWidgets.QMenuBar()

        self.setupUI()
        self.setupButtons()
        self.loadModules()

        self.widget.componentType.setEnabled(False)
        self.widget.build.setEnabled(False)

        self.newAsset = None
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

    def setupUI(self):
        self.moduleList = customWidgets.ModuleList(
            attributeContainer=self.widget.attributeLayoutContainer
        )
        self.buildList = customWidgets.BuildList()

        self.widget.moduleListContainer.addWidget(self.moduleList)
        self.widget.buildListContainer.addWidget(self.buildList)

        self.moduleList.setBuildList(self.buildList)
        self.rigInstance = None

        self.setupFileMenu()
        self.setupAssetMenu()
        self.setupToolsMenu()

        self.widget.menuLayout.addWidget(self.menu)

    def setupFileMenu(self):
        buildMenu = self.menu.addMenu("File")

        actionNew = buildMenu.addAction("New Build")
        actionNew.triggered.connect(lambda: self.resetBuildList())

        actionOpen = buildMenu.addAction("Open Build")
        actionOpen.triggered.connect(lambda: self.loadBuild())

        self.openRecentMenu = buildMenu.addMenu("Open Recent")
        recentFiles = self.getConfigData()["recentFiles"]
        recentFiles.reverse()

        for i, f in enumerate(recentFiles):
            if i >= 10:
                break
            recentFileAction = self.openRecentMenu.addAction(f)
            recentFileAction.triggered.connect(partial(self.loadBuild, f))

        buildMenu.addSeparator()

        actionSave = buildMenu.addAction("Save Build")
        actionSave.triggered.connect(
            lambda: self.saveBuild(self.rigInstance.build.full_path)
        )

        actionSaveAs = buildMenu.addAction("Save Build As...")
        actionSaveAs.triggered.connect(lambda: self.saveBuild())

        buildMenu.addSeparator()
        self.actionOpenInExplorer = buildMenu.addAction("Open In Explorer")
        self.actionOpenInExplorer.triggered.connect(lambda: self.openAssetInExplorer())

    def setupAssetMenu(self):
        assetMenu = self.menu.addMenu("Asset")

        newAssetAction = assetMenu.addAction("New Asset")
        newAssetAction.triggered.connect(lambda: self.launchAssetWidget())
        # TODO: when a new asset is created, open its build file by default. We will need a callback.

        versionAssetAction = assetMenu.addAction("Version Asset")
        versionAssetAction.triggered.connect(lambda: self.rigInstance.version_asset())

    def setupToolsMenu(self):
        toolsMenu = self.menu.addMenu("Tools")

        # CVs
        cvsMenu = toolsMenu.addMenu("CVs")

        actionMirror = cvsMenu.addAction("Mirror CVs")
        actionRemoveData = cvsMenu.addAction("Remove CV Data (Selection)")

        actionMirror.triggered.connect(lambda: self.mirrorCvData())
        actionRemoveData.triggered.connect(lambda: self.removeSelectedCVData())

        # Guides
        guidesMenu = toolsMenu.addMenu("Guides")

        actionBuildGuides = guidesMenu.addAction("Build Guides")
        actionBuildGuides.triggered.connect(self.build_guides)

        actionBuildBindJoints = guidesMenu.addAction("Build Bind Joints From Guides")
        actionBuildBindJoints.triggered.connect(self.build_bind_joints)

    def openAssetInExplorer(self):
        try:
            self.rigInstance.open_in_explorer(
                os.path.split(self.rigInstance.anim_rig.full_path)[0]
            )
        except AttributeError:
            log.warning("An asset instance has not been established")

    def launchAssetWidget(self):
        assetCreatorUI = assetCreator.AssetCreator(parent=qtbase.get_maya_main_window())
        assetCreatorUI.show()
        assetCreatorUI.activateWindow()

    def setupButtons(self):
        self.widget.loadComponent.clicked.connect(self.loadComponent)
        self.widget.saveComponent.clicked.connect(self.saveComponent)
        self.widget.referenceComponent.clicked.connect(self.referenceComponent)
        self.widget.build.clicked.connect(self.buildCharacter)

    def loadModules(self):
        from bmaya.maya.rigging import modules

        rigModsPath = os.path.dirname(os.path.abspath(modules.__file__))
        mods = os.listdir(rigModsPath)
        mods.sort()
        for mod in mods:
            if mod.endswith(".py") and not mod.startswith("_"):
                self.moduleList.addItem(mod[0:-3])

    def saveComponent(self):
        componentType = self.widget.componentType.currentText()

        # Updated to use your new custom Modal Confirm Dialog
        dialog = qtbase.ConfirmDialog(
            f"Are you sure you would like to save {componentType}?",
            windowTitle="Save Component",
        )

        if not dialog.exec():
            return

        if componentType not in [
            component.type for component in self.rigInstance.components
        ]:
            log.error(f"Invalid component type {componentType}")
            return

        componentInstance = getattr(self.rigInstance, componentType)
        componentInstance.save()

    def loadComponent(self):
        componentType = self.widget.componentType.currentText()
        log.info("loading component")

        if componentType not in [
            component.type for component in self.rigInstance.components
        ]:
            log.error(f"Invalid component type {componentType}")
            return

        componentInstance = getattr(self.rigInstance, componentType)
        componentInstance.load()

    def referenceComponent(self):
        componentType = self.widget.componentType.currentText()
        componentInstance = getattr(self.rigInstance, componentType)

        if hasattr(componentInstance, "reference"):
            componentInstance.reference()
        else:
            log.info(f"Cannot reference component type {componentType}")

    def buildCharacter(self):
        if self.rigInstance:
            manager = ProgressManager()

            with manager:
                progress_window = ProgressWindow()
                progress_window.show()
                buildPath = self.rigInstance.build.full_path
                fileUtils.version_file(buildPath)
                self.saveBuild(buildPath)
                self.rigInstance.build_rig()

    def exploreToBuildPath(self, action="Open", fileMode=1):
        buildpath = bmaya.maya.constants.RIGGING_PROJECT_DIR
        filepath = cmds.fileDialog2(
            okCaption=action,
            fileMode=fileMode,
            fileFilter="Build Files (*.json);;",
            caption=f"{action} Build File",
            startingDirectory=buildpath,
        )
        return filepath[0] if filepath else None

    def loadBuild(self, filepath=None):
        if not filepath:
            filepath = self.exploreToBuildPath(action="Open", fileMode=1)
            if not filepath:
                return

        asset_id = asset.Asset.get_asset_id_from_file(filepath)

        if not asset_id:
            log.warning(f"{filepath} is not a part of an asset. Building is disabled.")
            self.widget.build.setEnabled(False)
            self.widget.componentType.setEnabled(False)
            self.widget.currentAssetLabel.setText("No Asset Loaded")
        else:
            self.rigInstance = rig.Rig(asset_id)
            self.widget.componentType.setEnabled(True)
            self.widget.build.setEnabled(True)
            self.widget.currentAssetLabel.setText(asset_id)

        self.resetBuildList()
        self.buildData = buildio.load(filepath)
        self.buildList.loadList(
            self.buildData,
            attributeLayoutContainer=self.widget.attributeLayoutContainer,
        )
        self.addRecentFile(filepath)

    def saveBuild(self, filepath=None):
        jsonData = self.buildList.getAllValues()

        if not filepath:
            filepath = self.exploreToBuildPath(action="Save", fileMode=0)
            if not filepath:
                return

        try:
            fileUtils.version_file(filepath)
        except AttributeError:
            asset_id = asset.Asset.get_asset_id_from_file(filepath)
            if not asset_id:
                return
            else:
                self.rigInstance = rig.Rig(asset_id)
                self.widget.componentType.setEnabled(True)
                self.widget.build.setEnabled(True)
                self.widget.currentAssetLabel.setText(asset_id)
                fileUtils.version_file(filepath)

        buildio.save(filepath, jsonData)

    def resetBuildList(self):
        self.buildList.cellData = {}
        self.buildList.hideAttrLayouts()
        self.buildList.clear()

    def getConfigData(self):
        configFile = os.path.join(os.path.dirname(__file__), "config.json")
        with open(configFile, "r") as f:
            return json.load(f)

    def addRecentFile(self, filepath):
        configFile = os.path.join(os.path.dirname(__file__), "config.json")
        with open(configFile, "r") as f:
            configData = json.load(f)

        recentFiles = configData["recentFiles"]
        if filepath not in recentFiles:
            recentFiles.append(filepath)

        configData["recentFiles"] = recentFiles
        with open(configFile, "w") as f:
            json.dump(configData, f, indent=4)

    def mirrorCvData(self):
        from bmaya.maya.rigging.shapes import shapeio

        shapeio.mirror(self.rigInstance.component_path_from_type("cvs"))

    def removeSelectedCVData(self):
        from bmaya.maya.rigging.shapes import shapeio

        shapeio.remove_shape_data(
            self.rigInstance.component_path_from_type("cvs"), cmds.ls(selection=True)
        )

    def build_guides(self):
        self.rigInstance.build_guides()
    
    def build_bind_joints(self):
        self.rigInstance.build_bind_joints()


def run():
    ui = RigManager(
        parent=qtbase.get_maya_main_window(),
        designerFile=os.path.join(os.path.dirname(__file__), "rigManager.ui"),
    )
    ui.dock()
    return ui
