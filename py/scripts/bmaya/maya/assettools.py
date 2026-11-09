"""Asset tools for RigModules rigs, behind the RigModules menu (RigModules D30).

A rig can be built anywhere, before its asset exists. Once the asset's folder exists, these tools read and
write the asset's files. A built rig names its own asset id and variant (the rig root's rigName), read
through rigmodules.query. Nothing here walks rig nodes or parses names (RigModules D24).

The shape and rig save tools fall back to a file dialog for a rig whose asset folder doesn't exist yet.
Once it exists, they always use the asset's paths, so a file never lands in two places.

The functions at the top take everything as arguments, so batch jobs and other tools can call them. The
*_ui functions below act on the active rig (bmaya.maya.activerig), ask with dialogs, and call them.
"""

from __future__ import annotations

import os

import maya.cmds as cmds
import rigmodules.query
import rigmodules.template

import bmaya.asset
import bmaya.asset.handlers
import bmaya.core.log
import bmaya.maya.activerig
import bmaya.maya.assethandlers

SCENE_FILTER = "Maya ASCII (*.ma)"
SHAPES_FILTER = "Shape files (*.json)"
TEMPLATE_FILTER = "Rig templates (*.json)"


def find_asset(asset_id: str) -> bmaya.asset.Asset | None:
    """The asset when its folder holds an asset.json, else None. None too, with a warning, when there is no
    projects root to look in."""
    try:
        asset = bmaya.asset.Asset(asset_id)
    except bmaya.asset.ProjectError as error:
        bmaya.core.log.warning(str(error))
        return None
    return asset if asset.exists() else None


def require_asset(asset_id: str) -> bmaya.asset.Asset:
    asset = bmaya.asset.Asset(asset_id)
    if not asset.exists():
        raise bmaya.asset.AssetError(f"{asset.id} has no asset.json at {asset.folder}. Create it with New Asset first.")
    return asset


def new_variant(asset_id: str, template_path: str) -> str:
    """Copies a template into the asset as a new variant, named by the template's rigName. Returns the variant."""
    asset = require_asset(asset_id)
    variant = rigmodules.template.get_rig_name(template_path)
    if asset.file_exists("template", variant):
        raise bmaya.asset.AssetError(f"{asset.id} already has variant {variant!r}: {asset.path('template', variant)}")
    bmaya.maya.assethandlers.register()
    path = bmaya.asset.handlers.save(asset, "template", variant, source=template_path)
    bmaya.core.log.info(f"Added variant {variant!r} to {asset.id}: {path}")
    return variant


def save_skeleton(asset_id: str) -> str:
    """Saves the open scene as the asset's skeleton file. The scene is renamed to that file."""
    asset = require_asset(asset_id)
    if not bmaya.asset.assetid.equals(asset.skeleton, asset.id):
        raise bmaya.asset.AssetError(f"{asset.id} uses the skeleton of {asset.skeleton}. Save the skeleton there.")
    bmaya.maya.assethandlers.register()
    path = bmaya.asset.handlers.save(asset, "skeleton")
    bmaya.core.log.info(f"Saved the skeleton of {asset.id}: {path}")
    return path


def build_rig(asset_id: str, variant: str, namespace: str | None = None) -> str:
    """Imports the asset's skeleton, builds the variant's template on it, and loads the variant's shape file
    when there is one. Builds into the open scene. Returns the rig root."""
    asset = require_asset(asset_id)
    bmaya.maya.assethandlers.register()
    template = bmaya.asset.handlers.load(asset, "template", variant)
    skeleton_asset = require_asset(asset.skeleton)
    namespace = namespace or asset.name
    # Variants share one skeleton, so a second variant in the namespace would need the joints already there,
    # not a second import. Until that is built, each build gets a namespace of its own.
    if rigmodules.query.get_rigs(namespace):
        raise RuntimeError(f"Namespace {namespace!r} already holds a rig. Build into a new scene or another namespace.")

    nodes = bmaya.asset.handlers.load(skeleton_asset, "skeleton", namespace=namespace)
    joints = cmds.ls(nodes, type="joint")
    if not joints:
        raise RuntimeError(f"The skeleton file of {skeleton_asset.id} has no joints.")
    cmds.createRigFromTemplate(*joints, template=template.replace("\\", "/"), asset=asset.id, namespace=namespace)

    rig_root = next(info.rig_root for info in rigmodules.query.get_rigs(namespace) if info.variant == variant)
    if asset.file_exists("shapes", variant):
        bmaya.asset.handlers.load(asset, "shapes", variant, rig_root=rig_root)
    bmaya.core.log.info(f"Built {asset.id} variant {variant!r} into namespace {namespace!r}.")
    return rig_root


def save_rig(node: str) -> str | None:
    """Saves the open scene as the rig file of the rig node's asset and variant. Without an asset folder, asks
    for a file. Returns the path, or None when the dialog is cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        path = _ask_file("Save Rig", SCENE_FILTER, save=True)
        if path:
            cmds.file(rename=path)
            cmds.file(save=True, type="mayaAscii", force=True)
        return path

    if info.variant not in asset.variants:
        raise bmaya.asset.AssetError(f"{asset.id} has no variant {info.variant!r}. Add its template with New Variant first.")
    bmaya.maya.assethandlers.register()
    path = bmaya.asset.handlers.save(asset, "rig", info.variant)
    bmaya.core.log.info(f"Saved {asset.id} variant {info.variant!r}: {path}")
    return path


def save_control_shapes(node: str) -> str | None:
    """Saves the rig's control shapes to its asset's shape file, or to a file chosen in a dialog when the asset
    folder doesn't exist. Returns the path, or None when the dialog is cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        path = _ask_file("Save Control Shapes", SHAPES_FILTER, save=True)
        if path:
            cmds.saveRigControlShapes(info.rig_root, file=path)
        return path

    bmaya.maya.assethandlers.register()
    path = bmaya.asset.handlers.save(asset, "shapes", info.variant, rig_root=info.rig_root)
    bmaya.core.log.info(f"Saved the control shapes of {asset.id} variant {info.variant!r}: {path}")
    return path


