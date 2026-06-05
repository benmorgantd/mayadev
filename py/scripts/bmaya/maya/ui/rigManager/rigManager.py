import os
import json
from functools import partial

import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya3.lib.Qt import QtWidgets, QtCore

from bmaya3.maya.ui import qtbase
from bmaya3.maya.util import fileUtils
from bmaya3.maya.asset import asset
from . import customWidgets, assetCreator

from bmaya3.maya.rigging.base import rig
from bmaya3.rigging import buildio


class RigManager(qtbase.DockableWidget):
    def __init__(self, parent=None, designerFile=None, title='Rig Manager'):
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

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def setupUI(self):

        self.moduleList = customWidgets.ModuleList(
            attributeContainer=self.widget.attributeLayoutContainer)

        self.buildList = customWidgets.BuildList()

        self.widget.moduleListContainer.addWidget(
            self.moduleList)
        self.widget.buildListContainer.addWidget(self.buildList)

        self.moduleList.setBuildList(self.buildList)

        self.rigInstance = None

        self.setupFileMenu()
        self.setupAssetMenu()
        self.setupCVsMenu()

        self.widget.menuLayout.addWidget(self.menu)

    def setupFileMenu(self):

        buildMenu = self.menu.addMenu('File')

        actionNew = buildMenu.addAction('New Build')
        actionNew.triggered.connect(lambda: self.resetBuildList())

        actionOpen = buildMenu.addAction('Open Build')
        actionOpen.triggered.connect(lambda: self.loadBuild())

        self.openRecentMenu = buildMenu.addMenu('Open Recent')
        recentFiles = self.getConfigData()['recentFiles']
        recentFiles.reverse()

        i = 0
        for f in recentFiles:
            recentFileAction = self.openRecentMenu.addAction(f)
            recentFileAction.triggered.connect(partial(self.loadBuild, f))

            i += 1
            if i > 10:
                # only show 10 most recent files
                break

        buildMenu.addSeparator()

        actionSave = buildMenu.addAction('Save Build')
        actionSave.triggered.connect(lambda: self.saveBuild(self.rigInstance.build.fullPath))

        actionSave = buildMenu.addAction('Save Build As...')
        actionSave.triggered.connect(lambda: self.saveBuild())

        buildMenu.addSeparator()

        self.actionOpenInExplorer = buildMenu.addAction('Open In Explorer')
        self.actionOpenInExplorer.triggered.connect(lambda: self.openAssetInExplorer())

    def setupAssetMenu(self):

        assetMenu = self.menu.addMenu('Asset')

        newAssetAction = assetMenu.addAction('New Asset')
        newAssetAction.triggered.connect(lambda: self.launchAssetWidget())

        versionAssetAction = assetMenu.addAction('Version Asset')
        versionAssetAction.triggered.connect(lambda: self.rigInstance.versionAsset())
        
    def setupCVsMenu(self):
        cvsMenu = self.menu.addMenu('CV Tools')

        actionMirror = cvsMenu.addAction('Mirror')
        actionRemoveData = cvsMenu.addAction('Remove Data (Selection)')

        actionMirror.triggered.connect(lambda: self.mirrorCvData())
        actionRemoveData.triggered.connect(lambda: self.removeSelectedCVData())
    
    def openAssetInExplorer(self):
        try:
            self.rigInstance.openInExplorer(os.path.split(
                self.rigInstance.animRig.fullPath)[0])
        except AttributeError:
            om.MGlobal.displayWarning('An asset instance has not been established')

    def launchAssetWidget(self):

        assetCreatorUI = assetCreator.AssetCreator(parent=qtbase.getMayaMainWindow(),
                                                   designerFile=os.path.join(os.path.dirname(__file__),'assetCreator.ui'))

        assetCreatorUI.show()
        assetCreatorUI.activateWindow()

    def setupButtons(self):
        self.widget.loadComponent.clicked.connect(self.loadComponent)
        self.widget.saveComponent.clicked.connect(self.saveComponent)
        self.widget.referenceComponent.clicked.connect(self.referenceComponent)
        self.widget.build.clicked.connect(self.buildCharacter)

    def loadModules(self):
        # TODO: move this down to the module file
        # TODO: remove inline import
        from bmaya3.rigging import modules

        rigModsPath = os.path.dirname(os.path.abspath(modules.__file__))
        # load every module from the rigMods folder
        mods = os.listdir(rigModsPath)
        # sort them alphabetically 
        mods.sort()
        for mod in mods:
            if mod.endswith('.py') and not mod.startswith('_'):
                self.moduleList.addItem(mod[0:-3])

    def saveComponent(self):
        componentType = self.widget.componentType.currentText()

        result = cmds.confirmDialog(message='Are you sure you would like to save ' + componentType + '?',
                                    button=['Yes', 'No'], defaultButton='Yes', cancelButton='No')
                                    
        if result in ['dismiss', 'No']:
            return

        if componentType not in [component.type for component in self.rigInstance.components]:
            om.MGlobal.displayError('Invalid component type {}'.format(componentType))
            return

        componentInstance = getattr(self.rigInstance, componentType)
        componentInstance.save()


    def loadComponent(self):
        componentType = self.widget.componentType.currentText()
        print('loading component')

        # result = cmds.confirmDialog(message='Are you sure you would like to open ' + componentType + '?',
        #                             button=['Yes', 'No'], defaultButton='Yes', cancelButton='No')
        
        # if result in ['dismiss', 'No']:
        #     return

        if componentType not in [component.type for component in self.rigInstance.components]:
            om.MGlobal.displayError('Invalid component type {}'.format(componentType))
            return

        componentInstance = getattr(self.rigInstance, componentType)
        componentInstance.load()

    def referenceComponent(self):
        componentType = self.widget.componentType.currentText()
        componentInstance = getattr(self.rigInstance, componentType)

        if hasattr(componentInstance, 'reference'):
            componentInstance.reference()
        else:
            om.MGlobal.displayInfo("Cannot reference component type " + componentType)

    def buildCharacter(self):
        if self.rigInstance:
            # save and version the build first
            buildPath = self.rigInstance.build.fullPath

            fileUtils.versionFile(buildPath)

            self.saveBuild(buildPath)

            self.rigInstance.buildRig()

    def exploreToBuildPath(self, action='Open', fileMode=1):

        buildpath = asset.PROJECT_DIR

        filepath = cmds.fileDialog2(okCaption=action,
                                    fileMode=fileMode,
                                    fileFilter='Build Files (*.json);;',
                                    caption=action + ' Build File',
                                    startingDirectory=buildpath)

        if not filepath:
            return
        
        else:
            return filepath[0]

    def loadBuild(self, filepath=None):

        if not filepath:
            filepath = self.exploreToBuildPath(action='Open', fileMode=1)
            if not filepath:
                return

        # set our asset to the one derived from the path
        assetId = asset.Asset.getAssetIdFromFile(filepath)

        if not assetId:
            om.MGlobal.displayWarning('{} is not a part of an asset. Building is disabled.'.format(filepath))
            self.widget.build.setEnabled(False)
            self.widget.componentType.setEnabled(False)
            self.widget.currentAssetLabel.setText('No Asset Loaded')
        else:
            self.rigInstance = rig.Rig(assetId)
            self.widget.componentType.setEnabled(True)
            self.widget.build.setEnabled(True)
            self.widget.currentAssetLabel.setText(assetId)
    
        self.resetBuildList()
        self.buildData = buildio.load(filepath)
        self.buildList.loadList(self.buildData, 
            attributeLayoutContainer=self.widget.attributeLayoutContainer)

        self.addRecentFile(filepath)

    def saveBuild(self, filepath=None):
        jsonData = self.buildList.getAllValues()

        if not filepath:
            filepath = self.exploreToBuildPath(action='Save', fileMode=0)
            if not filepath:
                return

        try:
            fileUtils.versionFile(filepath)
        except AttributeError:
            assetId = asset.Asset.getAssetIdFromFile(filepath)

            if not assetId:
                # file was not saved into an asset
                return
            else:
                self.rigInstance = rig.Rig(assetId)

                self.widget.componentType.setEnabled(True)
                self.widget.build.setEnabled(True)
                self.widget.currentAssetLabel.setText(assetId)

                fileUtils.versionFile(filepath)

        buildio.save(filepath, jsonData)

    def resetBuildList(self):
        
        self.buildList.cellData = {}
        self.buildList.hideAttrLayouts()
        self.buildList.clear()


    def getConfigData(self):
        configFile = os.path.join(os.path.dirname(__file__), 'config.json')

        with open(configFile, "r") as f:
            configData = json.load(f)

        return configData

    def addRecentFile(self, filepath):
        configFile = os.path.join(os.path.dirname(__file__), 'config.json')

        with open(configFile, "r") as f:
            configData = json.load(f)

        recentFiles = configData['recentFiles']

        if filepath not in recentFiles:
            recentFiles.append(filepath)

        configData['recentFiles'] = recentFiles

        with open(configFile, "w") as f:
            json.dump(configData, f, indent=4)

    def mirrorCvData(self):
        from bmaya3.maya.rigging.shapes import shapeio
        shapeio.mirror(self.rigInstance.componentPathFromType('cvs'))

    def removeSelectedCVData(self):
        from bmaya3.maya.rigging.shapes import shapeio
        import maya.cmds as cmds

        shapeio.removeShapeData(self.rigInstance.componentPathFromType('cvs'), cmds.ls(selection=True))

def run():
    ui = RigManager(designerFile=os.path.join(os.path.dirname(__file__), 'rigManager.ui'))
    ui.dock()
    return ui

