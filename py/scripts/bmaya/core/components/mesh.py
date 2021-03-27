import os
from mayaComponent import MayaComponent


class Mesh(MayaComponent):

    def __init__(self, asset, componentType):
        super(Mesh, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /mesh/mesh.ma
        return os.path.join(self.type, self.type + self.extension)

