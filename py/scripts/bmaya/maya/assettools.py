"""Asset tools for RigModules rigs, behind the RigModules menu (RigModules D30).

A rig can be built anywhere, before its asset exists. Once the asset's folder exists, these tools read and
write the asset's files. An asset holds skeletons, rigs and looks (RigModules D54): a rig is a template built on one
skeleton, and a look is the meshes and skin weights a rig of that skeleton wears. A built rig names its own asset id
and rig name (the rig root's rigName, which is the rig's folder name) and the look it wears (RigInfo.look, from its
lookRoot node, RigModules D54), read through rigmodules.query. The tools that read or write a look's files use the
look the rig wears, and take a look to override it. Nothing here walks rig nodes or parses names (RigModules D24).

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
import tempfile
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
DEFAULT_NAME = "default"   # the name offered for an asset's first skeleton and first look (RigModules D54)
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


def new_rig(asset_id: str, template_path: str, rig: str | None = None, skeleton: str = DEFAULT_NAME,
            skeleton_asset: str | None = None, source: bmaya.core.asset.RigRef | None = None) -> str:
    """Adds a rig to the asset: copies a template into rigs/<rig>, with its rigName set to the rig's name, and writes
    the rig's rig.json. rig is the template's own rigName when left out. skeleton is the skeleton the rig is built on,
    in this asset unless skeleton_asset names another. It needn't be saved yet. source is the rig this one is a copy
    of, whose poses and animations the library then lists beside its own. Returns the rig's name."""
    asset = require_asset(asset_id)
    rig = rig or rigmodules.template.get_rig_name(template_path)
    reference = bmaya.core.asset.SkeletonRef(skeleton, skeleton_asset)
    if asset.file_exists("riginfo", rig) or asset.file_exists("template", rig):
        raise bmaya.core.asset.AssetError(f"{asset.id} already has a rig {rig!r}: {os.path.dirname(asset.path('riginfo', rig))}")
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "template", rig, source=template_path)
    asset.add_rig(rig, reference, source)
    bmaya.core.log.info(f"Added the rig {rig!r} to {asset.id}, on the skeleton {skeleton!r}: {path}")
    return rig


def new_look(asset_id: str, look: str = DEFAULT_NAME, skeleton: str = DEFAULT_NAME, skeleton_asset: str | None = None) -> str:
    """Adds a look to the asset: writes looks/<look>/look.json, naming the skeleton its meshes bind to (in this asset
    unless skeleton_asset names another). Any rig of that skeleton can wear the look. Returns the look's name."""
    asset = require_asset(asset_id)
    asset.add_look(look, [bmaya.core.asset.SkeletonRef(skeleton, skeleton_asset)])
    bmaya.core.log.info(f"Added the look {look!r} to {asset.id}, for the skeleton {skeleton!r}: {asset.path('lookinfo', look)}")
    return look


def save_skeleton(asset_id: str, skeleton: str = DEFAULT_NAME, joints: list[str] | None = None) -> str:
    """Saves joints (every joint in the scene when left out) as a skeleton of the asset: skeletons/<skeleton>/
    skeleton.json, the only form a skeleton is stored in (RigModules D54). The scene is not saved or renamed.
    Every joint must carry joint markup, since the file holds marked joints only, and none may be driven by a rig,
    since the file records the joints as they are. Nothing is written when a joint fails. Returns the file."""
    asset = require_asset(asset_id)
    joints = list(joints) if joints else cmds.ls(type="joint", long=True)
    if not joints:
        raise RuntimeError("There are no joints to save as a skeleton.")
    driven = [joint for joint in joints if rigmodules.query.find_rig_info(joint) is not None]
    if driven:
        raise RuntimeError("These joints are driven by a rig, so they may not be at rest. Save the skeleton from a "
                           "scene without the rig: " + ", ".join(driven))
    # A first write to a scratch file: a joint without markup fails here, before the asset's file is versioned,
    # checked out or its folder made.
    handle, scratch = tempfile.mkstemp(suffix=".skeleton.json")
    os.close(handle)
    try:
        cmds.saveRigSkeleton(*joints, file=scratch.replace("\\", "/"))
    finally:
        os.remove(scratch)
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "skeleton", skeleton, joints=joints)
    bmaya.core.log.info(f"Saved the skeleton {skeleton!r} of {asset.id}: {path}")
    return path


