import os
from component import Component
from bmaya.rigging.shapes import shapeio


class Cvs(Component):

    def __init__(self, asset, componentType):
        super(Cvs, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/cvs.json
        return os.path.join('rig', 'components', self.type + self.extension)

    def load(self):
        shapeio.load(self.fullPath)

    def save(self):
        shapeio.save(self.fullPath)