"""Purpose:
Base class for production Animation Rigs that handles logic for asset Id, file management, and versioning.
Animation Rigs are a type of Maya Component, meaning they are specific to Maya.
"""

import os
from .component import ComponentType
from .mayaComponent import MayaComponent


class AnimRig(MayaComponent):

    def __init__(self, asset):
        super(AnimRig, self).__init__(asset, ComponentType.AnimRig)

    @property
    def relative_path(self):
        # /rig/animRig.ma
        return os.path.join("rig", self.type + self.extension)
