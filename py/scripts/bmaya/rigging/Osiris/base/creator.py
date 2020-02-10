"""Creator is used to initiate and build assets."""

from . import character
#reload(character)
from decorators import wrapStandalone

__all__ = ['initiate', 'build']


def initiate(name, project, assetType, standalone=True):
    
    @wrapStandalone
    def withStandalone(name, project, assetType):
        asset = character.Character(name, project, assetType)
        return asset

    if standalone:
        asset = withStandalone(name, project, assetType)
    else:
        asset = character.Character(name, project, assetType)

    return asset


def build(asset, standalone=True):

    @wrapStandalone
    def withStandalone(asset):
        asset.buildRig()
    if standalone:
        withStandalone(asset)
    else:
        asset.buildRig()

    





