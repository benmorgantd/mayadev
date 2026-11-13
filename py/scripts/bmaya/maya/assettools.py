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

import dataclasses
import os

import maya.cmds as cmds
import rigmodules.displaylayers
import rigmodules.groups
import rigmodules.jointclip
import rigmodules.query
import rigmodules.skinweights
import rigmodules.template

import bmaya.asset
import bmaya.asset.animproperties
import bmaya.asset.handlers
import bmaya.core.log
import bmaya.maya.activerig
import bmaya.maya.assethandlers
import bmaya.maya.posetools

SCENE_FILTER = "Maya ASCII (*.ma)"
SHAPES_FILTER = "Shape files (*.json)"
TEMPLATE_FILTER = "Rig templates (*.json)"
POSE_FILTER = "Pose files (*.json)"
ANIMATION_FILTER = "Animation files (*.json)"
CLIP_FILTER = "FBX clips (*.fbx)"


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
        model_nodes = bmaya.asset.handlers.load(asset, "model", variant, namespace=namespace)
        rigmodules.displaylayers.add_meshes(rig_root, model_nodes)
        rigmodules.groups.parent_meshes(rig_root, model_nodes)
        if asset.file_exists("weights", variant):
            bmaya.asset.handlers.load(asset, "weights", variant, namespace=namespace)
    # The imports above leave their nodes selected. A finished build starts with nothing selected.
    cmds.select(clear=True)
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
    """Saves the pose of scope (a rig root, or controls of one rig) as controlposes/<name>.json in the asset's
    controlposes folder, which every variant of the asset shares. An existing file is versioned first. Returns the
    path."""
    asset = require_asset(asset_id)
    path = bmaya.maya.assethandlers.save_control_file(
        bmaya.maya.assethandlers.ControlPoseHandler(), asset, "controlposes", name, scope=scope)
    bmaya.core.log.info(f"Saved pose {name!r} of {asset.id}: {path}")
    return path


def save_animation(asset_id: str, name: str, scope: list[str], start_frame: int, end_frame: int) -> str:
    """Saves the keys of scope (a rig root, or controls of one rig) over start_frame to end_frame as
    controlanims/<name>.json in the asset's controlanims folder (a ControlAnim, RigModules D42). An existing file is
    versioned first. Returns the path."""
    asset = require_asset(asset_id)
    path = bmaya.maya.assethandlers.save_control_file(
        bmaya.maya.assethandlers.ControlAnimHandler(), asset, "controlanims", name,
        scope=scope, start_frame=start_frame, end_frame=end_frame)
    bmaya.core.log.info(f"Saved animation {name!r} of {asset.id} on frames {start_frame} to {end_frame}: {path}")
    return path


def save_skeleton_export(asset_id: str, rig_root: str) -> tuple[str, str]:
    """Writes the asset's skeleton export, the skeleton asset source for the engine, and its bone map into the
    asset's exports folder. Returns the FBX and the bone map."""
    asset = require_asset(asset_id)
    fbx, bone_map = bmaya.maya.assethandlers.save_skeleton_export(asset, rig_root)
    bmaya.core.log.info(f"Saved the skeleton export of {asset.id}: {fbx}")
    return fbx, bone_map


def check_clip_skeleton(asset_id: str, fbx: str) -> None:
    """Checks that the animation FBX has the joint names and parents of the asset's skeleton export. Raises
    FileNotFoundError when the asset has no skeleton export, and ValueError naming every joint that differs."""
    asset = require_asset(asset_id)
    skeleton = bmaya.maya.assethandlers.get_skeleton_export_path(asset)
    if not os.path.isfile(skeleton):
        raise FileNotFoundError(f"{asset.id} has no skeleton export at {skeleton}. Save it with Save Skeleton Export first.")
    rigmodules.jointclip.check_skeleton_match(fbx, skeleton)
    bmaya.core.log.info(f"{fbx} matches the skeleton of {asset.id}.")


