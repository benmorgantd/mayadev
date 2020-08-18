import os
from component import Component

class PostOps(Component):

    def __init__(self, asset, componentType):
        super(PostOps, self).__init__(asset, componentType)

    @property
    def relativePath(self):
        # /rig/components/postops.py
        return os.path.join('rig', 'components', self.type + self.extension)
