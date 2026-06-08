"""Purpose:
The PostOps component is a python file that allows the user to run custom logic on a rig after it is built.
"""

import os
from .component import Component


class PostOps(Component):

    def __init__(self, asset, component_type):
        super(PostOps, self).__init__(asset, component_type)

    @property
    def relative_path(self):
        # /rig/components/postops.py
        return os.path.join('rig', 'components', self.type + self.extension)
