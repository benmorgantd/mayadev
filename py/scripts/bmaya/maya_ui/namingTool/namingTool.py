from PySide6 import QtWidgets
from bmaya.maya_ui import qtbase


class NamingTool(qtbase.SimpleWindow):
    def __init__(self, parent=None, title="Naming Tool"):
        super(NamingTool, self).__init__(parent=parent, title=title)

        self.resize(240, 130)
        self.setMaximumSize(240, 130)
        self.setMinimumSize(240, 130)
        self._addWidgets()

    def _addWidgets(self):

        self.nameText = QtWidgets.QLineEdit()
        self.nameText.setPlaceholderText("name")
        self.mainLayout.addWidget(self.nameText)

        self.sideBox = QtWidgets.QComboBox()
        self.sideBox.addItems(
            [
                constants.SIDE_NAMES["left"],
                constants.SIDE_NAMES["right"],
                constants.SIDE_NAMES["middle"],
            ]
        )
        self.mainLayout.addWidget(self.sideBox)

        self.typeBox = QtWidgets.QComboBox()
        self.typeBox.addItems(
            [constants.JOINT_SUFFIX, constants.MESH_SUFFIX, constants.CTRL_SUFFIX]
        )
        self.mainLayout.addWidget(self.typeBox)

        self.renameBtn = QtWidgets.QPushButton("Rename")
        self.renameBtn.setStyleSheet("background-color:orange;color:black")
        self.mainLayout.addWidget(self.renameBtn)

        self.renameBtn.clicked.connect(lambda: self.doRename())

    def doRename(self):
        nameText = self.nameText.text()
        typeText = self.typeBox.currentText()
        sideText = self.sideBox.currentText()

        nameSelection(
            cmds.ls(selection=True), name=nameText, side=sideText, suffix=typeText
        )


def run():
    ui = NamingTool(parent=qtbase.getMayaMainWindow())
    ui.show()
