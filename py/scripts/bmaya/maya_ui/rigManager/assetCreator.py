"""Asset creator for initiating new assets"""

from PySide6 import QtWidgets

from bmaya.core import log
from bmaya.maya.rigging.base import rig
from bmaya.maya.asset import asset


class AssetCreator(QtWidgets.QMainWindow):
    def __init__(self, parent=None, title="AssetCreator"):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(480, 159)

        # Main Central Widget and Layout
        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.main_layout = QtWidgets.QVBoxLayout(self.centralwidget)

        # Asset Attributes Group
        self.attr_group = QtWidgets.QGroupBox("Asset Attributes")
        self.attr_layout = QtWidgets.QHBoxLayout(self.attr_group)

        # Project Group & LineEdit
        self.project_group = QtWidgets.QGroupBox("Project")
        self.project_layout = QtWidgets.QHBoxLayout(self.project_group)
        self.projectName = QtWidgets.QLineEdit()
        self.project_layout.addWidget(self.projectName)
        self.attr_layout.addWidget(self.project_group)

        # Type Group & LineEdit
        self.type_group = QtWidgets.QGroupBox("Type")
        self.type_layout = QtWidgets.QHBoxLayout(self.type_group)
        self.assetType = QtWidgets.QLineEdit()
        self.type_layout.addWidget(self.assetType)
        self.attr_layout.addWidget(self.type_group)

        # Name Group & LineEdit
        self.name_group = QtWidgets.QGroupBox("Name")
        self.name_layout = QtWidgets.QHBoxLayout(self.name_group)
        self.assetName = QtWidgets.QLineEdit()
        self.name_layout.addWidget(self.assetName)
        self.attr_layout.addWidget(self.name_group)

        # Add the main attribute group to the vertical layout
        self.main_layout.addWidget(self.attr_group)

        # Create Asset Button
        self.createAssetBtn = QtWidgets.QPushButton("Create Asset")
        self.main_layout.addWidget(self.createAssetBtn)

        # Connections
        self.createAssetBtn.clicked.connect(self.createAsset)

    def createAsset(self):
        project = self.projectName.text().strip()
        asset_type = self.assetType.text().strip()
        name = self.assetName.text().strip()

        asset_id = "|".join([project, asset_type, name])

        assetPath = asset.Asset.exists(project, name, asset_type)

        if assetPath:
            log.info("An asset of this description already exists")
            return
        else:
            rig.Rig(asset_id)
            self.close()


def show_asset_creator():
    window = AssetCreator(parent=None)
    window.show()
    return window