def load_skeleton(asset_id: str, skeleton: str = DEFAULT_NAME, namespace: str | None = None) -> list[str]:
    """Creates the joints of a skeleton of the asset in the scene, at rest and marked, to look at or edit it. They
    go into namespace, the current one when left out. Returns the joints."""
    asset = require_asset(asset_id)
    bmaya.maya.assethandlers.register()
    joints = bmaya.core.asset.handlers.load(asset, "skeleton", skeleton, namespace=namespace)
    bmaya.core.log.info(f"Loaded the skeleton {skeleton!r} of {asset.id}: {len(joints)} joint(s).")
    return joints


def save_model(asset_id: str, look: str, meshes: list[str] | None = None) -> str:
    """Saves meshes (every visible mesh in the scene when left out) as the look's model file. A model file is only
    meshes (RigModules D54): each is exported from its undeformed shape with no skinning, no history and no joints,
    under its own name, with its meshId and its shading. The scene is not saved, renamed or changed. Warns about
    meshes without a meshId, because their weights can't be saved or loaded."""
    asset = require_asset(asset_id)
    if look not in asset.looks:
        raise bmaya.core.asset.AssetError(f"{asset.id} has no look {look!r}. Add it with New Look first.")
    meshes = list(meshes) if meshes else bmaya.maya.assethandlers.get_scene_meshes()
    unmarked = [mesh for mesh in meshes if not rigmodules.skinweights.get_mesh_id(mesh)]
    if unmarked:
        bmaya.core.log.warning("These meshes have no meshId, so their weights can't be saved. Mark them with "
                               "Mark Meshes for Skinning: " + ", ".join(unmarked))
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "model", look, meshes=meshes)
    bmaya.core.log.info(f"Saved the model of {asset.id} look {look!r}: {path}")
    return path


def build_rig(asset_id: str, rig: str, look: str | None = None, namespace: str | None = None) -> str:
    """Builds a rig of the asset in the open scene: creates its skeleton's joints from the skeleton file (the
    skeleton may be another asset's), builds the rig's template on them, and loads the rig's shape file. Then it puts
    a look on the rig: the look's model is imported into the same namespace and its skin weights are loaded onto the
    rig's joints. look is the asset's "default" look when left out and it has one, else none. A look that is named and
    missing, or whose look.json doesn't name the rig's skeleton, fails before anything is created. Builds into
    "{asset name}_{rig}" unless namespace is given, the namespace RigModules gives a rig (D54). Returns the rig root."""
    asset = require_asset(asset_id)
    bmaya.maya.assethandlers.register()
    template = bmaya.core.asset.handlers.load(asset, "template", rig)
    skeleton_asset, skeleton = asset.skeleton_of(rig)
    if not skeleton_asset.exists() or skeleton not in skeleton_asset.skeletons:
        raise bmaya.core.asset.AssetError(
            f"The rig {rig!r} of {asset.id} is built on the skeleton {skeleton!r} of {skeleton_asset.id}, which has no "
            f"skeleton file. Save it with Save Skeleton first.")
    if look is None and DEFAULT_NAME in asset.looks:
        look = DEFAULT_NAME
    if look is not None and not asset.look_fits(look, rig):   # raises for a look the asset doesn't have
        raise bmaya.core.asset.AssetError(
            f"The look {look!r} of {asset.id} is not for the skeleton {skeleton!r} that the rig {rig!r} is built on.")
    # The skeleton goes into the namespace before the build, so the namespace is decided here. The rig's name is
    # the template's rigName, so this is RigModules' own default.
    namespace = namespace or f"{asset.name}_{rig}"
    # A namespace holds one rig (RigModules D54), and createRigFromTemplate refuses a second. Failing here keeps
    # the skeleton out of a namespace that can't take the build.
    if rigmodules.query.get_rigs(namespace):
        raise RuntimeError(f"Namespace {namespace!r} already holds a rig. Build into a new scene or another namespace.")

    joints = bmaya.core.asset.handlers.load(skeleton_asset, "skeleton", skeleton, namespace=namespace)
    if not joints:
        raise RuntimeError(f"The skeleton {skeleton!r} of {skeleton_asset.id} has no joints.")
    cmds.createRigFromTemplate(*joints, template=template.replace("\\", "/"), asset=asset.id, namespace=namespace)

    (rig_info,) = rigmodules.query.get_rigs(namespace)
    rig_root = rig_info.rig_root
    if asset.file_exists("shapes", rig):
        bmaya.core.asset.handlers.load(asset, "shapes", rig, rig_root=rig_root)
    if look is not None and asset.file_exists("model", look):
        if asset.file_exists("weights", look):
            apply_look(rig_root, look)   # records the look on the rig
        else:
            # A model with no weights yet has nothing to swap in: its meshes are imported unskinned and no look is recorded.
            model_nodes = bmaya.core.asset.handlers.load(asset, "model", look, namespace=namespace)
            rigmodules.displaylayers.add_meshes(rig_root, model_nodes)
            rigmodules.groups.parent_meshes(rig_root, model_nodes)
    # The imports above leave their nodes selected. A finished build starts with nothing selected.
    cmds.select(clear=True)
    # The build selects nothing, so the tracker would never see the new rig. It becomes the active rig.
    tracker = bmaya.maya.activerig.ActiveRigTracker.current()
    if tracker is not None:
        tracker.set_rig_root(rig_root)
    wearing = f" wearing the look {look!r}" if look is not None else " with no look"
    bmaya.core.log.info(f"Built the rig {rig!r} of {asset.id} into namespace {namespace!r},{wearing}.")
    return rig_root


