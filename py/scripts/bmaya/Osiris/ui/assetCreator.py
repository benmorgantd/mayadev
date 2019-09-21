"""Asset creator for initiating new assets"""

import os

import maya.OpenMaya as om

from lib.Qt import QtWidgets, QtCompat

from ..base import creator
reload(creator)
from bmaya import asset
reload(asset)


class AssetCreator(QtWidgets.QMainWindow):
    def __init__(self, parent=None, designerFile=None, title='Asset Creator', rigBuilder=None):
        super(AssetCreator, self).__init__(parent)

        if designerFile and isinstance(designerFile, basestring):
            designPath = os.path.join(os.path.dirname(__file__), designerFile)
            if os.path.exists(designPath):
                self.widget = QtCompat.load_ui(designPath)
                self.setCentralWidget(self.widget)
            else:
                raise RuntimeError('Given Qt Designer file not in folder.')

        self.setWindowTitle(title)

        self.rigBuilder = rigBuilder

        self.widget.createAsset.clicked.connect(lambda: self.createAsset())

        self.resize(400, 150)

    def createAsset(self):
        project = self.widget.projectName.text().strip().lower()
        assetType = self.widget.assetType.text().strip().lower()
        name = self.widget.assetName.text().strip().lower()

        assetPath = asset.Asset.exists(project, name, assetType)

        if assetPath:
            om.MGlobal.displayInfo('An asset of this description already exists')
            return
        else:
            self.rigBuilder.assetInstance = creator.initiate(name, project, assetType,
                                             standalone=False)

            if self.rigBuilder:
                self.rigBuilder.loadBuild(self.rigBuilder.assetInstance.build.fullPath)
                self.rigBuilder.resetAssetBoxes()
                self.rigBuilder.buildList.reset()

                self.rigBuilder.widget.loadComponent.setEnabled(True)
                self.rigBuilder.widget.saveComponent.setEnabled(True)
                self.rigBuilder.widget.build.setEnabled(True)

                projectindex = self.rigBuilder.widget.projectName.findText(project)
                self.rigBuilder.widget.projectName.setCurrentIndex(projectindex)

                typeindex = self.rigBuilder.widget.assetType.findText(assetType)
                self.rigBuilder.widget.assetType.setCurrentIndex(typeindex)

                nameindex = self.rigBuilder.widget.assetName.findText(name)
                self.rigBuilder.widget.assetName.setCurrentIndex(nameindex)
            
            self.close()