def set_clip_properties(fbx: str, **changes) -> bmaya.asset.animproperties.AnimProperties:
    """Changes fields of the engine properties beside the clip's FBX (loop, root_motion, additive, events, curves),
    starting from the defaults when it has none. Returns the new properties."""
    path = bmaya.asset.animproperties.get_path(fbx)
    current = bmaya.asset.animproperties.read(path) if os.path.isfile(path) else bmaya.asset.animproperties.AnimProperties()
    properties = dataclasses.replace(current, **changes)
    bmaya.asset.animproperties.write(path, properties)
    bmaya.core.log.info(f"Saved the clip properties: {path}")
    return properties


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
    unless new_ids, which a duplicated mesh needs. Returns the ids. The log says how many ids were new and how many
    were kept, so marking meshes that already have ids doesn't look like it did nothing."""
    before = {cmds.getAttr(plug) for plug in cmds.ls("*.meshId") or []}
    ids = cmds.setRigMeshId(newId=new_ids) or []
    if new_ids:
        bmaya.core.log.info(f"{len(ids)} mesh(es) given new ids.")
    else:
        kept = sum(1 for mesh_id in ids if mesh_id in before)
        bmaya.core.log.info(f"{len(ids)} mesh(es) marked for skinning: {len(ids) - kept} new id(s), "
                            f"{kept} already had one and kept it.")
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
    asset_id = _ask_asset_id("New Asset", "Asset id, its folder below the projects root (game\\project\\type\\name):")
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

    name = _ask_text("Save Pose", f"Pose name, saved in the controlposes folder of {asset.id}:", "")
    if not name:
        return None
    path = os.path.join(asset.path("controlposes"), name + ".json")
    if os.path.exists(path) and not _confirm_replace("Save Pose", f"Pose {name!r}"):
        return None
    return save_pose(asset.id, name, scope)


def load_pose_ui() -> str | None:
    """Loads a pose file chosen in a dialog that opens in the asset's controlposes folder, onto the selected controls or
    the whole active rig. Returns the path, or None when cancelled."""
    scope = bmaya.maya.posetools.get_scope()
    asset = find_asset(rigmodules.query.get_rig_info(scope[0]).asset_id)
    folder = asset.path("controlposes") if asset else ""
    path = _ask_file("Load Pose", POSE_FILTER, save=False, folder=folder if os.path.isdir(folder) else "")
    if path:
        changed = cmds.loadRigPose(*scope, file=path) or []
        bmaya.core.log.info(f"Loaded the pose onto {len(changed)} control(s): {path}")
    return path


def save_animation_ui() -> str | None:
    """Saves the keys of the selected controls, or of the whole active rig, over the playback range, under a name
    typed in a dialog, in the asset's controlanims folder. Before the asset's folder exists, asks for a file
    instead. Returns the path, or None when cancelled."""
    scope = bmaya.maya.posetools.get_scope()
    start = int(cmds.playbackOptions(query=True, minTime=True))
    end = int(cmds.playbackOptions(query=True, maxTime=True))
    asset = find_asset(rigmodules.query.get_rig_info(scope[0]).asset_id)
    if asset is None:
        path = _ask_file("Save Animation", ANIMATION_FILTER, save=True)
        if path:
            cmds.saveRigAnimation(*scope, file=_command_path(path), startFrame=start, endFrame=end)
        return path

    name = _ask_text("Save Animation", f"Animation name, saved in the controlanims folder of {asset.id}:", "")
    if not name:
        return None
    existing = bmaya.maya.assethandlers.ControlAnimHandler.file_path(asset.path("controlanims"), name)
    if os.path.exists(existing) and not _confirm_replace("Save Animation", f"Animation {name!r}"):
        return None
    return save_animation(asset.id, name, scope, start, end)


def load_animation_ui(mirror: bool = False) -> str | None:
    """Loads an animation file chosen in a dialog that opens in the asset's controlanims folder onto the selected
    controls or the whole active rig, keys at the frames they were saved on. mirror puts the Left side's keys on the
    Right and the Right's on the Left. Returns the path, or None when cancelled."""
    scope = bmaya.maya.posetools.get_scope()
    asset = find_asset(rigmodules.query.get_rig_info(scope[0]).asset_id)
    folder = asset.path("controlanims") if asset else ""
    path = _ask_file("Load Animation", ANIMATION_FILTER, save=False, folder=folder if os.path.isdir(folder) else "")
    if path:
        changed = cmds.loadRigAnimation(*scope, file=_command_path(path), mirror=mirror) or []
        bmaya.core.log.info(f"Loaded the animation onto {len(changed)} control(s){' mirrored' if mirror else ''}: {path}")
    return path


def save_joint_clip(asset_id: str, name: str, rig_root: str, start_frame: int, end_frame: int) -> str:
    """Captures the rig's export joints over start_frame to end_frame into exports/<name>/<name>.fbx in the
    asset's folder, which every variant of the asset shares. An existing clip is versioned first. Returns the FBX
    path."""
    asset = require_asset(asset_id)
    fbx = bmaya.maya.assethandlers.save_anim_clip(
        asset, name, rig_root=rig_root, start_frame=start_frame, end_frame=end_frame)
    bmaya.core.log.info(f"Saved clip {name!r} of {asset.id} on frames {start_frame} to {end_frame}: {fbx}")
    return fbx


