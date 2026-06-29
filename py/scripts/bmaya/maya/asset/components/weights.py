"""Purpose:
The Weights component is a folder that contains the skin weight files for a rig.
These live in .weights files in the rig/components/weights folder and are saved and loaded using the weightio module,
which handles the actual logic for saving and loading weight data.
"""

import os
from .component import Component, ComponentType
from bmaya.maya.rigging.weights import weightio


class Weights(Component):

    def __init__(self, asset):
        super(Weights, self).__init__(asset, ComponentType.Weights)

    @property
    def relative_path(self):
        # /rig/components/weights/
        return os.path.join("rig", "components", self.type)

    @property
    def files(self):
        try:
            files = os.listdir(self.full_path)
        except WindowsError:
            files = []

        return files

    def load(self):
        for f in self.files:
            weightio.load(os.path.join(self.full_path, f))

    def save(self):
        weightio.save(self.full_path)
