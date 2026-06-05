"""Purpose:
The Weights component is a folder that contains the skin weight files for a rig.
These live in .weights files in the rig/components/weights folder and are saved and loaded using the weightio module, 
which handles the actual logic for saving and loading weight data.
"""

import os
from .component import Component
from bmaya.maya.rigging.weights import weightio


class Weights(Component):

    def __init__(self, asset, componentType):
        super(Weights, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/weights/
        return os.path.join('rig', 'components', self.type)

    @property
    def files(self):
        try:
            files = os.listdir(self.fullPath)
        except WindowsError:
            files = []

        return files

    def load(self):
        for f in self.files:
            weightio.load(os.path.join(self.fullPath, f))

    def save(self):
        weightio.save(self.fullPath)