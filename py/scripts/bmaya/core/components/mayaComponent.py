import os
from component import Component

import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.core import fileio


class MayaComponent(Component):
    def __init__(self, asset, componentType):
        super(MayaComponent, self).__init__(asset, componentType)

    def save(self):
        om.MGlobal.displayInfo('Saving ' + self.type + ' ...')
        fileio.versionFile(self.fullPath)
        cmds.file(rename=self.fullPath)
        cmds.file(save=True, type="mayaAscii", force=True)

    def load(self):
        cmds.file(self.fullPath, open=True, force=True)

    def reference(self):
        cmds.file(self.fullPath, reference=True, namespace=os.path.splitext(os.path.basename(self.fullPath))[0])