def apply_look(node: str, look: str) -> str:
    """Puts the rig that node belongs to in a look of its asset (RigModules D54): imports the look's model into the
    rig's namespace, then cmds.setRigLook loads the look's weight files onto the rig's joints, deletes the previous
    look's meshes and records the look on the rig's lookRoot. The new meshes join the rig's mesh layer and group. The
    controls and animation are not touched. A look that is not synced yet is synced first (source control), and then
    checked against the rig like any other. One undo step. A weight file made for another skeleton fails the swap, and
    the imported meshes are removed again. Raises AssetError for a look the asset doesn't have, one that doesn't fit the
    rig's skeleton, or one with no model or weights. Returns the lookRoot node."""
    info = rigmodules.query.get_rig_info(node)
    asset = require_asset(info.asset_id)
    if look in {entry.name for entry in asset.all_looks() if not entry.local}:
        asset.sync_look(look)   # before the scene is touched: a failed sync changes nothing
    asset.look(look)   # raises for a look the asset doesn't have
    if info.rig_name in asset.rigs and not asset.look_fits(look, info.rig_name):
        raise bmaya.core.asset.AssetError(
            f"The look {look!r} of {asset.id} is not for the skeleton that the rig {info.rig_name!r} is built on.")
    for file_type in ("model", "weights"):
        if not asset.file_exists(file_type, look):
            raise bmaya.core.asset.AssetError(f"The look {look!r} of {asset.id} has no {file_type} file. Save it first.")
    files = bmaya.maya.assethandlers.RigSkinWeightsHandler.files(asset.path("weights", look))
    if not files:
        raise bmaya.core.asset.AssetError(f"The look {look!r} of {asset.id} has no weight files.")

    bmaya.maya.assethandlers.register()
    cmds.undoInfo(openChunk=True, chunkName="Apply Look")
    try:
        model_nodes = bmaya.core.asset.handlers.load(asset, "model", look, namespace=info.namespace)
        meshes = [model_node for model_node in model_nodes
                  if cmds.nodeType(model_node) == "transform" and rigmodules.skinweights.get_mesh_id(model_node)]
        try:
            if not meshes:
                raise bmaya.core.asset.AssetError(f"The model of the look {look!r} has no mesh with a meshId.")
            look_root = cmds.setRigLook(info.rig_root, mesh=meshes, file=[path.replace("\\", "/") for path in files],
                                        asset=asset.id, look=look)
        except Exception:
            # The import is not part of setRigLook's undo, so a failed swap takes the imported meshes out itself.
            cmds.delete([mesh for mesh in meshes if cmds.objExists(mesh)])
            raise
        # setRigLook renamed the meshes after their files, so they are found again by id.
        wanted = {rigmodules.skinweights.read_file_mesh_id(path) for path in files}
        new_meshes = [mesh for mesh_id, mesh in rigmodules.skinweights.get_meshes(info.namespace).items() if mesh_id in wanted]
        rigmodules.displaylayers.add_meshes(info.rig_root, new_meshes)
        rigmodules.groups.parent_meshes(info.rig_root, new_meshes)
        cmds.select(clear=True)   # inside the chunk, so an undo takes the whole apply and not just the selection
    finally:
        cmds.undoInfo(closeChunk=True)
    bmaya.core.log.info(f"Put the rig {info.rig_name!r} of {asset.id} in the look {look!r}.")
    return look_root


