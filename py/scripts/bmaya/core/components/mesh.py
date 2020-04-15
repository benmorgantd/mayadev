import os
from component import Component

class Mesh(Component):

    def __init__(self, asset, componentType):
        super(Mesh, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /mesh/mesh.ma
        return os.path.join(self.type, self.type + self.extension)