def load_control_shapes(node: str) -> str | None:
    """Loads the rig's control shapes from its asset's shape file, or from a file chosen in a dialog when the
    asset folder doesn't exist. Returns the path, or None when the dialog is cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        path = _ask_file("Load Control Shapes", SHAPES_FILTER, save=False)
        if path:
            cmds.loadRigControlShapes(info.rig_root, file=path)
        return path

    bmaya.maya.assethandlers.register()
    bmaya.asset.handlers.load(asset, "shapes", info.variant, rig_root=info.rig_root)
    return asset.path("shapes", info.variant)


# ---- menu entry points ---------------------------------------------------------------------

def new_project_ui() -> None:
    folder = _ask_folder("New Project: pick the project folder")
    if folder:
        project = bmaya.asset.Project.create(folder)
        bmaya.core.log.info(f"Created {project.root}")


def new_asset_ui() -> None:
    asset_id = _ask_asset_id("New Asset", "Asset id, its folder below the projects root (game|project|type|name):")
    if not asset_id:
        return
    project = bmaya.asset.Asset(asset_id).project   # raises when no project.json is above the folder
    asset_type = _choose("New Asset", f"Asset type of {asset_id}:", project.asset_types)
    if asset_type:
        asset = bmaya.asset.Asset.create(asset_id, asset_type)
        bmaya.core.log.info(f"Created {asset.id}: {asset.info_path}")


def new_variant_ui() -> None:
    asset_id = _ask_asset_id("New Variant")
    if asset_id:
        template = _ask_file("New Variant: pick the template", TEMPLATE_FILTER, save=False)
        if template:
            new_variant(asset_id, template)


def save_skeleton_ui() -> None:
    asset_id = _ask_asset_id("Save Skeleton")
    if asset_id:
        save_skeleton(asset_id)


def build_rig_ui() -> None:
    asset_id = _ask_asset_id("Build Rig")
    if not asset_id:
        return
    variants = require_asset(asset_id).variants
    if not variants:
        raise bmaya.asset.AssetError(f"{asset_id} has no variants. Add a template with New Variant first.")
    variant = variants[0] if len(variants) == 1 else _choose("Build Rig", f"Variant of {asset_id}:", variants)
    if variant:
        cmds.select(build_rig(asset_id, variant), replace=True)


def save_rig_ui() -> None:
    save_rig(bmaya.maya.activerig.get_active_rig().rig_root)


def save_control_shapes_ui() -> None:
    save_control_shapes(bmaya.maya.activerig.get_active_rig().rig_root)


def load_control_shapes_ui() -> None:
    load_control_shapes(bmaya.maya.activerig.get_active_rig().rig_root)


# ---- dialogs ---------------------------------------------------------------------------------

def _ask_asset_id(title: str, message: str = "Asset id (game|project|type|name):") -> str | None:
    """An asset id typed in a dialog, filled in with the active rig's asset id when the scene has a rig. Always
    asks, so the asset a tool is about to write to is on screen first."""
    try:
        default = bmaya.maya.activerig.get_active_rig().asset_id
    except RuntimeError:
        default = ""
    return _ask_text(title, message, default)


def _ask_text(title: str, message: str, text: str) -> str | None:
    result = cmds.promptDialog(title=title, message=message, text=text, button=["OK", "Cancel"],
                               defaultButton="OK", cancelButton="Cancel", dismissString="Cancel")
    value = cmds.promptDialog(query=True, text=True).strip() if result == "OK" else ""
    return value or None


def _choose(title: str, message: str, options: list[str]) -> str | None:
    """One of options, picked from a menu in a dialog. None when cancelled."""
    picked = {"value": options[0]}

    def layout():
        form = cmds.setParent(query=True)
        cmds.formLayout(form, edit=True, width=320)
        column = cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAttach=("both", 10))
        cmds.text(label=message, align="left")
        menu = cmds.optionMenu(changeCommand=lambda value: picked.update(value=value))
        for option in options:
            cmds.menuItem(label=option, parent=menu)
        cmds.rowLayout(numberOfColumns=2, parent=column)
        cmds.button(label="OK", width=150, command=lambda *_: cmds.layoutDialog(dismiss="OK"))
        cmds.button(label="Cancel", width=150, command=lambda *_: cmds.layoutDialog(dismiss="Cancel"))

    return picked["value"] if cmds.layoutDialog(title=title, uiScript=layout) == "OK" else None


def _ask_file(caption: str, file_filter: str, save: bool) -> str | None:
    paths = cmds.fileDialog2(caption=caption, fileFilter=file_filter, fileMode=0 if save else 1)
    return paths[0] if paths else None


def _ask_folder(caption: str) -> str | None:
    start = os.environ.get(bmaya.asset.project.PROJECTS_ROOT_ENV, "")
    paths = cmds.fileDialog2(caption=caption, fileMode=3, startingDirectory=start)
    return paths[0] if paths else None
