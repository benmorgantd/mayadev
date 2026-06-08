"""Purpose:
Class for the Build component, which is a json file that contains the rig structure.
"""

import os
from .component import Component


class Build(Component):

    def __init__(self, asset, componentType):
        super(Build, self).__init__(asset, componentType)

    @property
    def relative_path(self):
        # /rig/components/animRig.ma
        return os.path.join('rig', 'components', self.type + self.extension)
