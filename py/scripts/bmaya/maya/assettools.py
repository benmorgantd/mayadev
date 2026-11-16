"""Asset tools for RigModules rigs, behind the RigModules menu (RigModules D30).

A rig can be built anywhere, before its asset exists. Once the asset's folder exists, these tools read and
write the asset's files. A built rig names its own asset id and rig name (the rig root's rigName, which is the variant's name), read
through rigmodules.query. Nothing here walks rig nodes or parses names (RigModules D24).

The shape, weight and rig tools ask for a file or folder for a rig whose asset folder doesn't exist yet.
Once it exists, they always use the asset's paths, so a file never lands in two places.

The functions at the top take everything as arguments, so batch jobs and other tools can call them. The
*_interactive functions below are the menu's entry points: they act on the active rig (bmaya.maya.activerig), ask
the user through a Prompter (bmaya.core.prompts), and call them. Nothing here opens a dialog itself (RigModules
D49). A plain function that falls back to asking for a file, when the asset folder doesn't exist yet, takes a
prompter too.
"""

from __future__ import annotations

import dataclasses
import os
import typing

import maya.cmds as cmds
import rigmodules.displaylayers
import rigmodules.groups
import rigmodules.jointclip
import rigmodules.query
import rigmodules.skinweights
import rigmodules.template

import bmaya.core.asset
import bmaya.core.asset.animproperties
import bmaya.core.asset.handlers
import bmaya.core.asset.library
import bmaya.core.log
import bmaya.core.prompts
import bmaya.maya.activerig
import bmaya.maya.assethandlers
import bmaya.maya.posetools

SCENE_FILTER = "Maya ASCII (*.ma)"
SHAPES_FILTER = "Shape files (*.json)"
TEMPLATE_FILTER = "Rig templates (*.json)"
POSE_FILTER = "Pose files (*.controlpose.json *.json)"
ANIMATION_FILTER = "Animation files (*.controlanim.json *.json)"
CLIP_FILTER = "FBX clips (*.fbx)"


def find_asset(asset_id: str) -> bmaya.core.asset.Asset | None:
    """The asset when its folder holds an asset.json, else None. None too, with a warning, when there is no
    projects root to look in."""
    try:
        asset = bmaya.core.asset.Asset(asset_id)
    except bmaya.core.asset.ProjectError as error:
        bmaya.core.log.warning(str(error))
        return None
    return asset if asset.exists() else None


def require_asset(asset_id: str) -> bmaya.core.asset.Asset:
    asset = bmaya.core.asset.Asset(asset_id)
    if not asset.exists():
        raise bmaya.core.asset.AssetError(f"{asset.id} has no asset.json at {asset.folder}. Create it with New Asset first.")
    return asset


def new_variant(asset_id: str, template_path: str) -> str:
    """Copies a template into the asset as a new variant, named by the template's rigName. Returns the variant."""
    asset = require_asset(asset_id)
    variant = rigmodules.template.get_rig_name(template_path)
    if asset.file_exists("template", variant):
        raise bmaya.core.asset.AssetError(f"{asset.id} already has variant {variant!r}: {asset.path('template', variant)}")
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "template", variant, source=template_path)
    bmaya.core.log.info(f"Added variant {variant!r} to {asset.id}: {path}")
    return variant


def save_skeleton(asset_id: str) -> str:
    """Saves the open scene as the asset's skeleton file. The scene is renamed to that file."""
    asset = require_asset(asset_id)
    if asset.skeleton != asset.id:
        raise bmaya.core.asset.AssetError(f"{asset.id} uses the skeleton of {asset.skeleton}. Save the skeleton there.")
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "skeleton")
    bmaya.core.log.info(f"Saved the skeleton of {asset.id}: {path}")
    return path


def save_model(asset_id: str, variant: str) -> str:
    """Saves the open scene as the variant's model file, the meshes the variant skins. The scene is renamed to
    that file. Warns about meshes without a meshId, because their weights can't be saved or loaded."""
    asset = require_asset(asset_id)
    if variant not in asset.variants:
        raise bmaya.core.asset.AssetError(f"{asset.id} has no variant {variant!r}. Add its template with New Variant first.")
    unmarked = [mesh for mesh in _scene_meshes() if not rigmodules.skinweights.get_mesh_id(mesh)]
    if unmarked:
        bmaya.core.log.warning("These meshes have no meshId, so their weights can't be saved. Mark them with "
                               "Mark Meshes for Skinning: " + ", ".join(unmarked))
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "model", variant)
    bmaya.core.log.info(f"Saved the model of {asset.id} variant {variant!r}: {path}")
    return path


