import os
from component import Component

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
            

