import os

import maya.cmds as cmds

from lib.Qt import QtWidgets
from bm.maya.utils import mayaQt
from . import base, customWidgets
reload(base)
reload(customWidgets)

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
        self.widget.menuLayout.addWidget(menu)

    def launchAssetWidget(self):

        assetBuilderUI = assetBuilder.AssetBuilder(
            parent=mayaQt.getMayaMainWindow())

        assetBuilderUI.show()


    def setupButtons(self):
        self.widget.loadCharacter.clicked.connect(lambda: self.initiateAsset())
        self.widget.loadComponent.clicked.connect(lambda: self.loadComponent())
        self.widget.saveComponent.clicked.connect(lambda: self.saveComponent())
        self.widget.build.clicked.connect(lambda: self.buildCharacter())


    def loadProjects(self):
        projects = os.listdir(asset._PROJECT_ROOT)
        for project in projects:
            self.widget.projectName.addItem(project)

    def loadAssetTypes(self):
        assetTypes = os.listdir(os.path.join(asset._PROJECT_ROOT,
                                self.widget.projectName.currentText()))

        self.widget.assetType.clear()

        for assetType in assetTypes:
            self.widget.assetType.addItem(assetType)

        self.loadAssets()

    def loadAssets(self):
        assets = os.listdir(os.path.join(asset._PROJECT_ROOT,
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

    def setupFileMenu(self):
        self.widget.actionLoad.triggered.connect(lambda: self.loadBuild())
        self.widget.actionSave.triggered.connect(lambda: self.saveBuild())

    def setupAssetMenu(self):

        self.widget.actionSaveSkeleton.triggered.connect(lambda: self.saveComponent('skeleton'))
        self.widget.actionLoadSkeleton.triggered.connect(lambda: self.loadComponent('skeleton'))

        self.widget.actionSaveMesh.triggered.connect(lambda: self.saveComponent('mesh'))
        self.widget.actionLoadMesh.triggered.connect(lambda: self.loadComponent('mesh'))

        self.widget.actionSaveCVS.triggered.connect(lambda: self.saveComponent('cvs'))
        self.widget.actionLoadCVS.triggered.connect(lambda: self.loadComponent('cvs'))

        self.widget.actionSaveWeights.triggered.connect(lambda: self.saveComponent('weights'))
        self.widget.actionLoadWeights.triggered.connect(lambda: self.loadComponent('weights'))

        self.widget.actionSaveAnimRig.triggered.connect(lambda: self.saveComponent('animRig'))
        self.widget.actionLoadAnimRig.triggered.connect(lambda: self.loadComponent('animRig'))

    def saveComponent(self):
        componentType = self.widget.componentType.currentText()

        result = cmds.confirmDialog(message='Are you sure you would like to save ' + componentType + '?')

        if not result:
            return

        if componentType in ['skeleton', 'mesh', 'animRig']:
            self.assetInstance.versionFile(self.assetInstance.getComponentPath(componentType))
            cmds.file(rename=self.assetInstance.getComponentPath(componentType))
            cmds.file(save=True, type="mayaAscii", force=True)
        elif componentType == 'cvs':
            import Osiris.lib.tools.shapes.io as shapeIO
            shapeIO.save(self.assetInstance.getComponentPath(componentType))
        elif componentType == 'weights':
            import Osiris.lib.tools.weights.io as weightIO
            reload(weightIO)
            weightIO.save(self.assetInstance.getComponentPath(componentType))

    def loadComponent(self):
        componentType = self.widget.componentType.currentText()

        if componentType in ['skeleton', 'mesh', 'animRig']:
            self.assetInstance.openFile(self.assetInstance.getComponentPath(componentType))
        elif componentType == 'cvs':
            import Osiris.lib.tools.shapes.io as shapeIO
            shapeIO.load(self.assetInstance.getComponentPath(componentType))
        elif componentType == 'weights':
            import Osiris.lib.tools.weights.io as weightIO
            weightIO.load(self.assetInstance.getComponentPath(componentType))
        elif componentType == 'build':
            self.loadBuild()

    def initiateAsset(self):
        project = self.widget.projectName.currentText()
        name = self.widget.assetName.currentText()
        assetType = self.widget.assetType.currentText()

        self.assetPath = asset.Asset.exists(project, name, assetType)

        if self.assetPath:
            self.setWindowTitle('Osiris Rig Builder: ' + self.assetPath)
            self.assetInstance = creator.initiate(name, project, assetType, standalone=False)
            self.loadBuild(self.assetInstance.getComponentPath('build'))

        else:
            result = cmds.confirmDialog(title='Error Loading Character',
                message='Asset <{0}> \nType <{1}>\nProject <{2}>\ndoes not exist.'.format(name, assetType, project),
                button=['Create Asset', 'No'],
                icon='warning',
                cancelButton='No',
                dismissString='No')

            if result == "Create Asset":
                self.assetInstance = creator.initiate(name, project, assetType, standalone=False)
                self.loadBuild(self.assetInstance.getComponentPath('build'))


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
                buildpath = asset._PROJECT_ROOT

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

        self.loadBuildList()

        self.widget.build.setEnabled(True)

    def saveBuild(self, filepath=None):
        jsonData = self.buildList.getAllValues()

        if self.assetInstance:
            filepath = self.assetInstance.getComponentPath('build')
        else:
            buildpath = asset._PROJECT_ROOT

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

    def loadBuildList(self):

        self.buildList.clear()

        for mod in self.buildData:

            modType = mod['modType']
            modName = mod['name']

            customAttrs = mod
            customAttrs.pop('character')
            customAttrs.pop('modType')
            customAttrs.pop('name')

            listItem = customWidgets.BuildListItem(modType=modType, 
                                                   attributeContainer=self.widget.attributeLayoutContainer,
                                                   customAttrs=customAttrs)
            listItem.setText(str(modName))
            self.buildList.addItem(listItem)


##############
##############

def run():
    ui = RigBuilder(designerFile='widget.ui')
    ui.dock()
