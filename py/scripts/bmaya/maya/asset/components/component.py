"""Purpose:
Base class for production Components that handles logic for asset Id, file management, and versioning.
Components are the individual files that make up an asset. 
Contains the type extensions for each component type, as well as the base class for all components.
Also handles the unimplemented logic for loading and saving and referencing, which must be defined by each specific component type.
"""

import os

TYPE_EXTENSIONS = {'mesh'       : '.ma',
                   'skeleton'   : '.ma',
                   'cvs'        : '.json', 
                   'animRig'    : '.ma', 
                   'weights'    : '.weights', 
                   'build'      : '.json', 
                   'components' : '',
                   'postops'    : '.py',
                   'facePoses'  : '.json'}

class Component(object):

    def __init__(self, asset, componentType):
        # gather the info it needs about its filepaths from the asset
        self.asset = asset

        if componentType in TYPE_EXTENSIONS.keys():
            self._componentType = componentType
        else:
            raise RuntimeError('Given component type <{}> invalid.'.format(componentType))
    
    @property
    def type(self):
        return self._componentType

    @property
    def extension(self):
        return TYPE_EXTENSIONS[self.type]

    @property
    def relativePath(self):
        # /rig/components
        return os.path.join('rig', 'components')

    @property
    def fullPath(self):
        return os.path.join(self.asset.rootDir, self.relativePath)

    def save(self):
        raise NotImplementedError()

    def load(self):
        raise NotImplementedError()

    def reference(self):
        raise NotImplementedError()