def build_rig(asset_id: str, variant: str, namespace: str | None = None) -> str:
    """Imports the asset's skeleton, builds the variant's template on it, then loads the variant's files that
    exist: its shape file, its model (imported into the same namespace) and its skin weights. Builds into the
    open scene, into "{asset name}_{variant}" unless namespace is given, the namespace RigModules gives a rig
    (D54). Returns the rig root."""
    asset = require_asset(asset_id)
    bmaya.maya.assethandlers.register()
    template = bmaya.core.asset.handlers.load(asset, "template", variant)
    skeleton_asset = require_asset(asset.skeleton)
    # The skeleton is imported into the namespace before the build, so the namespace is decided here. The variant
    # is the template's rigName, so this is RigModules' own default.
    namespace = namespace or f"{asset.name}_{variant}"
    # A namespace holds one rig (RigModules D54), and createRigFromTemplate refuses a second. Failing here keeps
    # the skeleton import out of a namespace that can't take the build.
    if rigmodules.query.get_rigs(namespace):
        raise RuntimeError(f"Namespace {namespace!r} already holds a rig. Build into a new scene or another namespace.")

    nodes = bmaya.core.asset.handlers.load(skeleton_asset, "skeleton", namespace=namespace)
    joints = cmds.ls(nodes, type="joint")
    if not joints:
        raise RuntimeError(f"The skeleton file of {skeleton_asset.id} has no joints.")
    cmds.createRigFromTemplate(*joints, template=template.replace("\\", "/"), asset=asset.id, namespace=namespace)

    (rig_info,) = rigmodules.query.get_rigs(namespace)
    rig_root = rig_info.rig_root
    if asset.file_exists("shapes", variant):
        bmaya.core.asset.handlers.load(asset, "shapes", variant, rig_root=rig_root)
    if asset.file_exists("model", variant):
        model_nodes = bmaya.core.asset.handlers.load(asset, "model", variant, namespace=namespace)
        rigmodules.displaylayers.add_meshes(rig_root, model_nodes)
        rigmodules.groups.parent_meshes(rig_root, model_nodes)
        if asset.file_exists("weights", variant):
            bmaya.core.asset.handlers.load(asset, "weights", variant, namespace=namespace)
    # The imports above leave their nodes selected. A finished build starts with nothing selected.
    cmds.select(clear=True)
    # The build selects nothing, so the tracker would never see the new rig. It becomes the active rig.
    tracker = bmaya.maya.activerig.ActiveRigTracker.current()
    if tracker is not None:
        tracker.set_rig_root(rig_root)
    bmaya.core.log.info(f"Built {asset.id} variant {variant!r} into namespace {namespace!r}.")
    return rig_root


def save_rig(node: str, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Saves the open scene as the rig file of the rig node's asset and variant. Without an asset folder, asks
    for a file. Returns the path, or None when cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        path = _prompter(prompter).ask_file("Save Rig", SCENE_FILTER, save=True)
        if path:
            cmds.file(rename=path)
            cmds.file(save=True, type="mayaAscii", force=True)
        return path

    if info.rig_name not in asset.variants:
        raise bmaya.core.asset.AssetError(f"{asset.id} has no variant {info.rig_name!r}. Add its template with New Variant first.")
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "rig", info.rig_name)
    bmaya.core.log.info(f"Saved {asset.id} variant {info.rig_name!r}: {path}")
    return path


def save_control_shapes(node: str, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Saves the rig's control shapes to its asset's shape file, or to a file the user picks when the asset
    folder doesn't exist. Returns the path, or None when cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        path = _prompter(prompter).ask_file("Save Control Shapes", SHAPES_FILTER, save=True)
        if path:
            cmds.saveRigControlShapes(info.rig_root, file=path)
        return path

    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "shapes", info.rig_name, rig_root=info.rig_root)
    bmaya.core.log.info(f"Saved the control shapes of {asset.id} variant {info.rig_name!r}: {path}")
    return path


