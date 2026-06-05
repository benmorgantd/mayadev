"""Purpose:
Class for the FacePoses component, which is a maya file that contains an animation of poses.
An animator can hand-animate each pose on the rig and save these off.
"""
import os
from .mayaComponent import MayaComponent


class FacePoses(MayaComponent):

    def __init__(self, asset, componentType):
        super(FacePoses, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        return os.path.join('rig', 'components', self.type + self.extension)
