"""Maya save and load handlers for asset file types (bmaya.asset.handlers).

Only formats that exist get a handler: Maya scenes, RigModules templates, shape files, skin weights, control
poses and animations (ControlPose and ControlAnim files) and animation clips (FBX, RigModules D42). Other file types
(textures, shaders, postops) have none yet, so saving or loading them raises NotImplementedError until one is written.

Call register() once per session before handlers.save / handlers.load.

    from bmaya.asset import Asset, handlers
    from bmaya.maya import assethandlers

    assethandlers.register()
    hero = Asset("shooter\\main\\characters\\hero")
    handlers.load(hero, "skeleton")                                  # imports into the hero namespace
    handlers.save(hero, "shapes", variant="game", rig_root="hero:rigRootModule1")
    handlers.save(hero, "weights", variant="game", namespace="hero")
    assethandlers.save_anim_clip(hero, "walk", rig_root="hero:rigRootModule1", start_frame=1, end_frame=48)
    clip = handlers.load(hero, "exports", name="walk")               # an AnimClip, read from exports/walk/walk.fbx
    cmds.animateRigFromJointClip("hero:rigRootModule1", jointClip=clip.joint_clip)
"""

from __future__ import annotations

import dataclasses
import glob
import os
import re
import shutil
import tempfile

import maya.cmds as cmds
import rigmodules.jointclip
import rigmodules.skinweights
import rigmodules.template

import bmaya.core.log

from bmaya.asset import animproperties, handlers, sourcecontrol, versions
from bmaya.asset.asset import Asset

MAYA_FILE_TYPES = ("skeleton", "model", "rig")

# The same rule as a pose name: it becomes a file name.
CLIP_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_ -]*$")
BONE_MAP_SUFFIX = ".bonemap.json"
CONTROL_ANIM_SUFFIX = ".anim.json"


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


@dataclasses.dataclass(frozen=True)
class AnimClip:
    """A clip loaded from an FBX file."""

    name: str
    fbx: str                 # the clip's FBX file
    joint_clip: str          # the JointClip file read from it, a temporary: cmds.animateRigFromJointClip(jointClip=...)
    sidecar: str | None      # the ControlAnim beside the FBX (<name>.anim.json), or None: animateRigFromJointClip(sidecar=...)
    properties: animproperties.AnimProperties | None   # the engine properties beside the FBX, or None


