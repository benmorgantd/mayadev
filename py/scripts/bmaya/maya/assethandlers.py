"""Maya save and load handlers for asset file types (bmaya.core.asset.handlers).

Only formats that exist get a handler: skeleton files, model files (meshes only), rig scenes, RigModules templates,
shape files, skin weights, texture folders, control poses and animations (ControlPose and ControlAnim files) and
animation clips (FBX, RigModules D42). Other file types (shaders, postops) have none yet, so saving or loading them raises
NotImplementedError until one is written.

A file belongs to a skeleton, a rig or a look of the asset (RigModules D54), named as the third argument.

Call register() once per session before handlers.save / handlers.load.

    from bmaya.core.asset import Asset, handlers
    from bmaya.maya import assethandlers

    assethandlers.register()
    hero = Asset("shooter\\main\\characters\\hero")
    handlers.load(hero, "skeleton", "default", namespace="hero_body")   # creates the joints from skeleton.json
    handlers.save(hero, "shapes", "body", rig_root="hero_body:rigRootModule1")
    handlers.save(hero, "model", "winter", meshes=["hero_body:body_geo"])    # meshes only: no skinning, no history
    handlers.save(hero, "weights", "winter", namespace="hero_body")
    assethandlers.save_anim_clip(hero, "body", "walk", rig_root="hero_body:rigRootModule1", start_frame=1, end_frame=48)
    clip = handlers.load(hero, "exports", "default", name="walk")    # an AnimClip, read from exports/walk/walk.fbx
    cmds.animateRigFromJointClip("hero_body:rigRootModule1", jointClip=clip.joint_clip)
"""

from __future__ import annotations

import dataclasses
import glob
import json
import os
import tempfile

import maya.cmds as cmds
import rigmodules.jointclip
import rigmodules.skinweights

import bmaya.core.log

from bmaya.core.asset import animproperties, handlers, library, sourcecontrol, versions
from bmaya.core.asset.asset import Asset

# The namespace a model's meshes are copied into while they are exported, so the file is written without it.
MODEL_EXPORT_NAMESPACE = "bmaya_model_export"

# The same rule as a pose name: it becomes a file name.
CLIP_NAME = library.NAME_RULE
BONE_MAP_SUFFIX = ".bonemap.json"
# The ControlAnim beside an exported clip is named as one in a library. Clips captured before D51 have <name>.anim.json.
CONTROL_ANIM_SUFFIX = library.SUFFIX[library.ANIMATION]
LEGACY_CONTROL_ANIM_SUFFIX = ".anim.json"


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


class ModelHandler(MayaSceneHandler):
    """A look's model file: meshes only, with no joints, no skinCluster and no history (RigModules D54). The skinning
    is the look's weight files, loaded onto a rig's joints after the meshes are imported. Load imports it, as any
    scene."""

    def save(self, asset: Asset | None, path: str, meshes: list[str] | None = None, **context) -> None:
        """Exports meshes (mesh transforms, or every visible mesh in the scene) to path. Each is exported from its
        undeformed shape, so a posed rig doesn't matter, at the top level of the file under its own short name, with
        its meshId and no shading (the look's textures file owns it). The scene is not saved, renamed or changed."""
        meshes = list(meshes) if meshes else get_scene_meshes()
        if not meshes:
            raise RuntimeError("There are no meshes to save as a model.")
        export_meshes(meshes, path)


def get_scene_meshes() -> list[str]:
    """Every visible mesh's transform in the scene, as long names, sorted."""
    shapes = cmds.ls(type="mesh", noIntermediate=True, long=True) or []
    return sorted({cmds.listRelatives(shape, parent=True, fullPath=True)[0] for shape in shapes})


