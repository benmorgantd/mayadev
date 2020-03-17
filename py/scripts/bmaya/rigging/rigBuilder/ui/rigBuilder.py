import os
import json
from functools import partial

import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.lib.Qt import QtWidgets, QtCore

from bmaya.core import qtbase, fileio, asset
from . import customWidgets, assetCreator

from ..base import creator
from bmaya.rigging.rigBuilder.tools import buildio


class RigBuilder(qtbase.DockableWidget):
    def __init__(self, parent=None, designerFile=None, title='Rig Builder'):
        super(RigBuilder, self).__init__(parent, designerFile, title)

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

        self.assetInstance = None

        self.setupFileMenu()
        self.setupAssetMenu()

        self.widget.menuLayout.addWidget(self.menu)

    def setupFileMenu(self):

        buildMenu = self.menu.addMenu('Build')

        actionNew = buildMenu.addAction('New Build')
        actionNew.triggered.connect(lambda: self.resetBuildList())

        actionOpen = buildMenu.addAction('Open Build')
        actionOpen.triggered.connect(lambda: self.loadBuild())

        self.openRecentMenu = buildMenu.addMenu('Open Recent')
        recentFiles = self.getConfigData()['recentFiles']

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
        actionSave.triggered.connect(lambda: self.saveBuild(self.assetInstance.build.fullPath))

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
        versionAssetAction.triggered.connect(lambda: self.assetInstance.versionAsset())
        
    
    def openAssetInExplorer(self):
        try:
            self.assetInstance.openInExplorer(os.path.split(
                self.assetInstance.animRig.fullPath)[0])
        except AttributeError:
            om.MGlobal.displayWarning('An asset instance has not been established')

    def launchAssetWidget(self):

        assetCreatorUI = assetCreator.AssetCreator(parent=qtbase.getMayaMainWindow(),
                                                    rigBuilder=self,
                                                    designerFile=os.path.join(
                                                        os.path.dirname(__file__),'assetCreator.ui'))

        assetCreatorUI.show()
        assetCreatorUI.activateWindow()

    def setupButtons(self):
        # self.widget.loadCharacter.clicked.connect(lambda: self.initiateAsset())
        self.widget.loadComponent.clicked.connect(lambda: self.loadComponent())
        self.widget.saveComponent.clicked.connect(lambda: self.saveComponent())
        self.widget.referenceComponent.clicked.connect(lambda: self.referenceComponent())
        self.widget.build.clicked.connect(lambda: self.buildCharacter())

    def loadModules(self):
        from bmaya.rigging import modules

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

        result = cmds.confirmDialog(message='Are you sure you would like to save ' + componentType + '?')

        if not result:
            return

        componentPath = self.assetInstance.componentPathFromType(componentType)

        if componentType in ['skeleton', 'mesh', 'animRig']:
            om.MGlobal.displayInfo('Saving ' + componentType + ' ...')
            fileio.versionFile(componentPath)
            cmds.file(rename=componentPath)
            cmds.file(save=True, type="mayaAscii", force=True)
        elif componentType == 'cvs':
            from bmaya.rigging.shapes import shapeio
            shapeio.save(componentPath)
        elif componentType == 'weights':
            from bmaya.rigging.weights import weightio
            weightio.save(componentPath)

    def loadComponent(self):
        componentType = self.widget.componentType.currentText()

        componentPath = self.assetInstance.componentPathFromType(componentType)

        if componentType in ['skeleton', 'mesh', 'animRig']:
            self.assetInstance.openFile(componentPath)
        elif componentType == 'cvs':
            from bmaya.rigging.shapes import shapeio
            shapeio.load(componentPath)
        elif componentType == 'weights':
            from bmaya.rigging.weights import weightio
            weightFiles = self.assetInstance.findFilesOfType(componentPath, 'weights')
            for f in weightFiles:
                weightio.load(os.path.join(componentPath, f))

    def referenceComponent(self):
        componentType = self.widget.componentType.currentText()
        componentPath = self.assetInstance.componentPathFromType(componentType)

        if componentType in ['skeleton', 'mesh', 'animRig']:
            self.assetInstance.referenceFile(componentPath)
        else:
            om.MGlobal.displayInfo("Cannot reference component type " + componentType)

    def buildCharacter(self):
        if self.assetInstance:
            # save and version the build first
            buildPath = self.assetInstance.build.fullPath

            fileio.versionFile(buildPath)

            self.saveBuild(buildPath)

            creator.build(self.assetInstance, standalone=False)

    def exploreToBuildPath(self, action='Open', fileMode=1):

        buildpath = asset.PROJECT_ROOT

        filepath = cmds.fileDialog2(okCaption=action,
                                    fileMode=fileMode,
                                    fileFilter='Build Files (build.json);;',
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
        assetArgs = asset.Asset.getAssetArgsFromFile(filepath)

        print assetArgs
        print filepath

        if any(not arg for arg in assetArgs):
            # we could set something in the ui saying we're not working on an asset
            om.MGlobal.displayWarning('File is not a part of an asset. Building is disabled.')
            self.widget.build.setEnabled(False)
            self.widget.componentType.setEnabled(False)
            self.widget.currentAssetLabel.setText('(No Asset Loaded).')
        else:
            self.assetInstance = creator.initiate(*assetArgs, standalone=False)

            self.widget.componentType.setEnabled(True)
            self.widget.build.setEnabled(True)
            self.widget.currentAssetLabel.setText('{0}'.format(' | '.join([assetArgs[1], assetArgs[2], assetArgs[0]])))
    
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
            fileio.versionFile(filepath)
        except AttributeError:
            assetArgs = asset.Asset.getAssetArgsFromFile(filepath)

            if any(not arg for arg in assetArgs):
                # file was not saved into an asset
                return
            else:
                self.assetInstance = creator.initiate(*assetArgs, standalone=False)

                self.widget.componentType.setEnabled(True)
                self.widget.build.setEnabled(True)
                self.widget.currentAssetLabel.setText('{0}'.format(' | '.join([assetArgs[1], assetArgs[2], assetArgs[0]])))

                fileio.versionFile(filepath)

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

def run():
    ui = RigBuilder(designerFile=os.path.join(os.path.dirname(__file__), 'widget.ui'))
    ui.dock()
    return ui

