import os
from component import Component

class Locators(Component):

    def __init__(self, asset, componentType):
        super(Locators, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/locators.ma
        return os.path.join('rig', 'components', self.type + self.extension)
