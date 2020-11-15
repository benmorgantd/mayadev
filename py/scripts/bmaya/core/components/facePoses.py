import os
from component import Component

class FacePoses(Component):

    def __init__(self, asset, componentType):
        super(FacePoses, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/cvs.json
        return os.path.join('rig', 'components', self.type + self.extension)