def capture_joint_clip_ui() -> str | None:
    """Captures the active rig's export joints over the playback range as an FBX clip (RigModules D42), under a
    name typed in a dialog, in the asset's exports folder. Before the asset's folder exists, asks for a file
    instead. Returns the FBX path, or None when cancelled."""
    start = int(cmds.playbackOptions(query=True, minTime=True))
    end = int(cmds.playbackOptions(query=True, maxTime=True))
    return _capture_joint_clip("Capture Joint Clip", start, end)


def capture_joint_pose_ui() -> str | None:
    """Captures the active rig's export joints at the current frame as an FBX clip with one pose, saved as
    capture_joint_clip_ui saves a clip. Returns the FBX path, or None when cancelled."""
    frame = int(cmds.currentTime(query=True))
    return _capture_joint_clip("Capture Joint Pose", frame, frame)


def _capture_joint_clip(caption: str, start_frame: int, end_frame: int) -> str | None:
    rig = bmaya.maya.activerig.get_active_rig()
    asset = find_asset(rig.asset_id)
    if asset is None:
        path = _ask_file(caption, CLIP_FILTER, save=True)
        if not path:
            return None
        folder, file_name = os.path.split(path)
        fbx = bmaya.maya.assethandlers.AnimClipHandler().save(
            None, folder, name=os.path.splitext(file_name)[0], rig_root=rig.rig_root,
            start_frame=start_frame, end_frame=end_frame, own_folder=False)
        bmaya.core.log.info(f"Captured the joints on frames {start_frame} to {end_frame}: {fbx}")
        return fbx

    name = _ask_text(caption, f"Clip name, saved in the exports folder of {asset.id}:", "")
    if not name:
        return None
    fbx = bmaya.maya.assethandlers.AnimClipHandler.fbx_path(asset.path("exports"), name)
    if os.path.exists(fbx) and not _confirm_replace(caption, f"Clip {name!r}"):
        return None
    return save_joint_clip(asset.id, name, rig.rig_root, start_frame, end_frame)


def pose_from_joint_pose_ui() -> str | None:
    """Sets the selected controls, or the whole active rig, from an FBX clip with one pose, chosen in a dialog
    (RigModules D42). Returns the FBX path, or None when cancelled."""
    clip = _ask_clip("Pose Rig From Joint Pose")
    if clip:
        changed = cmds.poseRigFromJointPose(
            *bmaya.maya.posetools.get_scope(), jointPose=_command_path(clip.joint_clip)) or []
        bmaya.core.log.info(f"Posed {len(changed)} control(s) from the joint pose: {clip.fbx}")
        return clip.fbx
    return None


def animate_from_joint_clip_ui() -> str | None:
    """Keys the selected controls, or the whole active rig, from an FBX clip chosen in a dialog (RigModules D42),
    with the ControlAnim beside it as the sidecar when it has one. Returns the FBX path, or None when cancelled."""
    clip = _ask_clip("Animate Rig From Joint Clip")
    if clip:
        sidecar = {"sidecar": _command_path(clip.sidecar)} if clip.sidecar else {}
        cmds.animateRigFromJointClip(*bmaya.maya.posetools.get_scope(), jointClip=_command_path(clip.joint_clip), **sidecar)
        bmaya.core.log.info(f"Animated the rig from the joint clip: {clip.fbx}")
        return clip.fbx
    return None


def _ask_clip(caption: str) -> bmaya.maya.assethandlers.AnimClip | None:
    """An FBX clip chosen in a dialog that opens in the active rig's asset's exports folder, read into a JointClip
    file (with the bone map beside it, when there is one). None when cancelled."""
    asset = find_asset(bmaya.maya.activerig.get_active_rig().asset_id)
    folder = asset.path("exports") if asset else ""
    path = _ask_file(caption, CLIP_FILTER, save=False, folder=folder if os.path.isdir(folder) else "")
    if not path:
        return None
    folder, file_name = os.path.split(path)
    return bmaya.maya.assethandlers.AnimClipHandler().load(asset, folder, name=os.path.splitext(file_name)[0])


def _command_path(path: str) -> str:
    return path.replace("\\", "/")


def save_skeleton_export_ui() -> str | None:
    """Writes the active rig's skeleton export (the export joints at rest, as the skeleton asset source for the
    engine, with its bone map) into its asset's exports folder. Needs the asset's folder. Returns the FBX path."""
    rig = bmaya.maya.activerig.get_active_rig()
    fbx, _ = save_skeleton_export(rig.asset_id, rig.rig_root)
    return fbx