def load_control_shapes(node: str, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Loads the rig's control shapes from its asset's shape file, or from a file the user picks when the
    asset folder doesn't exist. Returns the path, or None when cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        path = _prompter(prompter).ask_file("Load Control Shapes", SHAPES_FILTER, save=False)
        if path:
            cmds.loadRigControlShapes(info.rig_root, file=path)
        return path

    bmaya.maya.assethandlers.register()
    bmaya.core.asset.handlers.load(asset, "shapes", info.rig_name, rig_root=info.rig_root)
    return asset.path("shapes", info.rig_name)


def library_meta(asset: bmaya.core.asset.Asset, scope: list[str], tags: typing.Sequence[str] = (),
                 description: str = "") -> dict:
    """The part of a library file's meta that the caller gives (RigModules D51): the author (the OS user), the rig's
    name as the template, the skeleton asset, and the tags and description when there are any. The rig fills the
    asset id, rig name, skeleton hash, plugin version and date itself (RigModules D54)."""
    meta = {
        "author": bmaya.core.asset.library.login(),
        "template": rigmodules.query.get_rig_info(scope[0]).rig_name,
        "skeleton": asset.skeleton if asset.exists() else asset.id,
    }
    if tags:
        meta["tags"] = list(tags)
    if description:
        meta["description"] = description
    return meta


def save_pose(asset_id: str, name: str, scope: list[str], tags: typing.Sequence[str] = (), description: str = "") -> str:
    """Saves the pose of scope (a rig root, or controls of one rig) to the own library of the current user for the
    asset, as <name>.controlpose.json in its controlposes folder (RigModules D51). No source control and no
    permission: a pose reaches the asset's Approved library by being published. An existing file is versioned first.
    Returns the path."""
    asset = bmaya.core.asset.Asset(asset_id)
    folder = bmaya.core.asset.library.user_source(asset).folders[bmaya.core.asset.library.POSE]
    path = bmaya.maya.assethandlers.save_control_file(
        bmaya.maya.assethandlers.ControlPoseHandler(), asset, "controlposes", name, folder=folder,
        scope=scope, meta=library_meta(asset, scope, tags, description))
    bmaya.core.log.info(f"Saved pose {name!r} of {asset.id}: {path}")
    return path


def save_animation(asset_id: str, name: str, scope: list[str], start_frame: int, end_frame: int,
                   tags: typing.Sequence[str] = (), description: str = "") -> str:
    """Saves the keys of scope (a rig root, or controls of one rig) over start_frame to end_frame to the own library
    of the current user for the asset, as <name>.controlanim.json in its controlanims folder (a ControlAnim,
    RigModules D42, D51). An existing file is versioned first. Returns the path."""
    asset = bmaya.core.asset.Asset(asset_id)
    folder = bmaya.core.asset.library.user_source(asset).folders[bmaya.core.asset.library.ANIMATION]
    path = bmaya.maya.assethandlers.save_control_file(
        bmaya.maya.assethandlers.ControlAnimHandler(), asset, "controlanims", name, folder=folder,
        scope=scope, start_frame=start_frame, end_frame=end_frame, meta=library_meta(asset, scope, tags, description))
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


def set_clip_properties(fbx: str, **changes) -> bmaya.core.asset.animproperties.AnimProperties:
    """Changes fields of the engine properties beside the clip's FBX (loop, root_motion, additive, events, curves),
    starting from the defaults when it has none. Returns the new properties."""
    path = bmaya.core.asset.animproperties.get_path(fbx)
    current = bmaya.core.asset.animproperties.read(path) if os.path.isfile(path) else bmaya.core.asset.animproperties.AnimProperties()
    properties = dataclasses.replace(current, **changes)
    bmaya.core.asset.animproperties.write(path, properties)
    bmaya.core.log.info(f"Saved the clip properties: {path}")
    return properties


def save_skin_weights(node: str, prompter: bmaya.core.prompts.Prompter | None = None) -> list[str] | None:
    """Saves the weights of every skinned mesh in the rig's namespace to its asset's weights folder, or to a
    folder the user picks when the asset folder doesn't exist. Returns the files written, or None when
    cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    handler = bmaya.maya.assethandlers.RigSkinWeightsHandler()
    if asset is None:
        folder = _ask_folder(_prompter(prompter), "Save Skin Weights: pick the weights folder")
        return handler.save(None, folder, namespace=info.namespace) if folder else None

    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "weights", info.rig_name, namespace=info.namespace)
    bmaya.core.log.info(f"Saved the skin weights of {asset.id} variant {info.rig_name!r}: {path}")
    return handler.files(path)


def load_skin_weights(node: str, prompter: bmaya.core.prompts.Prompter | None = None) -> list[str] | None:
    """Loads the weights in its asset's weights folder onto the meshes in the rig's namespace, matched by meshId,
    or from a folder the user picks when the asset folder doesn't exist. Returns the meshes loaded, or None
    when cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        folder = _ask_folder(_prompter(prompter), "Load Skin Weights: pick the weights folder")
        handler = bmaya.maya.assethandlers.RigSkinWeightsHandler()
        return handler.load(None, folder, namespace=info.namespace) if folder else None

    bmaya.maya.assethandlers.register()
    return bmaya.core.asset.handlers.load(asset, "weights", info.rig_name, namespace=info.namespace)


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
# Each takes its scope from the session (the active rig, the selection, the playback range) and asks for the rest
# through a Prompter: the one passed in, else the session's (bmaya.core.prompts.current()). Batch jobs call the
# plain functions above instead.

def new_project_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    folder = _ask_folder(_prompter(prompter), "New Project: pick the project folder")
    if folder:
        project = bmaya.core.asset.Project.create(folder)
        bmaya.core.log.info(f"Created {project.root}")


def new_asset_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "New Asset", "Asset id, its folder below the projects root (game\\project\\type\\name):")
    if not asset_id:
        return
    project = bmaya.core.asset.Asset(asset_id).project   # raises when no project.json is above the folder
    asset_type = prompter.choose("New Asset", f"Asset type of {asset_id}:", project.asset_types)
    if asset_type:
        asset = bmaya.core.asset.Asset.create(asset_id, asset_type)
        bmaya.core.log.info(f"Created {asset.id}: {asset.info_path}")


