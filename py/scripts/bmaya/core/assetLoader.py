import os

from bmaya.lib.Qt import QtWidgets, QtGui, QtCore, QtCompat
from . import qtbase, asset


class AssetLoader(qtbase.SimpleWindow):
    def __init__(self, parent=None):
        super(AssetLoader, self).__init__(parent)
        
        self.setWindowTitle('Asset Loader')
        self.setFixedSize(300,200)
        
        self.addWidgets()
        self.connectWidgets()

    @property
    def project(self):
        return self.projectCombo.currentText()
    
    @property
    def assetType(self):
        return self.typeCombo.currentText()

    @property
    def assetName(self):
        return self.nameCombo.currentText()    
    
    def addWidgets(self):

        self.setupProject()
        self.setupAssetTypes()
        self.setupAssetNames()

        self.loadBtn = QtWidgets.QPushButton('Load')
        self.mainLayout.addWidget(self.loadBtn)

    def setupProject(self):
        self.mainLayout.addWidget(QtWidgets.QLabel('Project'))
        self.projectCombo = QtWidgets.QComboBox()
        self.mainLayout.addWidget(self.projectCombo)

        availableProjects = os.listdir(asset.PROJECT_DIR)

        for project in availableProjects:
            self.projectCombo.addItem(project)
        
    def setupAssetTypes(self):
        self.mainLayout.addWidget(QtWidgets.QLabel('Type'))
        self.typeCombo = QtWidgets.QComboBox()
        self.mainLayout.addWidget(self.typeCombo)

        self.updateTypeCombo()

    def setupAssetNames(self):
        self.mainLayout.addWidget(QtWidgets.QLabel('Name'))
        self.nameCombo = QtWidgets.QComboBox()
        self.mainLayout.addWidget(self.nameCombo)

        self.updateNameCombo()

    def updateTypeCombo(self):
        availableAssetTypes = os.listdir(os.path.join(asset.PROJECT_DIR, self.project))

        self.typeCombo.clear()

        for assetType in availableAssetTypes:
            self.typeCombo.addItem(assetType)

    def updateNameCombo(self):
        availableAssets = os.listdir(os.path.join(asset.PROJECT_DIR, self.project, self.assetType))

        self.nameCombo.clear()

        for assetName in availableAssets:
            self.nameCombo.addItem(assetName)

    def connectWidgets(self):
        self.projectCombo.currentIndexChanged.connect(self.updateTypeCombo)
        self.typeCombo.currentIndexChanged.connect(self.updateNameCombo)
