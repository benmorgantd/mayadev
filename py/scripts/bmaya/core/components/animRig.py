import os
from .mayaComponent import MayaComponent

class AnimRig(MayaComponent):

    def __init__(self, asset, componentType):
        super(AnimRig, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/animRig.ma
        return os.path.join('rig', self.type + self.extension)