def new_variant_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "New Variant")
    if asset_id:
        template = prompter.ask_file("New Variant: pick the template", TEMPLATE_FILTER, save=False)
        if template:
            new_variant(asset_id, template)


def save_skeleton_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    asset_id = _ask_asset_id(_prompter(prompter), "Save Skeleton")
    if asset_id:
        save_skeleton(asset_id)


def save_model_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "Save Model")
    if not asset_id:
        return
    variant = _choose_variant(prompter, "Save Model", asset_id)
    if variant:
        save_model(asset_id, variant)


def build_rig_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "Build Rig")
    if not asset_id:
        return
    variant = _choose_variant(prompter, "Build Rig", asset_id)
    if variant:
        cmds.select(build_rig(asset_id, variant), replace=True)


def save_rig_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    save_rig(bmaya.maya.activerig.get_active_rig().rig_root, prompter=prompter)


def save_control_shapes_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    save_control_shapes(bmaya.maya.activerig.get_active_rig().rig_root, prompter=prompter)


def load_control_shapes_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    load_control_shapes(bmaya.maya.activerig.get_active_rig().rig_root, prompter=prompter)


def mirror_control_shapes_interactive(left_to_right: bool = True) -> None:
    """Copies the control shapes of one side of the active rig onto the other."""
    cmds.mirrorRigControlShapes(bmaya.maya.activerig.get_active_rig().rig_root, leftToRight=left_to_right)


def print_joint_markup_interactive() -> None:
    """Prints each selected joint's markup JSON."""
    joints = _get_selected_joints()
    for joint, markup in zip(joints, cmds.rigJointMarkup(*joints, query=True)):
        print(f"{joint}: {markup}")


def remove_joint_markup_interactive() -> None:
    """Removes the markup of the selected joints."""
    cmds.rigJointMarkup(*_get_selected_joints(), remove=True)


def _get_selected_joints() -> list[str]:
    joints = cmds.ls(selection=True, type="joint")
    if not joints:
        raise RuntimeError("Select joints.")
    return joints


