"""Purpose:
The Mesh class is a MayaComponent that contains the model for an Asset.
"""

import os
from .component import ComponentType
from .mayaComponent import MayaComponent


class Mesh(MayaComponent):

    def __init__(self, asset):
        super(Mesh, self).__init__(asset, ComponentType.Mesh)

    @property
    def relative_path(self):
        # /mesh/mesh.ma
        return os.path.join(self.type, self.type + self.extension)