def save_rig(node: str, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Saves the open scene as the rig file of the rig node's asset and rig. Without an asset folder, asks
    for a file. Returns the path, or None when cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        path = _prompter(prompter).ask_file("Save Rig", SCENE_FILTER, save=True)
        if path:
            cmds.file(rename=path)
            cmds.file(save=True, type="mayaAscii", force=True)
        return path

    if info.rig_name not in asset.rigs:
        raise bmaya.core.asset.AssetError(f"{asset.id} has no rig {info.rig_name!r}. Add it with New Rig first.")
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "rig", info.rig_name)
    bmaya.core.log.info(f"Saved the rig {info.rig_name!r} of {asset.id}: {path}")
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
    bmaya.core.log.info(f"Saved the control shapes of the rig {info.rig_name!r} of {asset.id}: {path}")
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
    name as the template, the name of the skeleton the rig is built on when the asset says, and the tags and
    description when there are any. The rig fills the asset id, rig name, skeleton hash, plugin version and date
    itself (RigModules D54): the hash, not the skeleton's name, is what says two files are for one skeleton."""
    rig = rigmodules.query.get_rig_info(scope[0]).rig_name
    meta = {"author": bmaya.core.asset.library.login(), "template": rig}
    if asset.exists() and rig in asset.rigs:
        meta["skeleton"] = asset.rig(rig).skeleton.name
    if tags:
        meta["tags"] = list(tags)
    if description:
        meta["description"] = description
    return meta


def save_pose(asset_id: str, name: str, scope: list[str], tags: typing.Sequence[str] = (), description: str = "") -> str:
    """Saves the pose of scope (a rig root, or controls of one rig) to the own library of the current user for the
    scope's rig of the asset, as <name>.controlpose.json in its controlposes folder (RigModules D51, D54). No source
    control and no permission: a pose reaches the rig's Approved library by being published. An existing file is
    versioned first. Returns the path."""
    asset = bmaya.core.asset.Asset(asset_id)
    rig = rigmodules.query.get_rig_info(scope[0]).rig_name
    folder = bmaya.core.asset.library.user_source(asset, rig).folders[bmaya.core.asset.library.POSE]
    path = bmaya.maya.assethandlers.save_control_file(
        bmaya.maya.assethandlers.ControlPoseHandler(), asset, rig, "controlposes", name, folder=folder,
        scope=scope, meta=library_meta(asset, scope, tags, description))
    bmaya.core.log.info(f"Saved pose {name!r} of {asset.id}: {path}")
    return path


def save_animation(asset_id: str, name: str, scope: list[str], start_frame: int, end_frame: int,
                   tags: typing.Sequence[str] = (), description: str = "") -> str:
    """Saves the keys of scope (a rig root, or controls of one rig) over start_frame to end_frame to the own library
    of the current user for the scope's rig of the asset, as <name>.controlanim.json in its controlanims folder (a
    ControlAnim, RigModules D42, D51). An existing file is versioned first. Returns the path."""
    asset = bmaya.core.asset.Asset(asset_id)
    rig = rigmodules.query.get_rig_info(scope[0]).rig_name
    folder = bmaya.core.asset.library.user_source(asset, rig).folders[bmaya.core.asset.library.ANIMATION]
    path = bmaya.maya.assethandlers.save_control_file(
        bmaya.maya.assethandlers.ControlAnimHandler(), asset, rig, "controlanims", name, folder=folder,
        scope=scope, start_frame=start_frame, end_frame=end_frame, meta=library_meta(asset, scope, tags, description))
    bmaya.core.log.info(f"Saved animation {name!r} of {asset.id} on frames {start_frame} to {end_frame}: {path}")
    return path


def save_skeleton_export(asset_id: str, rig_root: str) -> tuple[str, str]:
    """Writes the skeleton export of the rig's skeleton, the skeleton asset source for the engine, and its bone map
    into that skeleton's exports folder (skeletons/<skeleton>/exports, in the asset that holds the skeleton). Returns
    the FBX and the bone map."""
    asset = require_asset(asset_id)
    rig = rigmodules.query.get_rig_info(rig_root).rig_name
    fbx, bone_map = bmaya.maya.assethandlers.save_skeleton_export(asset, rig, rig_root)
    bmaya.core.log.info(f"Saved the skeleton export of the rig {rig!r} of {asset.id}: {fbx}")
    return fbx, bone_map


def check_clip_skeleton(asset_id: str, rig: str, fbx: str) -> None:
    """Checks that the animation FBX has the joint names and parents of the skeleton export of the rig's skeleton.
    Raises FileNotFoundError when there is no skeleton export, and ValueError naming every joint that differs."""
    asset = require_asset(asset_id)
    skeleton = bmaya.maya.assethandlers.get_skeleton_export_path(asset, rig)
    if not os.path.isfile(skeleton):
        raise FileNotFoundError(f"The rig {rig!r} of {asset.id} has no skeleton export at {skeleton}. Save it with "
                                f"Save Skeleton Export first.")
    rigmodules.jointclip.check_skeleton_match(fbx, skeleton)
    bmaya.core.log.info(f"{fbx} matches the skeleton of the rig {rig!r} of {asset.id}.")