def export_meshes(meshes: list[str], path: str) -> None:
    """Writes mesh transforms to a Maya ASCII file as meshes only. Each mesh is copied into a scratch namespace, the
    copy takes the mesh's original (undeformed) geometry and loses its history, and the copies are exported at the
    top level with that namespace left out of every name. They are on the default shading group: the look's textures
    file builds the shading when the look is applied. The scratch namespace and everything in it is deleted
    afterwards, and the current namespace and the selection are restored."""
    names = [_short_name(mesh) for mesh in meshes]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise RuntimeError("A model file holds each mesh under its own name, and these are used twice: " + ", ".join(repeated))
    scratch = ":" + MODEL_EXPORT_NAMESPACE
    if cmds.namespace(exists=scratch):
        raise RuntimeError(f"The namespace {MODEL_EXPORT_NAMESPACE!r} is in use. Remove it and save the model again.")

    selection = cmds.ls(selection=True, long=True)
    current = cmds.namespaceInfo(currentNamespace=True, absoluteName=True)
    cmds.namespace(add=scratch)
    try:
        # A duplicate is made in the current namespace under its source's own name, which is what keeps the names.
        cmds.namespace(setNamespace=scratch)
        copies = [_copy_mesh_for_export(mesh) for mesh in meshes]
        cmds.select(copies, replace=True)
        cmds.file(path, exportSelected=True, type="mayaAscii", force=True, relativeNamespace=scratch,
                  constructionHistory=False, channels=False, constraints=False, expressions=False, shader=False,
                  preserveReferences=False)
    finally:
        cmds.namespace(setNamespace=current)
        cmds.namespace(removeNamespace=scratch, deleteNamespaceContent=True)
        cmds.select(cmds.ls(selection, long=True), replace=True)


def _copy_mesh_for_export(mesh: str) -> str:
    """A copy of a mesh transform at the top level of the current namespace, with the mesh's original geometry, no
    history and no material: a look's shading is the textures file's (bmaya.maya.assettextures), so the model holds
    meshes only. Returns the copy."""
    shapes = [shape for shape in cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
              if cmds.nodeType(shape) == "mesh" and not cmds.getAttr(shape + ".intermediateObject")]
    if len(shapes) != 1:
        raise RuntimeError(f"{mesh} is not a transform with one mesh shape.")
    # The geometry before any deformer: the skinCluster's bind shape. "" for a mesh nothing deforms.
    original = (cmds.deformableShape(shapes[0], originalGeometry=True) or [""])[0]

    copy = cmds.ls(cmds.duplicate(mesh), long=True)[0]
    if cmds.listRelatives(copy, parent=True):
        copy = cmds.ls(cmds.parent(copy, world=True), long=True)[0]
    copy_shape = None
    for child in cmds.listRelatives(copy, children=True, fullPath=True) or []:
        if cmds.nodeType(child) == "mesh" and not cmds.getAttr(child + ".intermediateObject"):
            copy_shape = child
        else:
            cmds.delete(child)   # the duplicate's intermediate shapes, and anything parented under the mesh
    if original:
        cmds.connectAttr(original, copy_shape + ".inMesh", force=True)
        cmds.polyEvaluate(copy_shape, vertex=True)   # pulls the geometry in, so it stays when the input goes
        cmds.disconnectAttr(original, copy_shape + ".inMesh")

    cmds.sets(copy_shape, edit=True, forceElement="initialShadingGroup")   # the copy keeps its material otherwise
    return copy


class RigSkeletonHandler(handlers.FileHandler):
    """A skeleton file, skeleton.json: the only form a skeleton is stored in (RigModules D54). There is no skeleton
    scene. Saving serializes joints and loading creates them, through RigModules' commands."""

    def save(self, asset: Asset | None, path: str, joints: list[str] | None = None, **context) -> str:
        """Writes the joints to path as they are now, so they should be at rest. Every one must carry joint markup.
        Returns the skeleton hash."""
        if not joints:
            raise ValueError("Pass joints, the joints of the skeleton.")
        return cmds.saveRigSkeleton(*joints, file=path.replace("\\", "/"))

    def load(self, asset: Asset | None, path: str, namespace: str | None = None, **context) -> list[str]:
        """Creates the file's joints, at rest and marked, in namespace (the current one when left out). Returns
        them."""
        flags = {"namespace": namespace} if namespace is not None else {}
        return cmds.loadRigSkeleton(file=path.replace("\\", "/"), **flags) or []


