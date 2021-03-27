import os
from mayaComponent import MayaComponent


class FacePoses(MayaComponent):

    def __init__(self, asset, componentType):
        super(FacePoses, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/cvs.json
        return os.path.join('rig', 'components', self.type + self.extension)
