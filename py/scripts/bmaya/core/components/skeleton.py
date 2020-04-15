import os
from component import Component

class Skeleton(Component):

    def __init__(self, asset, componentType):
        super(Skeleton, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/skeleton.ma
        return os.path.join('rig', 'components', self.type + self.extension)

    