class RigShapesHandler(handlers.FileHandler):
    """A RigModules control shape file, through its own commands. Needs the rig root."""

    def save(self, asset: Asset, path: str, rig_root: str | None = None, **context) -> None:
        cmds.saveRigControlShapes(_require_rig_root(rig_root), file=path)

    def load(self, asset: Asset, path: str, rig_root: str | None = None, **context) -> list[str]:
        return cmds.loadRigControlShapes(_require_rig_root(rig_root), file=path) or []


class RigTemplateHandler(handlers.FileHandler):
    """A RigModules rig template, the template.json in a rig's folder (RigModules D29, D54)."""

    def save(self, asset: Asset, path: str, owner: str | None = None, source: str | None = None, **context) -> None:
        """Writes the template file at source into the rig's folder with its rigName set to the rig's name (owner),
        because a rig built from it is found by rigName, and RigModules names its namespace by it. Templates are
        shared between assets, so the source's own rigName is whatever the last asset called it. The file is written
        again as JSON: the keys keep their order, hand formatting inside it does not survive."""
        if not source:
            raise ValueError("Pass source, the template file to copy into the asset.")
        if not owner:
            raise ValueError("A template belongs to a rig: pass the rig's name.")
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"{source} is not a rig template: it is not a JSON object.")
        data["rigName"] = owner
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=_json_indent(text))
            handle.write("\n")

    def load(self, asset: Asset, path: str, **context) -> str:
        """The template's path, for cmds.createRigFromTemplate(template=...)."""
        return path


class RigSkinWeightsHandler(handlers.FileHandler):
    """A look's skin weights: a folder with one RigModules weight file per skinned mesh, named after the mesh.
    Files are matched to meshes by the meshId inside them, not by name, so a renamed mesh still loads. load(by_name=True)
    is the one exception, the repair for meshes whose ids changed (RigModules D68). Needs the namespace the meshes are
    in."""

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

    def load(self, asset: Asset | None, path: str, namespace: str | None = None, by_name: bool = False,
             **context) -> list[str]:
        """Loads every weight file in the folder at path onto the mesh in namespace with its meshId, as one undo
        step. A file whose mesh isn't in the scene is skipped with a warning. Returns the meshes loaded.

        by_name matches each file to the mesh named as the file's meshName instead (RigModules D68), for meshes whose
        ids changed since the weights were saved, and gives that mesh the file's meshId so the weights load. The ids
        it changed are logged: save the model so the next build matches them by meshId. A file whose mesh has another
        mesh's id taken already is skipped with a warning."""
        namespace = _require_namespace(namespace)
        files: dict[str, str] = {}
        for file_path in self.files(path):
            mesh_id = rigmodules.skinweights.read_file_mesh_id(file_path)
            if mesh_id in files:
                raise RuntimeError(f"{files[mesh_id]} and {file_path} are both for meshId {mesh_id}. Remove the old one.")
            files[mesh_id] = file_path
        meshes = rigmodules.skinweights.get_meshes(namespace)
        by_names = rigmodules.skinweights.get_meshes_by_name(namespace) if by_name else {}

        loaded, changed = [], []
        cmds.undoInfo(openChunk=True, chunkName="Load Skin Weights by Name" if by_name else "Load Skin Weights")
        try:
            for mesh_id, file_path in sorted(files.items(), key=lambda item: item[1]):
                if by_name:
                    mesh = self._take_id_by_name(file_path, mesh_id, namespace, meshes, by_names, changed)
                else:
                    mesh = meshes.get(mesh_id)
                    if mesh is None:
                        bmaya.core.log.warning(f"No mesh in namespace {namespace!r} has meshId {mesh_id}: skipped {file_path}")
                if mesh is None:
                    continue
                cmds.loadRigSkinWeights(mesh, file=file_path.replace("\\", "/"))
                loaded.append(mesh)
        finally:
            cmds.undoInfo(closeChunk=True)
        if changed:
            bmaya.core.log.warning("These meshes took their weight file's meshId: " + ", ".join(changed)
                                   + ". Save the model so the next build matches them by meshId.")
        return loaded

    @staticmethod
    def _take_id_by_name(file_path: str, mesh_id: str, namespace: str, meshes: dict[str, str],
                         by_names: dict[str, str], changed: list[str]) -> str | None:
        """The mesh named as the weight file's meshName, given the file's meshId when it has another (meshes, the id
        map, follows). None, with a warning, when there is no such mesh or another mesh has the id already."""
        name = rigmodules.skinweights.read_file_mesh_name(file_path)
        mesh = by_names.get(name)
        if mesh is None:
            bmaya.core.log.warning(f"No mesh in namespace {namespace!r} is named {name!r}: skipped {file_path}")
            return None
        current = rigmodules.skinweights.get_mesh_id(mesh)
        if current == mesh_id:
            return mesh
        holder = meshes.get(mesh_id)
        if holder is not None:
            bmaya.core.log.warning(f"{_short_name(holder)} already has meshId {mesh_id}, so {_short_name(mesh)} can't "
                                   f"take it: skipped {file_path}")
            return None
        rigmodules.skinweights.set_mesh_id(mesh, mesh_id)
        meshes.pop(current, None)
        meshes[mesh_id] = mesh
        changed.append(f"{_short_name(mesh)} ({current or 'no id'} -> {mesh_id})")
        return mesh