def save_pose_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Saves the pose of the selected controls, or of the whole active rig, under a name the user gives, in the
    own library of the user for the asset. Before the asset's folder exists, asks for a file instead. Returns the
    path, or None when cancelled."""
    prompter = _prompter(prompter)
    scope = bmaya.maya.posetools.get_scope()
    info = rigmodules.query.get_rig_info(scope[0])
    asset = find_asset(info.asset_id)
    if asset is None:
        path = prompter.ask_file("Save Pose", POSE_FILTER, save=True)
        if path:
            cmds.saveRigPose(*scope, file=path)
        return path

    user = bmaya.core.asset.library.user_source(asset)
    name = prompter.ask_text("Save Pose", f"Pose name, saved in your own library of {asset.id}:",
                             bmaya.core.asset.library.free_name(user, bmaya.core.asset.library.POSE, "pose"))
    if not name:
        return None
    taken = _library_file(user, bmaya.core.asset.library.POSE, name)
    if taken and not _confirm_replace(prompter, "Save Pose", f"Pose {name!r}"):
        return None
    return save_pose(asset.id, name, scope)


def load_pose_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Loads a pose file the user picks, starting in their own library (the asset's Approved folder when they have
    none), onto the selected controls or the whole active rig. Returns the path, or None when cancelled."""
    scope = bmaya.maya.posetools.get_scope()
    asset = find_asset(rigmodules.query.get_rig_info(scope[0]).asset_id)
    path = _prompter(prompter).ask_file("Load Pose", POSE_FILTER, save=False,
                                        folder=_library_folder(asset, bmaya.core.asset.library.POSE))
    if path:
        bmaya.maya.posetools.load_pose(scope, path)
    return path


def save_animation_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Saves the keys of the selected controls, or of the whole active rig, over the playback range, under a name
    the user gives, in the own library of the user for the asset. Before the asset's folder exists, asks for a file
    instead. Returns the path, or None when cancelled."""
    prompter = _prompter(prompter)
    scope = bmaya.maya.posetools.get_scope()
    start, end = _playback_range()
    asset = find_asset(rigmodules.query.get_rig_info(scope[0]).asset_id)
    if asset is None:
        path = prompter.ask_file("Save Animation", ANIMATION_FILTER, save=True)
        if path:
            cmds.saveRigAnimation(*scope, file=_command_path(path), startFrame=start, endFrame=end)
        return path

    user = bmaya.core.asset.library.user_source(asset)
    name = prompter.ask_text("Save Animation", f"Animation name, saved in your own library of {asset.id}:",
                             bmaya.core.asset.library.free_name(user, bmaya.core.asset.library.ANIMATION, "animation"))
    if not name:
        return None
    taken = _library_file(user, bmaya.core.asset.library.ANIMATION, name)
    if taken and not _confirm_replace(prompter, "Save Animation", f"Animation {name!r}"):
        return None
    return save_animation(asset.id, name, scope, start, end)


def load_animation_interactive(mirror: bool = False, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Loads an animation file the user picks, starting in their own library (the asset's Approved folder when they
    have none), onto the selected controls or the whole active rig, keyed at the frames they were saved on. mirror
    puts the Left side's keys on the Right and the Right's on the Left. Returns the path, or None when cancelled."""
    scope = bmaya.maya.posetools.get_scope()
    asset = find_asset(rigmodules.query.get_rig_info(scope[0]).asset_id)
    path = _prompter(prompter).ask_file("Load Animation", ANIMATION_FILTER, save=False,
                                        folder=_library_folder(asset, bmaya.core.asset.library.ANIMATION))
    if path:
        bmaya.maya.posetools.load_animation(scope, path, mirror=mirror)
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


def save_joint_clip_file(fbx: str, rig_root: str, start_frame: int, end_frame: int) -> str:
    """Captures the rig's export joints over start_frame to end_frame into the FBX file fbx, with the files a clip
    has beside it, for a rig with no asset folder. Returns the FBX path."""
    folder, file_name = os.path.split(fbx)
    path = bmaya.maya.assethandlers.AnimClipHandler().save(
        None, folder, name=os.path.splitext(file_name)[0], rig_root=rig_root,
        start_frame=start_frame, end_frame=end_frame, own_folder=False)
    bmaya.core.log.info(f"Captured the joints on frames {start_frame} to {end_frame}: {path}")
    return path


def capture_joint_clip_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Captures the active rig's export joints over the playback range as an FBX clip (RigModules D42), under a
    name the user gives, in the asset's exports folder. Before the asset's folder exists, asks for a file instead.
    Returns the FBX path, or None when cancelled."""
    start, end = _playback_range()
    return _capture_joint_clip(_prompter(prompter), "Capture Joint Clip", start, end)


def capture_joint_pose_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Captures the active rig's export joints at the current frame as an FBX clip with one pose, saved as
    capture_joint_clip_interactive saves a clip. Returns the FBX path, or None when cancelled."""
    frame = int(cmds.currentTime(query=True))
    return _capture_joint_clip(_prompter(prompter), "Capture Joint Pose", frame, frame)


