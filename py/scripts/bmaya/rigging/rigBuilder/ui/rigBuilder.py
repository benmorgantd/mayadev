import os

import maya.cmds as cmds

from bmaya.lib.Qt import QtWidgets, QtCore

from bmaya.core import qtbase
from . import customWidgets, assetCreator

from bmaya.core import asset
from ..base import creator
from ..tools import locatorSystems
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

        self.loadProjects()
        self.loadAssetTypes()
        self.loadAssets()

        # self.widget.loadComponent.setEnabled(False)
        # self.widget.saveComponent.setEnabled(False)
        # self.widget.referenceComponent.setEnabled(False)
        self.widget.componentType.setEnabled(False)
        self.widget.build.setEnabled(False)

        self.newAsset = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def setupUI(self):

        self.moduleList = customWidgets.ModuleList(
            attributeContainer=self.widget.attributeLayoutContainer)
        # self.moduleList.itemDoubleClicked.connect(lambda item: self.addNewLocatorSystem(item))

        self.buildList = customWidgets.BuildList()

        self.widget.moduleListContainer.addWidget(
            self.moduleList)
        self.widget.buildListContainer.addWidget(self.buildList)

        self.moduleList.setBuildList(self.buildList)

        self.widget.projectName.currentIndexChanged.connect(lambda: self.loadAssetTypes())
        self.widget.assetType.currentIndexChanged.connect(lambda: self.loadAssets())

        self.assetInstance = None

        self.setupFileMenu()
        self.setupAssetMenu()
        self.setupComponentMenu()

        self.widget.menuLayout.addWidget(self.menu)

    def setupFileMenu(self):

        fileMenu = self.menu.addMenu('File')

        actionNew = fileMenu.addAction('New Build')
        actionNew.triggered.connect(lambda: self.resetBuildList())

        actionOpen = fileMenu.addAction('Open Build')
        actionOpen.triggered.connect(lambda: self.loadBuild())

        fileMenu.addSeparator()

        actionSave = fileMenu.addAction('Save Build')
        actionSave.triggered.connect(lambda: self.saveBuild(self.assetInstance.build.fullPath))

        actionSave = fileMenu.addAction('Save Build As...')
        actionSave.triggered.connect(lambda: self.saveBuild())

        fileMenu.addSeparator()

        self.actionOpenInExplorer = fileMenu.addAction('Open In Explorer')
        self.actionOpenInExplorer.triggered.connect(lambda: self.openAssetInExplorer())

    def setupAssetMenu(self):

        assetMenu = self.menu.addMenu('Asset')

        newAssetAction = assetMenu.addAction('New Asset')
        newAssetAction.triggered.connect(lambda: self.launchAssetWidget())

        versionAssetAction = assetMenu.addAction('Version Asset')
        versionAssetAction.triggered.connect(lambda: self.assetInstance.versionAsset())

    def setupComponentMenu(self):
        componentMenu = self.menu.addMenu('Component')

        newAssetAction = componentMenu.addAction('Load')
        newAssetAction.triggered.connect(self.loadComponent)

        newAssetAction = componentMenu.addAction('Reference')
        newAssetAction.triggered.connect(self.referenceComponent)

        newAssetAction = componentMenu.addAction('Save New Version')
        newAssetAction.triggered.connect(self.saveComponent)

        
    
    def openAssetInExplorer(self):
        self.assetInstance.openInExplorer(os.path.split(
            self.assetInstance.animRig.fullPath)[0])

    def launchAssetWidget(self):

        assetCreatorUI = assetCreator.AssetCreator(parent=qtbase.getMayaMainWindow(),
                                                    rigBuilder=self,
                                                    designerFile=os.path.join(
                                                        os.path.dirname(__file__),'assetCreator.ui'))

        assetCreatorUI.show()
        assetCreatorUI.activateWindow()

    def setupButtons(self):
        self.widget.loadCharacter.clicked.connect(lambda: self.initiateAsset())
        # self.widget.loadComponent.clicked.connect(lambda: self.loadComponent())
        # self.widget.saveComponent.clicked.connect(lambda: self.saveComponent())
        # self.widget.referenceComponent.clicked.connect(lambda: self.referenceComponent())
        self.widget.build.clicked.connect(lambda: self.buildCharacter())

    def loadProjects(self):
        projects = os.listdir(asset.PROJECT_ROOT)
        for project in projects:
            self.widget.projectName.addItem(project)

    def loadAssetTypes(self):
        assetTypes = os.listdir(os.path.join(asset.PROJECT_ROOT,
                                self.widget.projectName.currentText()))

        self.widget.assetType.clear()

        for assetType in assetTypes:
            self.widget.assetType.addItem(assetType)

    def loadAssets(self):
        assets = os.listdir(os.path.join(asset.PROJECT_ROOT,
                            self.widget.projectName.currentText(),
                            self.widget.assetType.currentText()))

        self.widget.assetName.clear()

        for assetName in assets:
            self.widget.assetName.addItem(assetName)

    def loadModules(self):
        import bmaya.rigging.rigModules as rigModules

        rigModsPath = os.path.dirname(os.path.abspath(rigModules.__file__))
        # load every module from the rigMods folder
        mods = os.listdir(rigModsPath)
        # sort them alphabetically 
        mods.sort()
        for mod in mods:
            if mod.endswith('.py') and mod != '__init__.py':
                self.moduleList.addItem(mod[0:-3])

    def saveComponent(self):
        componentType = self.widget.componentType.currentText()

        result = cmds.confirmDialog(message='Are you sure you would like to save ' + componentType + '?')

        if not result:
            return

        componentPath = self.assetInstance.componentPathFromType(componentType)

        if componentType in ['skeleton', 'mesh', 'animRig']:
            print 'saving ' + componentType
            self.assetInstance.versionFile(componentPath)
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

        print componentPath

        if componentType in ['skeleton', 'mesh', 'animRig', 'locators']:
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
            print "Cannot reference component type " + componentType

    def initiateAsset(self):
        project = self.widget.projectName.currentText()
        name = self.widget.assetName.currentText()
        assetType = self.widget.assetType.currentText()

        self.assetPath = asset.Asset.exists(project, name, assetType)

        if self.assetPath:
            self.setWindowTitle('Rig Builder: ' + self.assetPath)
            self.assetInstance = creator.initiate(name, project, assetType, 
            standalone=False)

            self.buildList.reset()

            self.loadBuild(self.assetInstance.build.fullPath)

            # self.widget.loadComponent.setEnabled(True)
            # self.widget.saveComponent.setEnabled(True)
            # self.widget.referenceComponent.setEnabled(True)
            self.widget.componentType.setEnabled(True)
            self.widget.build.setEnabled(True)

    def buildCharacter(self):
        if self.assetInstance:
            # save and version the build first
            buildPath = self.assetInstance.build.fullPath

            self.assetInstance.versionFile(buildPath)

            self.saveBuild(buildPath)

            creator.build(self.assetInstance, standalone=False)

    def exploreToBuildPath(self, action='Open', fileMode=1):

        buildpath = asset.PROJECT_ROOT

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
        
        self.resetBuildList()

        self.buildData = buildio.load(filepath)

        # self.locatorSystems = buildio.initLocatorsFromData(self.buildData)

        self.buildList.loadList(self.buildData, 
            attributeLayoutContainer=self.widget.attributeLayoutContainer)

        self.widget.build.setEnabled(True)

    def saveBuild(self, filepath=None):
        jsonData = self.buildList.getAllValues()

        # finalData = buildio.saveLocatorData(self.locatorSystems, jsonData)

        if not filepath:
            filepath = self.exploreToBuildPath(action='Save', fileMode=0)
            if not filepath:
                return

        try:
            self.assetInstance.versionFile(filepath)
        except AttributeError:
            # no asset is loaded
            pass
        
        buildio.save(filepath, jsonData)

    def resetAssetBoxes(self):

        self.widget.projectName.clear()
        self.widget.assetType.clear()
        self.widget.assetName.clear()

        self.loadProjects()
        self.loadAssetTypes()
        self.loadAssets()

    def resetBuildList(self):
        
        self.buildList.cellData = {}
        self.buildList.hideAttrLayouts()
        self.buildList.clear()

    def addNewLocatorSystem(self, item):
        # add a new locator system from the given Module List item

        currentModule = self.buildList.currentItem()

        name = self.moduleList.addModule()
        # the name is checked to be unique in addModule 

        if name:
            systemType = item.text()
            if currentModule:
                parentSystem = self.getLocatorSystemByName(currentModule.name)
            else:
                parentSystem = None

            system = getattr(locatorSystems, systemType)(name, parentSystem=parentSystem)

            if parentSystem:
                # parent to the first attachment point for the parent module
                system.systemGroup.parent = parentSystem.startLocator.name
            else:
                system.systemGroup.parent = 'Locators'

            self.locatorSystems.append(system)

    def getLocatorSystemByName(self, name):
        for system in self.locatorSystems:
            if system.moduleName == name:
                return system


######################################################################
######################################################################

def run():
    ui = RigBuilder(designerFile=os.path.join(os.path.dirname(__file__), 'widget.ui'))
    ui.dock()
    return ui


"""
- save locator data with build (DONE)
- mirror locator data
- add locator system when you add a module (DONE)
- what happens when you change the locator's parent?  (rename and reorder in Maya, update ui from there)
    - UI can't be reordered (DONE)
    - send order to ui
    - this updates the parent for build data
- what happens when you rename the module in the ui? in Maya? (^ same)
        - ask for the name of the module during the double click event
- changing side renames locators, 

"""