TEXTURE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".tga", ".exr", ".hdr", ".psd", ".bmp", ".tx")


class TexturesHandler(handlers.FileHandler):
    """A look's textures: a folder of image files the artist puts there. Nothing is written in a format of ours, so Save
    only makes the folder (handlers.save has already made it) and Load returns the texture files in it, as paths."""

    @staticmethod
    def files(folder: str) -> list[str]:
        """The texture files directly in a textures folder, sorted. Other files and subfolders are not listed."""
        if not os.path.isdir(folder):
            return []
        return sorted(os.path.join(folder, name) for name in os.listdir(folder)
                      if name.lower().endswith(TEXTURE_EXTENSIONS) and os.path.isfile(os.path.join(folder, name)))

    def save(self, asset: Asset | None, path: str, **context) -> None:
        os.makedirs(path, exist_ok=True)

    def load(self, asset: Asset | None, path: str, **context) -> list[str]:
        return self.files(path)


@dataclasses.dataclass(frozen=True)
class AnimClip:
    """A clip loaded from an FBX file."""

    name: str
    fbx: str                 # the clip's FBX file
    joint_clip: str          # the JointClip file read from it, a temporary: cmds.animateRigFromJointClip(jointClip=...)
    sidecar: str | None      # the ControlAnim beside the FBX (<name>.controlanim.json), or None: animateRigFromJointClip(sidecar=...)
    properties: animproperties.AnimProperties | None   # the engine properties beside the FBX, or None


