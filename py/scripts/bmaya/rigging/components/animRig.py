import os
from component import Component

class AnimRig(Component):

    def __init__(self, asset, componentType):
        super(AnimRig, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/animRig.ma
        return os.path.join('rig', self.type + self.extension)


    