def _capture_joint_clip(prompter: bmaya.core.prompts.Prompter, caption: str, start_frame: int,
                        end_frame: int) -> str | None:
    rig = bmaya.maya.activerig.get_active_rig()
    asset = find_asset(rig.asset_id)
    if asset is None:
        path = prompter.ask_file(caption, CLIP_FILTER, save=True)
        return save_joint_clip_file(path, rig.rig_root, start_frame, end_frame) if path else None

    name = prompter.ask_text(caption, f"Clip name, saved in the exports folder of {asset.id}:")
    if not name:
        return None
    fbx = bmaya.maya.assethandlers.AnimClipHandler.fbx_path(asset.path("exports"), name)
    if os.path.exists(fbx) and not _confirm_replace(prompter, caption, f"Clip {name!r}"):
        return None
    return save_joint_clip(asset.id, name, rig.rig_root, start_frame, end_frame)


def pose_from_joint_pose_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Sets the selected controls, or the whole active rig, from an FBX clip with one pose that the user picks
    (RigModules D42). Returns the FBX path, or None when cancelled."""
    clip = _ask_clip(_prompter(prompter), "Pose Rig From Joint Pose")
    if clip:
        changed = cmds.poseRigFromJointPose(
            *bmaya.maya.posetools.get_scope(), jointPose=_command_path(clip.joint_clip)) or []
        bmaya.core.log.info(f"Posed {len(changed)} control(s) from the joint pose: {clip.fbx}")
        return clip.fbx
    return None


def animate_from_joint_clip_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Keys the selected controls, or the whole active rig, from an FBX clip the user picks (RigModules D42), with
    the ControlAnim beside it as the sidecar when it has one. Returns the FBX path, or None when cancelled."""
    clip = _ask_clip(_prompter(prompter), "Animate Rig From Joint Clip")
    if clip:
        sidecar = {"sidecar": _command_path(clip.sidecar)} if clip.sidecar else {}
        cmds.animateRigFromJointClip(*bmaya.maya.posetools.get_scope(), jointClip=_command_path(clip.joint_clip), **sidecar)
        bmaya.core.log.info(f"Animated the rig from the joint clip: {clip.fbx}")
        return clip.fbx
    return None


def _ask_clip(prompter: bmaya.core.prompts.Prompter, caption: str) -> bmaya.maya.assethandlers.AnimClip | None:
    """An FBX clip the user picks, starting in the active rig's asset's exports folder, read into a JointClip file
    (with the bone map beside it, when there is one). None when cancelled."""
    asset = find_asset(bmaya.maya.activerig.get_active_rig().asset_id)
    path = prompter.ask_file(caption, CLIP_FILTER, save=False, folder=_asset_folder(asset, "exports"))
    if not path:
        return None
    folder, file_name = os.path.split(path)
    return bmaya.maya.assethandlers.AnimClipHandler().load(asset, folder, name=os.path.splitext(file_name)[0])


def _command_path(path: str) -> str:
    return path.replace("\\", "/")


def save_skeleton_export_interactive() -> str | None:
    """Writes the active rig's skeleton export (the export joints at rest, as the skeleton asset source for the
    engine, with its bone map) into its asset's exports folder. Needs the asset's folder. Returns the FBX path."""
    rig = bmaya.maya.activerig.get_active_rig()
    fbx, _ = save_skeleton_export(rig.asset_id, rig.rig_root)
    return fbx


