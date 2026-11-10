"""Maya save and load handlers for asset file types (bmaya.asset.handlers).

Only formats that exist get a handler: Maya scenes, RigModules templates, shape files and skin weights.
Other file types (textures, shaders, postops, poses, anims) have none yet, so saving or loading them
raises NotImplementedError until one is written.

Call register() once per session before handlers.save / handlers.load.

    from bmaya.asset import Asset, handlers
    from bmaya.maya import assethandlers

    assethandlers.register()
    hero = Asset("shooter|main|characters|hero")
    handlers.load(hero, "skeleton")                                  # imports into the hero namespace
    handlers.save(hero, "shapes", variant="game", rig_root="hero:rigRootModule1")
    handlers.save(hero, "weights", variant="game", namespace="hero")
"""

from __future__ import annotations

import glob
import os
import shutil

import maya.cmds as cmds
import rigmodules.skinweights
import rigmodules.template

import bmaya.core.log

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


class RigTemplateHandler(handlers.FileHandler):
    """A RigModules rig template. Saving one is what makes a variant: the variant is the folder that holds it
    (RigModules D29, D30)."""

    def save(self, asset: Asset, path: str, variant: str | None = None, source: str | None = None, **context) -> None:
        """Copies the template file at source. Its rigName must be the variant, because rigs built from it
        are found by rigName."""
        if not source:
            raise ValueError("Pass source, the template file to copy into the asset.")
        rig_name = rigmodules.template.get_rig_name(source)
        if rig_name != variant:
            raise ValueError(f"{source} has rigName {rig_name!r}, but the variant is {variant!r}.")
        shutil.copyfile(source, path)

    def load(self, asset: Asset, path: str, **context) -> str:
        """The template's path, for cmds.createRigFromTemplate(template=...)."""
        return path


class RigSkinWeightsHandler(handlers.FileHandler):
    """A variant's skin weights: a folder with one RigModules weight file per skinned mesh, named after the mesh.
    Files are matched to meshes by the meshId inside them, never by name, so a renamed mesh still loads. Needs
    the namespace the meshes are in."""

    @staticmethod
    def files(folder: str) -> list[str]:
        """The weight files in a weights folder, sorted."""
        return sorted(glob.glob(os.path.join(folder, "*.json")))

    def save(self, asset: Asset | None, path: str, namespace: str | None = None, **context) -> list[str]:
        """Saves every skinned mesh in namespace into the folder at path. Returns the files written. A file left
        from a mesh's old name is removed (handlers.save has already kept a version copy of the folder)."""
        namespace = _require_namespace(namespace)
        meshes = rigmodules.skinweights.get_skinned_meshes(namespace)
        if not meshes:
            raise RuntimeError(f"Namespace {namespace!r} has no skinned meshes.")
        unmarked = [mesh for mesh in meshes if not rigmodules.skinweights.get_mesh_id(mesh)]
        if unmarked:
            raise RuntimeError("These meshes have no meshId. Run Mark Meshes for Skinning on them first: "
                               + ", ".join(_short_name(mesh) for mesh in unmarked))

        os.makedirs(path, exist_ok=True)
        written = {}
        for mesh in meshes:
            file_path = os.path.join(path, _short_name(mesh) + ".json")
            cmds.saveRigSkinWeights(mesh, file=file_path.replace("\\", "/"))
            written[rigmodules.skinweights.get_mesh_id(mesh)] = os.path.normcase(file_path)
        for stale in self.files(path):
            if os.path.normcase(stale) not in written.values() and rigmodules.skinweights.read_file_mesh_id(stale) in written:
                os.remove(stale)
        return sorted(written.values())

    def load(self, asset: Asset | None, path: str, namespace: str | None = None, **context) -> list[str]:
        """Loads every weight file in the folder at path onto the mesh in namespace with its meshId, as one undo
        step. A file whose mesh isn't in the scene is skipped with a warning. Returns the meshes loaded."""
        namespace = _require_namespace(namespace)
        files: dict[str, str] = {}
        for file_path in self.files(path):
            mesh_id = rigmodules.skinweights.read_file_mesh_id(file_path)
            if mesh_id in files:
                raise RuntimeError(f"{files[mesh_id]} and {file_path} are both for meshId {mesh_id}. Remove the old one.")
            files[mesh_id] = file_path
        meshes = rigmodules.skinweights.get_meshes(namespace)

        loaded = []
        cmds.undoInfo(openChunk=True, chunkName="Load Skin Weights")
        try:
            for mesh_id, file_path in sorted(files.items(), key=lambda item: item[1]):
                mesh = meshes.get(mesh_id)
                if mesh is None:
                    bmaya.core.log.warning(f"No mesh in namespace {namespace!r} has meshId {mesh_id}: skipped {file_path}")
                    continue
                cmds.loadRigSkinWeights(mesh, file=file_path.replace("\\", "/"))
                loaded.append(mesh)
        finally:
            cmds.undoInfo(closeChunk=True)
        return loaded


def _short_name(node: str) -> str:
    return node.split("|")[-1].split(":")[-1]


def _require_namespace(namespace: str | None) -> str:
    if namespace is None:
        raise ValueError("Skin weights belong to the meshes in one namespace: pass namespace.")
    return namespace


def _require_rig_root(rig_root: str | None) -> str:
    if not rig_root:
        raise ValueError("Shape files belong to one rig: pass rig_root, the rigRootModule node.")
    return rig_root


def register() -> None:
    scene = MayaSceneHandler()
    for file_type in MAYA_FILE_TYPES:
        handlers.register(file_type, scene)
    handlers.register("shapes", RigShapesHandler())
    handlers.register("weights", RigSkinWeightsHandler())
    handlers.register("template", RigTemplateHandler())
