import os

TYPE_EXTENSIONS = {'mesh': '.ma',
                   'skeleton': '.ma',
                   'cvs': '.json', 
                   'animRig': '.ma', 
                   'weights': '.weights', 
                   'build':'.json', 
                   'components':'',
                   'postops':'.py',
                   'facePoses':'.json'}

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