class AnimClipHandler(handlers.FileHandler):
    """Animation clips in a skeleton's exports folder, skeletons/<skeleton>/exports, which every rig of the skeleton
    shares (RigModules D42, D54): an animation FBX is skeleton data and targets one skeleton. A
    clip is an FBX file written through rigmodules.jointclip, in a folder of its own, exports/<name>/<name>.fbx,
    because an export is a bundle: the engine properties go beside it, and so does the control animation it was made
    from, <name>.controlanim.json, written when a clip is captured from a rig. That ControlAnim is the sidecar of a restore:
    it gives back what joints can't (spaces, blends, Layout controls) with the animator's own keys.
    The engine properties are <name>.animproperties.json (bmaya.core.asset.animproperties): a clip captured from a rig
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
        legacy = os.path.splitext(fbx)[0] + LEGACY_CONTROL_ANIM_SUFFIX
        if not os.path.isfile(control_anim) and os.path.isfile(legacy):
            control_anim = legacy
        properties = animproperties.get_path(fbx)
        return AnimClip(
            name, fbx, joint_clip, control_anim if os.path.isfile(control_anim) else None,
            animproperties.read(properties) if os.path.isfile(properties) else None)


class ControlDataHandler(handlers.FileHandler):
    """A folder of control data files (RigModules D42, D51): ControlPoses, <name>.controlpose.json, in controlposes and
    ControlAnims, <name>.controlanim.json, in controlanims. A file written before the suffixes, <name>.json, still
    loads and is listed. Control data is bound to a rig's controls by markup, which is unique per rig, so the folders
    belong to a rig. A subclass names the commands and what its file is called (kind). The scope is a rig root, or controls
    of one rig. Save takes meta, a dict for the file's meta block (author, tags, ...), and the rig fills the rest."""

    kind = "control data"

    def _write(self, scope: list[str], file: str, **context) -> None:
        raise NotImplementedError

    def _read(self, scope: list[str], file: str, **context) -> list[str]:
        raise NotImplementedError

    @classmethod
    def file_path(cls, folder: str, name: str) -> str:
        """Where a file called name is written: <name>.controlpose.json or <name>.controlanim.json."""
        return library.file_path(folder, cls.kind, name)

    @classmethod
    def names(cls, folder: str) -> list[str]:
        """The files in a control data folder, sorted."""
        return [item.name for item in library.list_files(
            library.LibrarySource("", "", {cls.kind: folder}, False), cls.kind)]

    def save(self, asset: Asset | None, path: str, name: str | None = None, scope: list[str] | None = None, **context) -> str:
        """Writes <path>/<name>.controlpose.json (or .controlanim.json) from the controls in scope. Returns the file."""
        file = self.file_path(path, _require_clip_name(name, self.kind))
        if not scope:
            raise ValueError("Pass scope: a rig root, or controls of one rig.")
        os.makedirs(path, exist_ok=True)
        self._write(scope, file.replace("\\", "/"), **context)
        return file

    def load(self, asset: Asset | None, path: str, name: str | None = None, scope: list[str] | None = None, **context) -> list[str]:
        """Loads <path>/<name>.controlpose.json (or a legacy <name>.json) onto the controls in scope. Returns the
        controls the command changed."""
        file = library.find_file(path, self.kind, name) if name else None
        if file is None:
            raise FileNotFoundError(f"{path} has no file {name!r}. It has: {', '.join(self.names(path)) or 'none'}.")
        if not scope:
            raise ValueError("Pass scope: a rig root, or controls of one rig.")
        return self._read(scope, file.replace("\\", "/"), **context) or []


class ControlPoseHandler(ControlDataHandler):
    """ControlPoses (cmds.saveRigPose, cmds.loadRigPose)."""

    kind = library.POSE

    def _write(self, scope: list[str], file: str, meta: dict | None = None, **context) -> None:
        cmds.saveRigPose(*scope, file=file, **_meta_flag(meta))

    def _read(self, scope: list[str], file: str, mirror: bool = False, **context) -> list[str]:
        return cmds.loadRigPose(*scope, file=file, mirror=mirror)


class ControlAnimHandler(ControlDataHandler):
    """ControlAnims (cmds.saveRigAnimation, cmds.loadRigAnimation). Save takes start_frame and end_frame, load takes
    offset and mirror."""

    kind = library.ANIMATION

    def _write(self, scope: list[str], file: str, start_frame: int | None = None, end_frame: int | None = None,
               meta: dict | None = None, **context) -> None:
        if start_frame is None or end_frame is None:
            raise ValueError("A ControlAnim needs start_frame and end_frame.")
        cmds.saveRigAnimation(*scope, file=file, startFrame=start_frame, endFrame=end_frame, **_meta_flag(meta))

    def _read(self, scope: list[str], file: str, offset: int = 0, mirror: bool = False, **context) -> list[str]:
        return cmds.loadRigAnimation(*scope, file=file, offset=offset, mirror=mirror)


class SourceClipHandler(AnimClipHandler):
    """Skeleton data brought in from other tools (a mocap take, a vendor skeleton) in the asset's sources folder.
    It loads like a clip, with the bone map beside the FBX, and never saves: the files come from outside."""

    def save(self, asset: Asset | None, path: str, **context) -> None:
        raise NotImplementedError("Sources are brought in from other tools: copy the FBX (and its bone map) into the sources folder.")


def _meta_flag(meta: dict | None) -> dict:
    """The meta keyword of a save command, as the command takes it (a JSON object), or nothing."""
    return {"meta": json.dumps(meta)} if meta else {}


