"""Purpose:
Base class for production Components that handles logic for asset Id, file management, and versioning.
Components are the individual files that make up an asset.
Contains the type extensions for each component type, as well as the base class for all components.
Also handles the unimplemented logic for loading and saving and referencing, which must be defined by each specific component type.
"""

import os
from enum import Enum

# TODO: these are all mainly maya-specific component types and should be under MayaComponent
class ComponentType(Enum):
    Mesh = 'mesh'
    Skeleton = 'skeleton'
    Cvs = 'cvs'
    AnimRig = 'animRig'
    Weights = 'weights'
    Build = 'build'
    Components = 'components'
    PostOps = 'postops'
    FacePoses = 'facePoses'

TYPE_EXTENSIONS = {
    ComponentType.Mesh: ".ma",
    ComponentType.Skeleton: ".ma",
    ComponentType.Cvs: ".json",
    ComponentType.AnimRig: ".ma",
    ComponentType.Weights: ".json",
    ComponentType.Build: ".json",
    ComponentType.Components: "",
    ComponentType.PostOps: ".py",
    ComponentType.FacePoses: ".json",
}


class Component(object):

    def __init__(self, asset, component_type):
        # gather the info it needs about its filepaths from the asset
        self.asset = asset

        if component_type in TYPE_EXTENSIONS.keys():
            self._component_type = component_type
        else:
            raise RuntimeError(
                "Given component type <{}> invalid.".format(component_type)
            )

    @property
    def type(self):
        return self._component_type.value

    @property
    def extension(self):
        return TYPE_EXTENSIONS[self._component_type]

    @property
    def relative_path(self):
        # /rig/components
        return os.path.join("rig", "components")

    @property
    def full_path(self):
        return os.path.join(self.asset.root_dir, self.relative_path)

    def save(self):
        raise NotImplementedError()

    def load(self):
        raise NotImplementedError()

    def reference(self):
        raise NotImplementedError()