def set_clip_properties(fbx: str, **changes) -> bmaya.core.asset.animproperties.AnimProperties:
    """Changes fields of the engine properties beside the clip's FBX (loop, root_motion, additive, events, curves),
    starting from the defaults when it has none. Returns the new properties."""
    path = bmaya.core.asset.animproperties.get_path(fbx)
    current = bmaya.core.asset.animproperties.read(path) if os.path.isfile(path) else bmaya.core.asset.animproperties.AnimProperties()
    properties = dataclasses.replace(current, **changes)
    bmaya.core.asset.animproperties.write(path, properties)
    bmaya.core.log.info(f"Saved the clip properties: {path}")
    return properties


def save_skin_weights(node: str, look: str | None = None,
                      prompter: bmaya.core.prompts.Prompter | None = None) -> list[str] | None:
    """Saves the weights of every skinned mesh in the rig's namespace to a look's weights folder in its asset, or to
    a folder the user picks when the asset folder doesn't exist. Skin weights belong to a look, and a built rig
    records the look it wears (RigModules D54), so look is only an override: the rig's look when left out, else the
    asset's only look for the rig's skeleton, and an error when it has several. Returns the files written, or None
    when cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    handler = bmaya.maya.assethandlers.RigSkinWeightsHandler()
    if asset is None:
        folder = _ask_folder(_prompter(prompter), "Save Skin Weights: pick the weights folder")
        return handler.save(None, folder, namespace=info.namespace) if folder else None

    look = _require_look(asset, info.rig_name, look, _worn_look(info))
    bmaya.maya.assethandlers.register()
    path = bmaya.core.asset.handlers.save(asset, "weights", look, namespace=info.namespace)
    bmaya.core.log.info(f"Saved the skin weights of {asset.id} look {look!r}: {path}")
    return handler.files(path)


def load_skin_weights(node: str, look: str | None = None,
                      prompter: bmaya.core.prompts.Prompter | None = None) -> list[str] | None:
    """Loads the weights in a look's weights folder onto the meshes in the rig's namespace, matched by meshId, or
    from a folder the user picks when the asset folder doesn't exist. look is as in save_skin_weights. Returns the
    meshes loaded, or None when cancelled."""
    info = rigmodules.query.get_rig_info(node)
    asset = find_asset(info.asset_id)
    if asset is None:
        folder = _ask_folder(_prompter(prompter), "Load Skin Weights: pick the weights folder")
        handler = bmaya.maya.assethandlers.RigSkinWeightsHandler()
        return handler.load(None, folder, namespace=info.namespace) if folder else None

    look = _require_look(asset, info.rig_name, look, _worn_look(info))
    bmaya.maya.assethandlers.register()
    return bmaya.core.asset.handlers.load(asset, "weights", look, namespace=info.namespace)


def get_rig_looks(asset: bmaya.core.asset.Asset, rig: str) -> list[str]:
    """The looks of the asset that a rig can wear: those whose look.json names the rig's skeleton. Every look when
    the asset has no such rig (a rig built from a template that was never added to the asset)."""
    if rig not in asset.rigs:
        return asset.looks
    return [look for look in asset.looks if asset.look_fits(look, rig)]


def list_rig_looks(asset: bmaya.core.asset.Asset, rig: str) -> list[bmaya.core.asset.AssetLook]:
    """The looks a rig can wear, local or not (RigModules D54 phase 6). A local look is listed when its look.json names
    the rig's skeleton (every one when the asset has no such rig). A look that is not synced can't be read, so it is
    listed as a name and its fit is checked when it is synced, by apply_look."""
    fitting = set(get_rig_looks(asset, rig))
    return [entry for entry in asset.all_looks() if entry.name in fitting or not entry.local]


def _worn_look(info: rigmodules.query.RigInfo) -> str | None:
    """The name of the look the rig wears when it is a look of the rig's own asset, else None."""
    return info.look.name if info.look is not None and info.look.asset_id == info.asset_id else None


def _require_look(asset: bmaya.core.asset.Asset, rig: str, look: str | None, worn: str | None = None) -> str:
    """look when given and the asset has it, else the look the rig wears (worn), else the one look the rig can wear.
    Raises AssetError otherwise."""
    look = look or worn
    if look is not None:
        asset.look(look)   # raises for a look the asset doesn't have
        return look
    looks = get_rig_looks(asset, rig)
    if len(looks) != 1:
        raise bmaya.core.asset.AssetError(
            f"{asset.id} has {len(looks)} looks for the rig {rig!r} ({', '.join(looks) or 'none'}): say which look. "
            f"Add one with New Look when it has none.")
    return looks[0]


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


