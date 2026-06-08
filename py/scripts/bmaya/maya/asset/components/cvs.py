"""Purpose:
The Cvs class is a component that is a json file containing the cv shape data for the controls on a rig.
It contains the logic for loading and saving cvs using the shapeio module, which handles the actual logic for saving and loading cv data.
"""

import os
from .component import Component
from bmaya.maya.rigging.shapes import shapeio


class Cvs(Component):

    def __init__(self, asset, component_type):
        super(Cvs, self).__init__(asset, component_type)

    @property
    def relative_path(self):
        # /rig/components/cvs.json
        return os.path.join("rig", "components", self.type + self.extension)

    def load(self):
        shapeio.load(self.full_path)

    def save(self):
        shapeio.save(self.full_path)
