"""Maya save and load handlers for asset file types (bmaya.asset.handlers).

Only formats that exist get a handler: Maya scenes and RigModules shape files. Other file types
(weights, textures, shaders, postops, poses, anims) have none yet, so saving or loading them raises
NotImplementedError until one is written.

Call register() once per session before handlers.save / handlers.load.

    from bmaya.asset import Asset, handlers
    from bmaya.maya import assethandlers

    assethandlers.register()
    hero = Asset("shooter|main|characters|hero")
    handlers.load(hero, "skeleton")                                  # imports into the hero namespace
    handlers.save(hero, "shapes", variant="game", rig_root="hero:rigRootModule1")
"""

from __future__ import annotations

import maya.cmds as cmds

from bmaya.asset import handlers
from bmaya.asset.asset import Asset

MAYA_FILE_TYPES = ("skeleton", "model", "rig")


class MayaSceneHandler(handlers.FileHandler):
    """A Maya ASCII scene. Load imports it, never references it: files import into the asset's namespace
    so they keep working after the source changes (D29)."""

    def save(self, asset: Asset, path: str, **context) -> None:
        """Saves the open scene as path, as the legacy components did. The scene is renamed to path."""
        cmds.file(rename=path)
        cmds.file(save=True, type="mayaAscii", force=True)

    def load(self, asset: Asset, path: str, namespace: str | None = None, **context) -> list[str]:
        """Imports path into namespace (the asset's name unless given), merging into it if it exists,
        because the asset owns one namespace per instance. Returns the new nodes."""
        return cmds.file(
            path,
            i=True,
            type="mayaAscii",
            namespace=namespace or asset.name,
            mergeNamespacesOnClash=True,
            returnNewNodes=True,
        ) or []


class RigShapesHandler(handlers.FileHandler):
    """A RigModules control shape file, through its own commands. Needs the rig root."""

    def save(self, asset: Asset, path: str, rig_root: str | None = None, **context) -> None:
        cmds.saveRigControlShapes(_require_rig_root(rig_root), file=path)

    def load(self, asset: Asset, path: str, rig_root: str | None = None, **context) -> list[str]:
        return cmds.loadRigControlShapes(_require_rig_root(rig_root), file=path) or []


def _require_rig_root(rig_root: str | None) -> str:
    if not rig_root:
        raise ValueError("Shape files belong to one rig: pass rig_root, the rigRootModule node.")
    return rig_root


def register() -> None:
    scene = MayaSceneHandler()
    for file_type in MAYA_FILE_TYPES:
        handlers.register(file_type, scene)
    handlers.register("shapes", RigShapesHandler())