def new_rig_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    """Asks for the asset, the template to copy, the rig's name (the template's rigName offered) and the skeleton
    the rig is built on, then adds the rig."""
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "New Rig")
    if not asset_id:
        return
    asset = require_asset(asset_id)
    template = prompter.ask_file("New Rig: pick the template", TEMPLATE_FILTER, save=False)
    if not template:
        return
    rig = prompter.ask_text("New Rig", f"Rig name, its folder in {asset_id} and the template's rigName:",
                            rigmodules.template.get_rig_name(template))
    if not rig:
        return
    skeleton = _ask_skeleton(prompter, "New Rig", asset, f"Skeleton the rig {rig!r} is built on:")
    if skeleton:
        new_rig(asset_id, template, rig, skeleton)


def new_look_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    """Asks for the asset, the look's name ("default" offered for its first look) and the skeleton its meshes bind
    to, then adds the look."""
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "New Look")
    if not asset_id:
        return
    asset = require_asset(asset_id)
    look = prompter.ask_text("New Look", f"Look name, its folder in {asset_id}:", "" if asset.looks else DEFAULT_NAME)
    if not look:
        return
    skeleton = _ask_skeleton(prompter, "New Look", asset, f"Skeleton the meshes of the look {look!r} bind to:")
    if skeleton:
        new_look(asset_id, look, skeleton)


def save_skeleton_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    """Asks for the asset and the skeleton's name (its only skeleton, or "default", offered), then saves the scene's
    joints as that skeleton."""
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "Save Skeleton")
    if not asset_id:
        return
    skeletons = require_asset(asset_id).skeletons
    offered = skeletons[0] if len(skeletons) == 1 else ("" if skeletons else DEFAULT_NAME)
    known = f" It has: {', '.join(skeletons)}." if skeletons else ""
    skeleton = prompter.ask_text("Save Skeleton", f"Skeleton name, its folder in {asset_id}.{known}", offered)
    if skeleton:
        save_skeleton(asset_id, skeleton)


def load_skeleton_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    """Asks for the asset and which of its skeletons, then creates its joints in the scene and selects them."""
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "Load Skeleton")
    if not asset_id:
        return
    skeleton = _choose_owner(prompter, "Load Skeleton", asset_id, "skeleton")
    if skeleton:
        cmds.select(load_skeleton(asset_id, skeleton), replace=True)


def save_model_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    """Asks for the asset and which of its looks, then saves the selected meshes, or every mesh in the scene when
    none is selected, as that look's model."""
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "Save Model")
    if not asset_id:
        return
    look = _choose_owner(prompter, "Save Model", asset_id, "look")
    if look:
        selected = [mesh for mesh in cmds.ls(selection=True, long=True) or []
                    if cmds.listRelatives(mesh, shapes=True, type="mesh", noIntermediate=True)]
        save_model(asset_id, look, selected or None)


