"""Asset creator for initiating new assets"""

import os

import maya.api.OpenMaya as om

from bmaya.lib.Qt import QtWidgets, QtCompat

from bmaya.maya.rigging.base import rig
from bmaya.core import asset


class AssetCreator(QtWidgets.QMainWindow):
    def __init__(self, parent=None, designerFile=None, title='Asset Creator'):
        super(AssetCreator, self).__init__(parent)

        if designerFile and isinstance(designerFile, str):
            designPath = os.path.join(os.path.dirname(__file__), designerFile)
            if os.path.exists(designPath):
                self.widget = QtCompat.load_ui(designPath)
                self.setCentralWidget(self.widget)
            else:
                raise RuntimeError('Given Qt Designer file not in folder.')

        self.setWindowTitle(title)

        self.widget.createAsset.clicked.connect(lambda: self.createAsset())

        self.resize(400, 150)

    def createAsset(self):
        project = self.widget.projectnameUtils.text().strip()
        assetType = self.widget.assetType.text().strip()
        name = self.widget.assetnameUtils.text().strip()

        asset_id = '|'.join([project, assetType, name])

        assetPath = asset.Asset.exists(project, name, assetType)

        if assetPath:
            om.MGlobal.displayInfo(
                'An asset of this description already exists')
            return
        else:
            rig.Rig(asset_id)

            self.close()
