"""Asset tools for RigModules rigs, behind the RigModules menu (RigModules D30).

A rig can be built anywhere, before its asset exists. Once the asset's folder exists, these tools read and
write the asset's files. A built rig names its own asset id and variant (the rig root's rigName), read
through rigmodules.query. Nothing here walks rig nodes or parses names (RigModules D24).

The shape, weight and rig tools fall back to a file or folder dialog for a rig whose asset folder doesn't exist
yet.
Once it exists, they always use the asset's paths, so a file never lands in two places.

The functions at the top take everything as arguments, so batch jobs and other tools can call them. The
*_ui functions below act on the active rig (bmaya.maya.activerig), ask with dialogs, and call them.
"""

from __future__ import annotations

import os
import re

import maya.cmds as cmds
import rigmodules.query
import rigmodules.skinweights
import rigmodules.template

import bmaya.asset
import bmaya.asset.handlers
import bmaya.asset.sourcecontrol
import bmaya.asset.versions
import bmaya.core.log
import bmaya.maya.activerig
import bmaya.maya.assethandlers
import bmaya.maya.posetools

SCENE_FILTER = "Maya ASCII (*.ma)"
SHAPES_FILTER = "Shape files (*.json)"
TEMPLATE_FILTER = "Rig templates (*.json)"
POSE_FILTER = "Pose files (*.json)"
POSE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_ -]*$")


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


def save_model(asset_id: str, variant: str) -> str:
    """Saves the open scene as the variant's model file, the meshes the variant skins. The scene is renamed to
    that file. Warns about meshes without a meshId, because their weights can't be saved or loaded."""
    asset = require_asset(asset_id)
    if variant not in asset.variants:
        raise bmaya.asset.AssetError(f"{asset.id} has no variant {variant!r}. Add its template with New Variant first.")
    unmarked = [mesh for mesh in _scene_meshes() if not rigmodules.skinweights.get_mesh_id(mesh)]
    if unmarked:
        bmaya.core.log.warning("These meshes have no meshId, so their weights can't be saved. Mark them with "
                               "Mark Meshes for Skinning: " + ", ".join(unmarked))
    bmaya.maya.assethandlers.register()
    path = bmaya.asset.handlers.save(asset, "model", variant)
    bmaya.core.log.info(f"Saved the model of {asset.id} variant {variant!r}: {path}")
    return path


def build_rig(asset_id: str, variant: str, namespace: str | None = None) -> str:
    """Imports the asset's skeleton, builds the variant's template on it, then loads the variant's files that
    exist: its shape file, its model (imported into the same namespace) and its skin weights. Builds into the
    open scene. Returns the rig root."""
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
    if asset.file_exists("model", variant):
        bmaya.asset.handlers.load(asset, "model", variant, namespace=namespace)
        if asset.file_exists("weights", variant):
            bmaya.asset.handlers.load(asset, "weights", variant, namespace=namespace)
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