def check_clip_skeleton_ui() -> str | None:
    """Checks an animation FBX chosen in a dialog against the active rig's asset's skeleton export. Raises when the
    joints differ, naming them. Returns the FBX path, or None when cancelled."""
    rig = bmaya.maya.activerig.get_active_rig()
    asset = find_asset(rig.asset_id)
    folder = asset.path("exports") if asset else ""
    path = _ask_file("Check Clip Against Skeleton", CLIP_FILTER, save=False, folder=folder if os.path.isdir(folder) else "")
    if path:
        check_clip_skeleton(rig.asset_id, path)
    return path


def edit_clip_properties_ui() -> str | None:
    """Sets the engine properties of an exported clip: an FBX chosen in a dialog that opens in the active rig's
    asset's exports folder, then loop, root motion and additive type in a small dialog. Events and curves are kept as
    they are. Returns the FBX path, or None when cancelled."""
    asset = find_asset(bmaya.maya.activerig.get_active_rig().asset_id)
    folder = asset.path("exports") if asset else ""
    path = _ask_file("Edit Clip Properties: pick the clip", CLIP_FILTER, save=False, folder=folder if os.path.isdir(folder) else "")
    if not path:
        return None
    properties_path = bmaya.asset.animproperties.get_path(path)
    current = (bmaya.asset.animproperties.read(properties_path) if os.path.isfile(properties_path)
               else bmaya.asset.animproperties.AnimProperties())
    changes = _ask_clip_properties(current)
    if changes is None:
        return None
    set_clip_properties(path, **changes)
    return path


def save_skin_weights_ui() -> None:
    save_skin_weights(bmaya.maya.activerig.get_active_rig().rig_root)


def load_skin_weights_ui() -> None:
    load_skin_weights(bmaya.maya.activerig.get_active_rig().rig_root)


# ---- dialogs ---------------------------------------------------------------------------------

def _ask_asset_id(title: str, message: str = "Asset id (game\\project\\type\\name):") -> str | None:
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


def _ask_clip_properties(current: bmaya.asset.animproperties.AnimProperties) -> dict | None:
    """Loop, root motion and additive type, chosen in a dialog that starts at current's values. None when cancelled."""
    picked = {"loop": current.loop, "root_motion": current.root_motion, "additive": current.additive}

    def layout():
        form = cmds.setParent(query=True)
        cmds.formLayout(form, edit=True, width=320)
        column = cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAttach=("both", 10))
        cmds.checkBox(label="Loop", value=current.loop, changeCommand=lambda value: picked.update(loop=bool(value)))
        cmds.checkBox(label="Root motion", value=current.root_motion, changeCommand=lambda value: picked.update(root_motion=bool(value)))
        menu = cmds.optionMenu(label="Additive", changeCommand=lambda value: picked.update(additive=value))
        for option in bmaya.asset.animproperties.ADDITIVE_TYPES:
            cmds.menuItem(label=option, parent=menu)
        cmds.optionMenu(menu, edit=True, value=current.additive)
        cmds.rowLayout(numberOfColumns=2, parent=column)
        cmds.button(label="OK", width=150, command=lambda *_: cmds.layoutDialog(dismiss="OK"))
        cmds.button(label="Cancel", width=150, command=lambda *_: cmds.layoutDialog(dismiss="Cancel"))

    return picked if cmds.layoutDialog(title="Clip Properties", uiScript=layout) == "OK" else None


def _confirm_replace(title: str, what: str) -> bool:
    return cmds.confirmDialog(
        title=title, message=f"{what} exists. Replace it? The old file is kept as a local version.",
        button=["Replace", "Cancel"], defaultButton="Cancel", cancelButton="Cancel",
        dismissString="Cancel") == "Replace"


def _ask_file(caption: str, file_filter: str, save: bool, folder: str = "") -> str | None:
    """A file chosen in a dialog that opens in folder, when it is given."""
    paths = cmds.fileDialog2(caption=caption, fileFilter=file_filter, fileMode=0 if save else 1,
                             startingDirectory=folder)
    return paths[0] if paths else None


def _ask_folder(caption: str) -> str | None:
    start = os.environ.get(bmaya.asset.project.PROJECTS_ROOT_ENV, "")
    paths = cmds.fileDialog2(caption=caption, fileMode=3, startingDirectory=start)
    return paths[0] if paths else None
