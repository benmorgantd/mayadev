"""Purpose:
Class for the FacePoses component, which is a maya file that contains an animation of poses.
An animator can hand-animate each pose on the rig and save these off.
"""

import os
from .component import ComponentType
from .mayaComponent import MayaComponent


class FacePoses(MayaComponent):

    def __init__(self, asset):
        super(FacePoses, self).__init__(asset, ComponentType.FacePoses)

    @property
    def relative_path(self):
        return os.path.join("rig", "components", self.type + self.extension)