def save_pose(asset_id: str, name: str, scope: list[str]) -> str:
    """Saves the pose of scope (a rig root, or controls of one rig) as poses/<name>.json in the asset's poses
    folder, which every variant of the asset shares. An existing file is versioned first. Returns the path."""
    asset = require_asset(asset_id)
    if not POSE_NAME.match(name):
        raise ValueError(f"{name!r} is not a pose name: use letters, digits, spaces, '_' and '-'.")
    path = os.path.join(asset.path("poses"), name + ".json")
    existed = os.path.exists(path)
    if existed:
        bmaya.asset.versions.version(path, asset.root)
        bmaya.asset.sourcecontrol.current().checkout(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmds.saveRigPose(*scope, file=path.replace("\\", "/"))
    if not existed:
        bmaya.asset.sourcecontrol.current().add(path)
    bmaya.core.log.info(f"Saved pose {name!r} of {asset.id}: {path}")
    return path


def save_skin_weights(node: str) -> list[str] | None:
    """Saves the weights of every skinned mesh in the rig's namespace to its asset's weights folder, or to a
    folder chosen in a dialog when the asset folder doesn't exist. Returns the files written, or None when the
    dialog is cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    handler = bmaya.maya.assethandlers.RigSkinWeightsHandler()
    if asset is None:
        folder = _ask_folder("Save Skin Weights: pick the weights folder")
        return handler.save(None, folder, namespace=info.namespace) if folder else None

    bmaya.maya.assethandlers.register()
    path = bmaya.asset.handlers.save(asset, "weights", info.variant, namespace=info.namespace)
    bmaya.core.log.info(f"Saved the skin weights of {asset.id} variant {info.variant!r}: {path}")
    return handler.files(path)


def load_skin_weights(node: str) -> list[str] | None:
    """Loads the weights in its asset's weights folder onto the meshes in the rig's namespace, matched by meshId,
    or from a folder chosen in a dialog when the asset folder doesn't exist. Returns the meshes loaded, or None
    when the dialog is cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        folder = _ask_folder("Load Skin Weights: pick the weights folder")
        handler = bmaya.maya.assethandlers.RigSkinWeightsHandler()
        return handler.load(None, folder, namespace=info.namespace) if folder else None

    bmaya.maya.assethandlers.register()
    return bmaya.asset.handlers.load(asset, "weights", info.variant, namespace=info.namespace)


def mark_meshes_for_skinning(new_ids: bool = False) -> list[str]:
    """Gives every selected mesh a meshId, the id its weight files are matched by. A mesh keeps the id it has
    unless new_ids, which a duplicated mesh needs. Returns the ids."""
    ids = cmds.setRigMeshId(newId=new_ids)
    bmaya.core.log.info(f"{len(ids)} mesh(es) marked for skinning.")
    return ids


def _scene_meshes() -> list[str]:
    """Every visible mesh's transform in the scene, sorted."""
    shapes = cmds.ls(type="mesh", noIntermediate=True, long=True) or []
    return sorted({cmds.listRelatives(shape, parent=True, fullPath=True)[0] for shape in shapes})


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


def save_model_ui() -> None:
    asset_id = _ask_asset_id("Save Model")
    if not asset_id:
        return
    variant = _choose_variant("Save Model", asset_id)
    if variant:
        save_model(asset_id, variant)


def build_rig_ui() -> None:
    asset_id = _ask_asset_id("Build Rig")
    if not asset_id:
        return
    variant = _choose_variant("Build Rig", asset_id)
    if variant:
        cmds.select(build_rig(asset_id, variant), replace=True)


def save_rig_ui() -> None:
    save_rig(bmaya.maya.activerig.get_active_rig().rig_root)


def save_control_shapes_ui() -> None:
    save_control_shapes(bmaya.maya.activerig.get_active_rig().rig_root)


def load_control_shapes_ui() -> None:
    load_control_shapes(bmaya.maya.activerig.get_active_rig().rig_root)


def save_pose_ui() -> str | None:
    """Saves the pose of the selected controls, or of the whole active rig, under a name typed in a dialog, in the
    asset's poses folder. Before the asset's folder exists, asks for a file instead. Returns the path, or None
    when cancelled."""
    scope = bmaya.maya.posetools.get_scope()
    info = rigmodules.query.get_rig_info(scope[0])
    asset = find_asset(info.asset_id)
    if asset is None:
        path = _ask_file("Save Pose", POSE_FILTER, save=True)
        if path:
            cmds.saveRigPose(*scope, file=path)
        return path

    name = _ask_text("Save Pose", f"Pose name, saved in the poses folder of {asset.id}:", "")
    if not name:
        return None
    path = os.path.join(asset.path("poses"), name + ".json")
    if os.path.exists(path) and cmds.confirmDialog(
            title="Save Pose", message=f"Pose {name!r} exists. Replace it? The old file is kept as a local version.",
            button=["Replace", "Cancel"], defaultButton="Cancel", cancelButton="Cancel",
            dismissString="Cancel") != "Replace":
        return None
    return save_pose(asset.id, name, scope)


def load_pose_ui() -> str | None:
    """Loads a pose file chosen in a dialog that opens in the asset's poses folder, onto the selected controls or
    the whole active rig. Returns the path, or None when cancelled."""
    scope = bmaya.maya.posetools.get_scope()
    asset = find_asset(rigmodules.query.get_rig_info(scope[0]).asset_id)
    folder = asset.path("poses") if asset else ""
    path = _ask_file("Load Pose", POSE_FILTER, save=False, folder=folder if os.path.isdir(folder) else "")
    if path:
        changed = cmds.loadRigPose(*scope, file=path) or []
        bmaya.core.log.info(f"Loaded the pose onto {len(changed)} control(s): {path}")
    return path


def save_skin_weights_ui() -> None:
    save_skin_weights(bmaya.maya.activerig.get_active_rig().rig_root)


def load_skin_weights_ui() -> None:
    load_skin_weights(bmaya.maya.activerig.get_active_rig().rig_root)


# ---- dialogs ---------------------------------------------------------------------------------

def _ask_asset_id(title: str, message: str = "Asset id (game|project|type|name):") -> str | None:
    """An asset id typed in a dialog, filled in with the active rig's asset id when the scene has a rig. Always
    asks, so the asset a tool is about to write to is on screen first."""
    try:
        default = bmaya.maya.activerig.get_active_rig().asset_id
    except RuntimeError:
        default = ""
    return _ask_text(title, message, default)


def _choose_variant(title: str, asset_id: str) -> str | None:
    """The asset's only variant, or one picked in a dialog. Raises when it has none."""
    variants = require_asset(asset_id).variants
    if not variants:
        raise bmaya.asset.AssetError(f"{asset_id} has no variants. Add a template with New Variant first.")
    return variants[0] if len(variants) == 1 else _choose(title, f"Variant of {asset_id}:", variants)


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


def _ask_file(caption: str, file_filter: str, save: bool, folder: str = "") -> str | None:
    """A file chosen in a dialog that opens in folder, when it is given."""
    paths = cmds.fileDialog2(caption=caption, fileFilter=file_filter, fileMode=0 if save else 1,
                             startingDirectory=folder)
    return paths[0] if paths else None


def _ask_folder(caption: str) -> str | None:
    start = os.environ.get(bmaya.asset.project.PROJECTS_ROOT_ENV, "")
    paths = cmds.fileDialog2(caption=caption, fileMode=3, startingDirectory=start)
    return paths[0] if paths else None
