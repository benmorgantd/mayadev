"""Purpose:
Base class for production Animation Rigs that handles logic for asset Id, file management, and versioning.
Animation Rigs are a type of Maya Component, meaning they are specific to Maya.
"""

import os
from .mayaComponent import MayaComponent

class AnimRig(MayaComponent):

    def __init__(self, asset, componentType):
        super(AnimRig, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/animRig.ma
        return os.path.join('rig', self.type + self.extension)

