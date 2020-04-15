import maya.cmds as cmds
import maya.OpenMaya as om

import constants

def nameSelection(selection, name='joint', side='L', suffix='JNT'):
    
    if not selection:
        return
    
    selLen = len(selection)
    
    for i in range(selLen -1, -1, -1):
        newName = '_'.join([name, str(i).zfill(2), side, suffix])
        
        if cmds.objExists(newName) and newName not in selection:
            om.MGlobal.displayWarning('An object with the name \'{0}\' already exists'.format(newName))
        
        cmds.rename(selection[i], newName)

def findControlName(node, identifier=None):
        nodeSplit = node.split('_')
        if identifier:
            nodeSplit[0] += identifier

        ctrlName = '_'.join(nodeSplit[0:-1])
        
        ctrlName = '_'.join([ctrlName, constants.CTRL_SUFFIX])

        return ctrlName

def findJointName(node, identifier=None, count=0, suffix='DRIVER'):
    nodeSplit = node.split('_')
    if identifier:
        nodeSplit[0] += identifier
    if isinstance(count, int):
        nodeSplit[1] = str(count).zfill(2)
    
    jntName = '_'.join(nodeSplit[0:-1])

    suffix = suffix.replace('_', '')
    
    jntName = jntName + '_' + suffix

    return jntName


from bmaya.lib.Qt import QtWidgets
from bmaya.core import qtbase

class NamingTool(qtbase.SimpleWindow):
    def __init__(self, parent=None, title='Naming Tool'):
        super(NamingTool, self).__init__(parent=parent, title=title)

        self.resize(240,130)
        self.setMaximumSize(240, 130)
        self.setMinimumSize(240, 130)
        self._addWidgets()

    def _addWidgets(self):

        self.nameText = QtWidgets.QLineEdit()
        self.nameText.setPlaceholderText('name')
        self.mainLayout.addWidget(self.nameText)

        self.sideBox = QtWidgets.QComboBox()
        self.sideBox.addItems([constants.SIDE_NAMES['left'],
                              constants.SIDE_NAMES['right'],
                              constants.SIDE_NAMES['middle']])
        self.mainLayout.addWidget(self.sideBox)
        
        self.typeBox = QtWidgets.QComboBox()
        self.typeBox.addItems([constants.JOINT_SUFFIX, constants.MESH_SUFFIX, constants.CTRL_SUFFIX])
        self.mainLayout.addWidget(self.typeBox)

        self.renameBtn = QtWidgets.QPushButton('Rename')
        self.renameBtn.setStyleSheet('background-color:orange;color:black')
        self.mainLayout.addWidget(self.renameBtn)

        self.renameBtn.clicked.connect(lambda:self.doRename())

    def doRename(self):
        nameText = self.nameText.text()
        typeText = self.typeBox.currentText()
        sideText = self.sideBox.currentText()

        nameSelection(cmds.ls(selection=True), 
                              name=nameText,
                              side=sideText, 
                              suffix=typeText)

def run():
    ui = NamingTool(parent=qtbase.getMayaMainWindow())
    ui.show()