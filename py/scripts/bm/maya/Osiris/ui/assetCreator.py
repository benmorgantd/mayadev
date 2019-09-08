"""Asset creator for initiating new assets"""

import os

import maya.OpenMaya as om

from lib.Qt import QtWidgets, QtCompat

from ..base import creator
# reload(creator)
from ..base import asset
# reload(asset)


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
        project = self.widget.projectName.text()
        name = self.widget.assetName.text()
        assetType = self.widget.assetType.text()

        # todo: parse these values

        assetPath = asset.Asset.exists(project, name, assetType)

        if assetPath:
            om.MGlobal.displayInfo('An asset of this description already exists')
        else:
            assetInstance = creator.initiate(name, project, assetType,
                                             standalone=False)

            if self.rigBuilder:
                self.rigBuilder.loadBuild(assetInstance.getComponentPath('build'))

            return assetInstance

        # todo: now refresh the dropdown lists in rigBuilder