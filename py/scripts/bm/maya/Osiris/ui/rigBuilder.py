import os

import maya.cmds as cmds

from lib.Qt import QtWidgets, QtCore
from bm.maya.utils import mayaQt
from . import base, customWidgets, assetCreator
reload(base)
reload(customWidgets)
reload(assetCreator)

from ..base import asset
reload(asset)
from ..base import creator
reload(creator)
from ..tools.build import io as buildIO
reload(buildIO)


class RigBuilder(base.DockableWidget):
    def __init__(self, parent=None, designerFile=None, title='Rig Builder'):
        super(RigBuilder, self).__init__(parent, designerFile, title)

        self.parent = parent

        self.buildData = None

        self.setupUI()
        self.setupButtons()
        self.loadModules()

        self.loadProjects()
        self.loadAssetTypes()
        self.loadAssets()

        self.widget.loadComponent.setEnabled(False)
        self.widget.saveComponent.setEnabled(False)
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

        self.widget.projectName.currentIndexChanged.connect(lambda: self.loadAssetTypes())
        self.widget.assetType.currentIndexChanged.connect(lambda: self.loadAssets())

        self.assetInstance = None

        self.setupMenu()

    def setupMenu(self):

        menu = QtWidgets.QMenuBar()
        fileMenu = menu.addMenu('File')
        newAssetAction = fileMenu.addAction('New Asset')
        newAssetAction.triggered.connect(lambda: self.launchAssetWidget())

        fileMenu.addSeparator()

        actionSave = fileMenu.addAction('Save Build')
        actionSave.triggered.connect(lambda: self.saveBuild())

        fileMenu.addSeparator()

        self.actionOpenInExplorer = fileMenu.addAction('Open In Explorer')
        self.actionOpenInExplorer.triggered.connect(lambda: self.openAssetInExplorer())

        self.widget.menuLayout.addWidget(menu)

    def openAssetInExplorer(self):
        self.assetInstance.openInExplorer(os.path.split(
            self.assetInstance.getComponentPath('animRig'))[0])


    def launchAssetWidget(self):

        assetCreatorUI = assetCreator.AssetCreator(parent=mayaQt.getMayaMainWindow(),
                                                    rigBuilder=self,
                                                    designerFile='assetCreator.ui')

        assetCreatorUI.show()
        assetCreatorUI.activateWindow()


    def setupButtons(self):
        self.widget.loadCharacter.clicked.connect(lambda: self.initiateAsset())
        self.widget.loadComponent.clicked.connect(lambda: self.loadComponent())
        self.widget.saveComponent.clicked.connect(lambda: self.saveComponent())
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
        rigModsPath = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'rigMods'))
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

        if componentType in ['skeleton', 'mesh', 'animRig']:
            print 'saving ' + componentType
            self.assetInstance.versionFile(self.assetInstance.getComponentPath(componentType))
            cmds.file(rename=self.assetInstance.getComponentPath(componentType))
            cmds.file(save=True, type="mayaAscii", force=True)
        elif componentType == 'cvs':
            from bm.maya.Osiris.tools.shapes import io as shapeIO
            shapeIO.save(self.assetInstance.getComponentPath(componentType))
        elif componentType == 'weights':
            from bm.maya.Osiris.tools.weights import io as weightIO
            reload(weightIO)
            weightIO.save(self.assetInstance.getComponentPath(componentType))

    def loadComponent(self):
        componentType = self.widget.componentType.currentText()

        if componentType in ['skeleton', 'mesh', 'animRig']:
            self.assetInstance.openFile(self.assetInstance.getComponentPath(componentType))
        elif componentType == 'cvs':
            from bm.maya.Osirs.tools.shapes import io as shapeIO
            shapeIO.load(self.assetInstance.getComponentPath(componentType))
        elif componentType == 'weights':
            from bm.maya.Osiris.tools.weights import io as weightIO
            weightIO.load(self.assetInstance.getComponentPath(componentType))

    def initiateAsset(self):
        project = self.widget.projectName.currentText()
        name = self.widget.assetName.currentText()
        assetType = self.widget.assetType.currentText()

        self.assetPath = asset.Asset.exists(project, name, assetType)

        if self.assetPath:
            self.setWindowTitle('Osiris Rig Builder: ' + self.assetPath)
            self.assetInstance = creator.initiate(name, project, assetType, 
            standalone=False)

            self.buildList.reset()

            self.loadBuild(self.assetInstance.getComponentPath('build'))

            self.widget.loadComponent.setEnabled(True)
            self.widget.saveComponent.setEnabled(True)
            self.widget.build.setEnabled(True)

    def buildCharacter(self):
        if self.assetInstance:
            # save and version the build first
            buildPath = self.assetInstance.getComponentPath('build')

            self.assetInstance.versionFile(buildPath)

            self.saveBuild(buildPath)

            creator.build(self.assetInstance, standalone=False)

    def loadBuild(self, filepath=None):

        if not filepath:

            if self.assetInstance:
                filepath = self.assetInstance.getComponentPath('build')
            else:
                buildpath = asset.PROJECT_ROOT

                try:
                    # have the user navigate to the picker file
                    filepath = cmds.fileDialog2(okCaption='Open',
                                                fileMode=1,
                                                fileFilter='Build Files (build.json);;',
                                                caption='Open Build File',
                                                startingDirectory=buildpath)[0]
                except:
                    return

        self.buildData = buildIO.load(filepath)

        self.buildList.loadList(self.buildData, 
            attributeLayoutContainer=self.widget.attributeLayoutContainer)

        self.widget.build.setEnabled(True)

    def saveBuild(self, filepath=None):
        jsonData = self.buildList.getAllValues()

        if self.assetInstance:
            filepath = self.assetInstance.getComponentPath('build')
        else:
            buildpath = asset.PROJECT_ROOT

        if not filepath:
            try:
                # have the user navigate to the picker file
                filepath = cmds.fileDialog2(okCaption='Save',
                                            fileMode=0,
                                            fileFilter='Build Files (build.json);;',
                                            caption='Save Build File',
                                            startingDirectory=buildpath)[0]
            except:
                return

        self.assetInstance.versionFile(filepath)

        buildIO.save(filepath, jsonData)

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


##############
##############

def run():
    ui = RigBuilder(designerFile='widget.ui')
    ui.dock()