class AnimClipHandler(handlers.FileHandler):
    """Animation clips in an asset's exports folder, which every variant of the asset shares (RigModules D42). A
    clip is an FBX file written through rigmodules.jointclip, in a folder of its own, exports/<name>/<name>.fbx,
    because an export is a bundle: the engine properties go beside it, and so does the control animation it was made
    from, <name>.anim.json, written when a clip is captured from a rig. That ControlAnim is the sidecar of a restore:
    it gives back what joints can't (spaces, blends, Layout controls) with the animator's own keys.
    The engine properties are <name>.animproperties.json (bmaya.asset.animproperties): a clip captured from a rig
    gets the defaults when it has none, and an existing file is never overwritten by a re-export.
    A bone map, <name>.bonemap.json beside an FBX, gives a file from another tool its joint markup."""

    @staticmethod
    def fbx_path(folder: str, name: str, own_folder: bool = True) -> str:
        """Where the clip <name> is in the exports folder `folder`: in a folder of its own, or in `folder` itself."""
        return os.path.join(folder, name, name + ".fbx") if own_folder else os.path.join(folder, name + ".fbx")

    @staticmethod
    def bone_map_path(fbx: str) -> str:
        return os.path.splitext(fbx)[0] + BONE_MAP_SUFFIX

    @staticmethod
    def control_anim_path(fbx: str) -> str:
        return os.path.splitext(fbx)[0] + CONTROL_ANIM_SUFFIX

    @staticmethod
    def names(folder: str) -> list[str]:
        """The clips in an exports folder, sorted."""
        return sorted(
            os.path.basename(os.path.dirname(path)) for path in glob.glob(os.path.join(folder, "*", "*.fbx"))
            if os.path.basename(path) == os.path.basename(os.path.dirname(path)) + ".fbx")

    def save(
        self,
        asset: Asset | None,
        path: str,
        name: str | None = None,
        joint_clip: str | None = None,
        rig_root: str | None = None,
        start_frame: int | None = None,
        end_frame: int | None = None,
        own_folder: bool = True,
        properties: animproperties.AnimProperties | None = None,
        **context,
    ) -> str:
        """Writes the clip <name> into the exports folder at path from a JointClip file (joint_clip), or captured
        from the rig's export joints over start_frame to end_frame (rig_root). own_folder=False writes
        <path>/<name>.fbx itself, for a file the user chose. Returns the FBX path. Nothing is written when an
        argument is wrong. A clip captured from a rig also gets its ControlAnim beside it. properties are written
        as the clip's engine properties (replacing a file there). Without them an export folder's clip gets the
        defaults when it has no file, and an existing file is kept. A file chosen in a dialog gets none."""
        name = _require_clip_name(name)
        if (joint_clip is None) == (rig_root is None):
            raise ValueError("Pass joint_clip (a JointClip file), or rig_root with start_frame and end_frame.")
        if rig_root is not None and (start_frame is None or end_frame is None):
            raise ValueError("Capturing from a rig needs start_frame and end_frame.")

        captured = None
        if rig_root is not None:
            handle, captured = tempfile.mkstemp(prefix=name + "_", suffix=".jointclip.json")
            os.close(handle)
            joint_clip = captured
        try:
            if captured:
                rigmodules.jointclip.capture_joint_clip(rig_root, start_frame, end_frame, captured)
            fbx = self.fbx_path(path, name, own_folder)
            os.makedirs(os.path.dirname(fbx), exist_ok=True)
            rigmodules.jointclip.write_fbx(joint_clip, fbx)
            properties_path = animproperties.get_path(fbx)
            if properties is not None or (own_folder and not os.path.exists(properties_path)):
                animproperties.write(properties_path, properties or animproperties.AnimProperties())
            if captured:
                cmds.saveRigAnimation(
                    rig_root, file=self.control_anim_path(fbx).replace("\\", "/"), startFrame=start_frame, endFrame=end_frame)
        finally:
            if captured and os.path.exists(captured):
                os.remove(captured)
        return fbx

    def load(
        self,
        asset: Asset | None,
        path: str,
        name: str | None = None,
        joint_clip: str | None = None,
        bone_map: str | None = None,
        **context,
    ) -> AnimClip:
        """Reads the clip <name> from the folder at path into a JointClip file (joint_clip, or a file named after
        the clip in a temporary folder that the next load of the same name overwrites). The FBX is
        <path>/<name>/<name>.fbx (an exports folder) or <path>/<name>.fbx (a folder of FBX files, such as the
        one a file dialog chose from), so a file from another tool loads too. Its bone map is bone_map, or the
        one beside the FBX when there is one."""
        if not name:
            raise ValueError("Pass name, the clip's file name without .fbx.")
        fbx = next((candidate for candidate in (self.fbx_path(path, name), self.fbx_path(path, name, False))
                    if os.path.isfile(candidate)), None)
        if fbx is None:
            raise FileNotFoundError(f"{path} has no clip {name!r}. It has: {', '.join(self.names(path)) or 'none'}.")
        if joint_clip is None:
            folder = os.path.join(tempfile.gettempdir(), "bmaya_joint_clips")
            os.makedirs(folder, exist_ok=True)
            joint_clip = os.path.join(folder, name + ".json")
        if bone_map is None and os.path.isfile(self.bone_map_path(fbx)):
            bone_map = self.bone_map_path(fbx)
        rigmodules.jointclip.read_fbx(fbx, joint_clip, bone_map)
        control_anim = self.control_anim_path(fbx)
        properties = animproperties.get_path(fbx)
        return AnimClip(
            name, fbx, joint_clip, control_anim if os.path.isfile(control_anim) else None,
            animproperties.read(properties) if os.path.isfile(properties) else None)


class ControlDataHandler(handlers.FileHandler):
    """A folder of control data files, <name>.json (RigModules D42): ControlPoses in controlposes and ControlAnims in
    controlanims. Control data is bound to a rig's controls by markup, so a file works on any rig of the asset's
    skeleton. A subclass names the commands and what its file is called (kind). The scope is a rig root, or controls
    of one rig."""

    kind = "control data"

    def _write(self, scope: list[str], file: str, **context) -> None:
        raise NotImplementedError

    def _read(self, scope: list[str], file: str, **context) -> list[str]:
        raise NotImplementedError

    @staticmethod
    def file_path(folder: str, name: str) -> str:
        return os.path.join(folder, name + ".json")

    @staticmethod
    def names(folder: str) -> list[str]:
        """The files in a control data folder, sorted."""
        return sorted(os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(folder, "*.json")))

    def save(self, asset: Asset | None, path: str, name: str | None = None, scope: list[str] | None = None, **context) -> str:
        """Writes <path>/<name>.json from the controls in scope. Returns the file."""
        file = self.file_path(path, _require_clip_name(name, self.kind))
        if not scope:
            raise ValueError("Pass scope: a rig root, or controls of one rig.")
        os.makedirs(path, exist_ok=True)
        self._write(scope, file.replace("\\", "/"), **context)
        return file

    def load(self, asset: Asset | None, path: str, name: str | None = None, scope: list[str] | None = None, **context) -> list[str]:
        """Loads <path>/<name>.json onto the controls in scope. Returns the controls the command changed."""
        file = self.file_path(path, name or "")
        if not name or not os.path.isfile(file):
            raise FileNotFoundError(f"{path} has no file {name!r}. It has: {', '.join(self.names(path)) or 'none'}.")
        if not scope:
            raise ValueError("Pass scope: a rig root, or controls of one rig.")
        return self._read(scope, file.replace("\\", "/"), **context) or []