def check_clip_skeleton_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Checks an animation FBX the user picks against the active rig's asset's skeleton export. Raises when the
    joints differ, naming them. Returns the FBX path, or None when cancelled."""
    rig = bmaya.maya.activerig.get_active_rig()
    asset = find_asset(rig.asset_id)
    path = _prompter(prompter).ask_file("Check Clip Against Skeleton", CLIP_FILTER, save=False,
                                        folder=_asset_folder(asset, "exports"))
    if path:
        check_clip_skeleton(rig.asset_id, path)
    return path


@dataclasses.dataclass(frozen=True)
class ClipSettings:
    """The clip properties Edit Clip Properties asks for. Events and curves are kept as they are."""

    loop: bool = False
    root_motion: bool = False
    additive: typing.Literal[bmaya.core.asset.animproperties.ADDITIVE_TYPES] = "none"


def edit_clip_properties_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Sets the engine properties of an exported clip: an FBX the user picks, starting in the active rig's asset's
    exports folder, then loop, root motion and additive type in a form. Events and curves are kept as they are.
    Returns the FBX path, or None when cancelled."""
    prompter = _prompter(prompter)
    asset = find_asset(bmaya.maya.activerig.get_active_rig().asset_id)
    path = prompter.ask_file("Edit Clip Properties: pick the clip", CLIP_FILTER, save=False,
                             folder=_asset_folder(asset, "exports"))
    if not path:
        return None
    properties_path = bmaya.core.asset.animproperties.get_path(path)
    current = (bmaya.core.asset.animproperties.read(properties_path) if os.path.isfile(properties_path)
               else bmaya.core.asset.animproperties.AnimProperties())
    settings = prompter.ask_form("Clip Properties", ClipSettings(current.loop, current.root_motion, current.additive))
    if settings is None:
        return None
    set_clip_properties(path, **dataclasses.asdict(settings))
    return path


def save_skin_weights_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    save_skin_weights(bmaya.maya.activerig.get_active_rig().rig_root, prompter=prompter)


def load_skin_weights_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    load_skin_weights(bmaya.maya.activerig.get_active_rig().rig_root, prompter=prompter)


# ---- questions the workflows share ----------------------------------------------------------

def _prompter(prompter: bmaya.core.prompts.Prompter | None) -> bmaya.core.prompts.Prompter:
    return prompter or bmaya.core.prompts.current()


def _playback_range() -> tuple[int, int]:
    return int(cmds.playbackOptions(query=True, minTime=True)), int(cmds.playbackOptions(query=True, maxTime=True))


def _asset_folder(asset: bmaya.core.asset.Asset | None, file_type: str) -> str:
    """The folder a file dialog starts in: the asset's folder for file_type when it exists, else none."""
    folder = asset.path(file_type) if asset else ""
    return folder if os.path.isdir(folder) else ""


def _library_file(source: bmaya.core.asset.library.LibrarySource, kind: str, name: str) -> str | None:
    """The file of a name in a library source, or None."""
    return bmaya.core.asset.library.find_file(source.folders[kind], kind, name)


def _library_folder(asset: bmaya.core.asset.Asset | None, kind: str) -> str:
    """The folder a pose or animation dialog starts in: the user's own library when it exists, else the asset's
    Approved folder when that does, else none."""
    if asset is None:
        return ""
    user = bmaya.core.asset.library.user_source(asset).folders[kind]
    return user if os.path.isdir(user) else _asset_folder(asset, bmaya.core.asset.library.FOLDER_TYPE[kind])


def _ask_asset_id(prompter: bmaya.core.prompts.Prompter, title: str,
                  message: str = "Asset id (game\\project\\type\\name):") -> str | None:
    """An asset id, offered as the active rig's asset id when the scene has a rig. Always asks, so the asset a tool
    is about to write to is on screen first."""
    try:
        default = bmaya.maya.activerig.get_active_rig().asset_id
    except RuntimeError:
        default = ""
    return prompter.ask_text(title, message, default)


def _choose_variant(prompter: bmaya.core.prompts.Prompter, title: str, asset_id: str) -> str | None:
    """The asset's only variant, or one the user picks. Raises when it has none."""
    variants = require_asset(asset_id).variants
    if not variants:
        raise bmaya.core.asset.AssetError(f"{asset_id} has no variants. Add a template with New Variant first.")
    return variants[0] if len(variants) == 1 else prompter.choose(title, f"Variant of {asset_id}:", variants)


def _confirm_replace(prompter: bmaya.core.prompts.Prompter, title: str, what: str) -> bool:
    return prompter.confirm(title, f"{what} exists. Replace it? The old file is kept as a local version.",
                            accept="Replace")


def _ask_folder(prompter: bmaya.core.prompts.Prompter, title: str) -> str | None:
    """A folder, starting in the projects root."""
    return prompter.ask_folder(title, os.environ.get(bmaya.core.asset.project.PROJECTS_ROOT_ENV, ""))