def build_rig_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    """Asks for the asset and which of its rigs, and for the look only when the rig can wear more than one, then
    builds the rig and selects its rig root."""
    prompter = _prompter(prompter)
    asset_id = _ask_asset_id(prompter, "Build Rig")
    if not asset_id:
        return
    rig = _choose_owner(prompter, "Build Rig", asset_id, "rig")
    if not rig:
        return
    looks = get_rig_looks(require_asset(asset_id), rig)
    look = looks[0] if len(looks) == 1 else None
    if len(looks) > 1:
        look = prompter.choose("Build Rig", f"Look the rig {rig!r} of {asset_id} wears:", looks)
        if not look:
            return
    cmds.select(build_rig(asset_id, rig, look), replace=True)


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

    user = bmaya.core.asset.library.user_source(asset, info.rig_name)
    name = prompter.ask_text("Save Pose", f"Pose name, saved in your own library of the rig {info.rig_name!r} of {asset.id}:",
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
    info = rigmodules.query.get_rig_info(scope[0])
    asset = find_asset(info.asset_id)
    path = _prompter(prompter).ask_file("Load Pose", POSE_FILTER, save=False,
                                        folder=_library_folder(asset, info.rig_name, bmaya.core.asset.library.POSE))
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
    info = rigmodules.query.get_rig_info(scope[0])
    asset = find_asset(info.asset_id)
    if asset is None:
        path = prompter.ask_file("Save Animation", ANIMATION_FILTER, save=True)
        if path:
            cmds.saveRigAnimation(*scope, file=_command_path(path), startFrame=start, endFrame=end)
        return path

    user = bmaya.core.asset.library.user_source(asset, info.rig_name)
    name = prompter.ask_text("Save Animation", f"Animation name, saved in your own library of the rig {info.rig_name!r} of {asset.id}:",
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
    info = rigmodules.query.get_rig_info(scope[0])
    asset = find_asset(info.asset_id)
    path = _prompter(prompter).ask_file("Load Animation", ANIMATION_FILTER, save=False,
                                        folder=_library_folder(asset, info.rig_name, bmaya.core.asset.library.ANIMATION))
    if path:
        bmaya.maya.posetools.load_animation(scope, path, mirror=mirror)
    return path


def save_joint_clip(asset_id: str, name: str, rig_root: str, start_frame: int, end_frame: int) -> str:
    """Captures the rig's export joints over start_frame to end_frame into exports/<name>/<name>.fbx in the exports
    folder of the rig's skeleton, which every rig of that skeleton shares. An existing clip is versioned first.
    Returns the FBX path."""
    asset = require_asset(asset_id)
    rig = rigmodules.query.get_rig_info(rig_root).rig_name
    fbx = bmaya.maya.assethandlers.save_anim_clip(
        asset, rig, name, rig_root=rig_root, start_frame=start_frame, end_frame=end_frame)
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
    fbx = bmaya.maya.assethandlers.AnimClipHandler.fbx_path(bmaya.maya.assethandlers.get_exports_folder(asset, rig.rig_name), name)
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
    rig = bmaya.maya.activerig.get_active_rig()
    asset = find_asset(rig.asset_id)
    path = prompter.ask_file(caption, CLIP_FILTER, save=False, folder=_exports_folder(asset, rig.rig_name))
    if not path:
        return None
    folder, file_name = os.path.split(path)
    return bmaya.maya.assethandlers.AnimClipHandler().load(asset, folder, name=os.path.splitext(file_name)[0])


def _command_path(path: str) -> str:
    return path.replace("\\", "/")


def save_skeleton_export_interactive() -> str | None:
    """Writes the active rig's skeleton export (the export joints at rest, as the skeleton asset source for the
    engine, with its bone map) into the exports folder of its skeleton. Needs the asset's folder. Returns the FBX
    path."""
    rig = bmaya.maya.activerig.get_active_rig()
    fbx, _ = save_skeleton_export(rig.asset_id, rig.rig_root)
    return fbx


def check_clip_skeleton_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Checks an animation FBX the user picks against the skeleton export of the active rig's skeleton. Raises when
    the joints differ, naming them. Returns the FBX path, or None when cancelled."""
    rig = bmaya.maya.activerig.get_active_rig()
    asset = find_asset(rig.asset_id)
    path = _prompter(prompter).ask_file("Check Clip Against Skeleton", CLIP_FILTER, save=False,
                                        folder=_exports_folder(asset, rig.rig_name))
    if path:
        check_clip_skeleton(rig.asset_id, rig.rig_name, path)
    return path


@dataclasses.dataclass(frozen=True)
class ClipSettings:
    """The clip properties Edit Clip Properties asks for. Events and curves are kept as they are."""

    loop: bool = False
    root_motion: bool = False
    additive: typing.Literal[bmaya.core.asset.animproperties.ADDITIVE_TYPES] = "none"


def edit_clip_properties_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    """Sets the engine properties of an exported clip: an FBX the user picks, starting in the exports folder of the
    active rig's skeleton, then loop, root motion and additive type in a form. Events and curves are kept as they
    are. Returns the FBX path, or None when cancelled."""
    prompter = _prompter(prompter)
    rig = bmaya.maya.activerig.get_active_rig()
    asset = find_asset(rig.asset_id)
    path = prompter.ask_file("Edit Clip Properties: pick the clip", CLIP_FILTER, save=False,
                             folder=_exports_folder(asset, rig.rig_name))
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
    """Saves the active rig's skin weights to a look of its asset: the only look the rig can wear, or one the user
    picks."""
    rig = bmaya.maya.activerig.get_active_rig()
    look, cancelled = _ask_rig_look(_prompter(prompter), "Save Skin Weights", rig)
    if not cancelled:
        save_skin_weights(rig.rig_root, look, prompter=prompter)


def load_skin_weights_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> None:
    """Loads a look's skin weights onto the active rig's meshes: the only look the rig can wear, or one the user
    picks."""
    rig = bmaya.maya.activerig.get_active_rig()
    look, cancelled = _ask_rig_look(_prompter(prompter), "Load Skin Weights", rig)
    if not cancelled:
        load_skin_weights(rig.rig_root, look, prompter=prompter)


def _ask_rig_look(prompter: bmaya.core.prompts.Prompter, title: str,
                  rig: rigmodules.query.RigInfo) -> tuple[str | None, bool]:
    """(look, cancelled) for a tool that writes or reads a look's files of the active rig. Asks only when the rig can
    wear more than one look. look is None when there is no asset folder or no choice to make: the plain function then
    decides, and reports an asset with no look."""
    asset = find_asset(rig.asset_id)
    looks = get_rig_looks(asset, rig.rig_name) if asset is not None else []
    if len(looks) < 2:
        return None, False
    look = prompter.choose(title, f"Look of {asset.id}:", looks)
    return look, look is None


# ---- questions the workflows share ----------------------------------------------------------

def _prompter(prompter: bmaya.core.prompts.Prompter | None) -> bmaya.core.prompts.Prompter:
    return prompter or bmaya.core.prompts.current()


def _playback_range() -> tuple[int, int]:
    return int(cmds.playbackOptions(query=True, minTime=True)), int(cmds.playbackOptions(query=True, maxTime=True))


def _exports_folder(asset: bmaya.core.asset.Asset | None, rig: str) -> str:
    """The folder a clip dialog starts in: the exports folder of the rig's skeleton when it exists, else none."""
    if asset is None or rig not in asset.rigs:
        return ""
    folder = bmaya.maya.assethandlers.get_exports_folder(asset, rig)
    return folder if os.path.isdir(folder) else ""


def _library_file(source: bmaya.core.asset.library.LibrarySource, kind: str, name: str) -> str | None:
    """The file of a name in a library source, or None."""
    return bmaya.core.asset.library.find_file(source.folders[kind], kind, name)


def _library_folder(asset: bmaya.core.asset.Asset | None, rig: str, kind: str) -> str:
    """The folder a pose or animation dialog starts in: the user's own library of the rig when it exists, else the
    rig's Approved folder when that does, else none."""
    if asset is None:
        return ""
    for source in reversed(bmaya.core.asset.library.sources(asset, rig)):
        if source.key != bmaya.core.asset.library.SHARED and os.path.isdir(source.folders[kind]):
            return source.folders[kind]
    return ""


def _ask_asset_id(prompter: bmaya.core.prompts.Prompter, title: str,
                  message: str = "Asset id (game\\project\\type\\name):") -> str | None:
    """An asset id, offered as the active rig's asset id when the scene has a rig. Always asks, so the asset a tool
    is about to write to is on screen first."""
    try:
        default = bmaya.maya.activerig.get_active_rig().asset_id
    except RuntimeError:
        default = ""
    return prompter.ask_text(title, message, default)


# What each kind of an asset's parts is listed by, and the tool that adds one.
_OWNER_TOOLS = {"skeleton": "Save Skeleton", "rig": "New Rig", "look": "New Look"}


def _choose_owner(prompter: bmaya.core.prompts.Prompter, title: str, asset_id: str, kind: str) -> str | None:
    """The asset's only skeleton, rig or look (kind), or one the user picks. Raises when it has none."""
    asset = require_asset(asset_id)
    names = {"skeleton": asset.skeletons, "rig": asset.rigs, "look": asset.looks}[kind]
    if not names:
        raise bmaya.core.asset.AssetError(f"{asset_id} has no {kind}s. Add one with {_OWNER_TOOLS[kind]} first.")
    return names[0] if len(names) == 1 else prompter.choose(title, f"{kind.capitalize()} of {asset_id}:", names)


def _ask_skeleton(prompter: bmaya.core.prompts.Prompter, title: str, asset: bmaya.core.asset.Asset,
                  message: str) -> str | None:
    """The name of a skeleton of the asset for a new rig or look: its only skeleton, one the user picks, or a name
    the user types ("default" offered) when it has none saved yet."""
    skeletons = asset.skeletons
    if len(skeletons) == 1:
        return skeletons[0]
    if skeletons:
        return prompter.choose(title, message, skeletons)
    return prompter.ask_text(title, message + " None is saved yet, so name the one it will be.", DEFAULT_NAME)


def _confirm_replace(prompter: bmaya.core.prompts.Prompter, title: str, what: str) -> bool:
    return prompter.confirm(title, f"{what} exists. Replace it? The old file is kept as a local version.",
                            accept="Replace")


def _ask_folder(prompter: bmaya.core.prompts.Prompter, title: str) -> str | None:
    """A folder, starting in the projects root."""
    return prompter.ask_folder(title, os.environ.get(bmaya.core.asset.project.PROJECTS_ROOT_ENV, ""))