class ControlPoseHandler(ControlDataHandler):
    """ControlPoses (cmds.saveRigPose, cmds.loadRigPose)."""

    kind = "pose"

    def _write(self, scope: list[str], file: str, **context) -> None:
        cmds.saveRigPose(*scope, file=file)

    def _read(self, scope: list[str], file: str, **context) -> list[str]:
        return cmds.loadRigPose(*scope, file=file)


class ControlAnimHandler(ControlDataHandler):
    """ControlAnims (cmds.saveRigAnimation, cmds.loadRigAnimation). Save takes start_frame and end_frame, load takes
    offset and mirror."""

    kind = "animation"

    def _write(self, scope: list[str], file: str, start_frame: int | None = None, end_frame: int | None = None, **context) -> None:
        if start_frame is None or end_frame is None:
            raise ValueError("A ControlAnim needs start_frame and end_frame.")
        cmds.saveRigAnimation(*scope, file=file, startFrame=start_frame, endFrame=end_frame)

    def _read(self, scope: list[str], file: str, offset: int = 0, mirror: bool = False, **context) -> list[str]:
        return cmds.loadRigAnimation(*scope, file=file, offset=offset, mirror=mirror)


class SourceClipHandler(AnimClipHandler):
    """Skeleton data brought in from other tools (a mocap take, a vendor skeleton) in the asset's sources folder.
    It loads like a clip, with the bone map beside the FBX, and never saves: the files come from outside."""

    def save(self, asset: Asset | None, path: str, **context) -> None:
        raise NotImplementedError("Sources are brought in from other tools: copy the FBX (and its bone map) into the sources folder.")


def save_control_file(handler: ControlDataHandler, asset: Asset, folder_type: str, name: str, **context) -> str:
    """Saves a control data file of an asset through its handler, as save_anim_clip saves a clip: versions and checks
    out only that file first, and adds a new one to source control. Returns the file."""
    folder = asset.path(folder_type)
    file = handler.file_path(folder, _require_clip_name(name, handler.kind))
    existing = os.path.exists(file)
    if existing:
        versions.version(file, asset.root)
        sourcecontrol.current().checkout(file)
    handler.save(asset, folder, name=name, **context)
    if not existing:
        sourcecontrol.current().add(file)
    return file


def save_skeleton_export(asset: Asset, rig_root: str) -> tuple[str, str]:
    """Writes the engine's skeleton asset source into the asset's exports folder: <name>_skeleton.fbx, the rig's
    export joints at rest, and <name>_skeleton.bonemap.json beside it, with the asset's id and its skeleton's id
    (RigModules D42). Existing files are versioned first. Returns the FBX and the bone map."""
    fbx = get_skeleton_export_path(asset)
    bone_map = AnimClipHandler.bone_map_path(fbx)
    existing = [path for path in (fbx, bone_map) if os.path.exists(path)]
    for path in existing:
        versions.version(path, asset.root)
        sourcecontrol.current().checkout(path)
    os.makedirs(os.path.dirname(fbx), exist_ok=True)
    rigmodules.jointclip.write_skeleton_fbx(rig_root, asset.skeleton, fbx, bone_map)
    for path in (fbx, bone_map):
        if path not in existing:
            sourcecontrol.current().add(path)
    return fbx, bone_map


def get_skeleton_export_path(asset: Asset) -> str:
    """Where the asset's skeleton export FBX is, or will be. It sits in the exports folder itself, so it is not a
    clip (clips are folders)."""
    return os.path.join(asset.path("exports"), f"{asset.name}_skeleton.fbx")


def save_anim_clip(asset: Asset, name: str, **context) -> str:
    """Saves a clip through AnimClipHandler.save (its arguments go in context). Versions and checks out only the
    clip's own FBX first, where handlers.save would copy the whole exports folder, and adds a new file to source
    control. Returns the FBX path."""
    handler = AnimClipHandler()
    fbx = handler.fbx_path(asset.path("exports"), _require_clip_name(name))
    existing = os.path.exists(fbx)
    if existing:
        versions.version(fbx, asset.root)
        sourcecontrol.current().checkout(fbx)
    fbx = handler.save(asset, asset.path("exports"), name=name, **context)
    if not existing and os.path.exists(fbx):
        sourcecontrol.current().add(fbx)
    return fbx


def _short_name(node: str) -> str:
    return node.split("|")[-1].split(":")[-1]


def _require_namespace(namespace: str | None) -> str:
    if namespace is None:
        raise ValueError("Skin weights belong to the meshes in one namespace: pass namespace.")
    return namespace


def _require_clip_name(name: str | None, kind: str = "clip") -> str:
    if not name or not CLIP_NAME.match(name):
        raise ValueError(f"{name!r} is not a {kind} name: use letters, digits, spaces, '_' and '-'.")
    return name


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
    handlers.register("exports", AnimClipHandler())
    handlers.register("sources", SourceClipHandler())
    handlers.register("controlposes", ControlPoseHandler())
    handlers.register("controlanims", ControlAnimHandler())