def save_control_file(handler: ControlDataHandler, asset: Asset, rig: str, folder_type: str, name: str,
                      folder: str | None = None, **context) -> str:
    """Saves a control data file of a rig of an asset through its handler, as save_anim_clip saves a clip: versions
    and checks out only that file first, and adds a new one to source control. folder is where it goes, the rig's
    folder for folder_type when left out. A file saved to another folder (the user's own library) is versioned but
    never goes to source control, because nobody tracks it. Returns the file."""
    tracked = folder is None
    folder = folder or asset.path(folder_type, rig)
    file = handler.file_path(folder, _require_clip_name(name, handler.kind))
    existing = os.path.exists(file)
    if existing:
        versions.version(file, asset.root)
        if tracked:
            sourcecontrol.current().checkout(file)
    handler.save(asset, folder, name=name, **context)
    if tracked and not existing:
        sourcecontrol.current().add(file)
    return file


def get_exports_folder(asset: Asset, rig: str) -> str:
    """The exports folder of the skeleton a rig is built on, skeletons/<skeleton>/exports. It is in the asset that
    holds the skeleton, which may be another asset, so every rig of one skeleton shares one folder."""
    skeleton_asset, skeleton = asset.skeleton_of(rig)
    return skeleton_asset.path("exports", skeleton)


def save_skeleton_export(asset: Asset, rig: str, rig_root: str) -> tuple[str, str]:
    """Writes the engine's skeleton asset source into the exports folder of the rig's skeleton:
    <name>_<skeleton>_skeleton.fbx, the rig's export joints at rest, and its .bonemap.json beside it, with the rig's
    asset id and its skeleton's name (RigModules D42, D54). Existing files are versioned first. Returns the FBX and
    the bone map."""
    skeleton_asset, skeleton = asset.skeleton_of(rig)
    fbx = get_skeleton_export_path(asset, rig)
    bone_map = AnimClipHandler.bone_map_path(fbx)
    existing = [path for path in (fbx, bone_map) if os.path.exists(path)]
    for path in existing:
        versions.version(path, skeleton_asset.root)
        sourcecontrol.current().checkout(path)
    os.makedirs(os.path.dirname(fbx), exist_ok=True)
    rigmodules.jointclip.write_skeleton_fbx(rig_root, skeleton, fbx, bone_map)
    for path in (fbx, bone_map):
        if path not in existing:
            sourcecontrol.current().add(path)
    return fbx, bone_map


def get_skeleton_export_path(asset: Asset, rig: str) -> str:
    """Where the skeleton export FBX of a rig's skeleton is, or will be. It sits in the exports folder itself, so it
    is not a clip (clips are folders)."""
    skeleton_asset, skeleton = asset.skeleton_of(rig)
    return os.path.join(get_exports_folder(asset, rig), f"{skeleton_asset.name}_{skeleton}_skeleton.fbx")


def save_anim_clip(asset: Asset, rig: str, name: str, **context) -> str:
    """Saves a clip of a rig through AnimClipHandler.save (its arguments go in context) into the exports folder of the
    rig's skeleton. Versions and checks out only the clip's own FBX first, where handlers.save would copy the whole
    exports folder, and adds a new file to source control. Returns the FBX path."""
    handler = AnimClipHandler()
    folder = get_exports_folder(asset, rig)
    fbx = handler.fbx_path(folder, _require_clip_name(name))
    existing = os.path.exists(fbx)
    if existing:
        versions.version(fbx, asset.root)
        sourcecontrol.current().checkout(fbx)
    fbx = handler.save(asset, folder, name=name, **context)
    if not existing and os.path.exists(fbx):
        sourcecontrol.current().add(fbx)
    return fbx


def _json_indent(text: str) -> int:
    """The indent a JSON file was written with: the leading spaces of its first indented line, 4 when it has none."""
    for line in text.splitlines():
        stripped = line.lstrip(" ")
        if stripped and len(stripped) != len(line):
            return len(line) - len(stripped)
    return 4


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
    handlers.register("skeleton", RigSkeletonHandler())
    handlers.register("model", ModelHandler())
    handlers.register("rig", MayaSceneHandler())
    handlers.register("shapes", RigShapesHandler())
    handlers.register("weights", RigSkinWeightsHandler())
    handlers.register("textures", TexturesHandler())
    handlers.register("template", RigTemplateHandler())
    handlers.register("exports", AnimClipHandler())
    handlers.register("sources", SourceClipHandler())
    handlers.register("controlposes", ControlPoseHandler())
    handlers.register("controlanims", ControlAnimHandler())
