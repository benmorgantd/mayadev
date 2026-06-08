"""Purpose:
A MayaComponent is a type of Component that is specific to Maya.
It contains the file handling logic for components that are Maya files.
"""

import os
from .component import Component

import maya.cmds as cmds
import maya.api.OpenMaya as om

from bmaya.core.util import fileUtils


class MayaComponent(Component):
    def __init__(self, asset, component_type):
        super(MayaComponent, self).__init__(asset, component_type)

    def save(self):
        om.MGlobal.displayInfo('Saving ' + self.type + ' ...')
        fileUtils.version_file(self.full_path)
        cmds.file(rename=self.full_path)
        cmds.file(save=True, type="mayaAscii", force=True)

    def load(self):
        cmds.file(self.full_path, open=True, force=True)

    def reference(self):
        cmds.file(
            self.full_path,
            reference=True,
            namespace=os.path.splitext(
                os.path.basename(
                    self.full_path))[0])
