"""The Asset Editor's Files tab view-model: one row per file of the chosen asset, and Save and Load for each
(RigModules design/asset-editor.md, D61).

No Qt. A view connects to changed and reads rows and message. Every command is a call into assettools or the asset
handlers, so mayapy and tests run what the buttons do. A row says whether its file exists, when it changed and how
many local version copies it has, and why Save or Load is not possible right now.

What each file type needs from the scene is the table at the bottom (ACTIONS): a skeleton needs joints, a model needs
meshes and a look, weights need the rig. A file type with its own action there gets a row, so a new one (textures,
shaders, tracked high-res files) is a FileAction and a handler, with no change to the window.
"""

from __future__ import annotations

import dataclasses
import json
import os
from collections.abc import Callable

import maya.cmds as cmds
import rigmodules.query

import bmaya.core.asset
import bmaya.core.asset.context
import bmaya.core.asset.handlers
import bmaya.core.asset.lookstatus
import bmaya.core.asset.publishing
import bmaya.core.asset.textures
import bmaya.core.asset.versions
import bmaya.core.log
import bmaya.core.observable
import bmaya.core.prompts
import bmaya.maya.assethandlers
import bmaya.maya.assettools

DEFAULT_NAME = bmaya.core.asset.context.DEFAULT_NAME


@dataclasses.dataclass(frozen=True)
class FileRow:
    """One file of the asset. save_blocked and load_blocked are "" when the command can run, else the reason, which
    the window shows as the button's tool tip. saves and loads say whether the file type has the command at all."""

    key: str
    label: str
    owner_kind: str | None
    owner: str | None
    path: str
    exists: bool
    modified: float | None
    versions: int
    saves: bool
    loads: bool
    save_blocked: str = ""
    load_blocked: str = ""
    loads_by_name: bool = False   # Load by Name is offered (skin weights, RigModules D68); load_blocked applies to it
    opens_folder: bool = False    # a folder the artist fills (textures): Open Folder makes it and shows it, no Save or Load
    file_count: int | None = None   # for such a folder: the files in it (None when it is not there yet)
    open_blocked: str = ""
    imports_images: bool = False   # Import Textures... is on the row's menu (its blocked reason is save_blocked)
    note: str = ""   # said after the file count: how the folder's sidecar stands


@dataclasses.dataclass(frozen=True)
class RestoreChoice:
    """The answer to Restore: which local version to put back. The prompter shows it as a spin box."""

    version: int


class FileAction:
    """What one file type needs and does. A subclass sets key, label and owner_kind, and overrides the commands it has.
    Every method receives the model, for its asset, owners, the rig in the scene and the scene's selection."""

    key = ""
    label = ""
    owner_kind: str | None = None
    saves = False
    loads = False
    loads_by_name = False   # has load_by_name, offered on the row's right-click menu
    save_hint = ""   # what Save writes, shown in the button's tool tip
    confirms = True   # Save asks before it replaces a file that exists
    imports_images = False   # the row's menu has Import Textures...
    opens_folder = False   # a folder of files the artist adds by hand: the row's menu has Open Folder

    def open_blocked(self, model: AssetFilesModel) -> str:
        return ""

    def list_files(self, model: AssetFilesModel) -> list[str]:
        return []

    def note(self, model: AssetFilesModel) -> str:
        return ""

    def path(self, model: AssetFilesModel, owner: str | None) -> str:
        """The row's file: the asset's path for the file type. A folder type with a sidecar says the sidecar's."""
        return model.asset.path(self.key, owner)

    def save_blocked(self, model: AssetFilesModel) -> str:
        return ""

    def load_blocked(self, model: AssetFilesModel) -> str:
        return ""

    def save(self, model: AssetFilesModel) -> str:
        raise NotImplementedError

    def load(self, model: AssetFilesModel) -> None:
        raise NotImplementedError


class SkeletonAction(FileAction):
    key, label, owner_kind, saves, loads = "skeleton", "Skeleton", "skeleton", True, True
    save_hint = "Every joint in the scene, whatever is selected"

    def save_blocked(self, model):
        return "" if model.joints() else "There are no joints in the scene."

    def save(self, model):
        return bmaya.maya.assettools.save_skeleton(model.asset_id, model.owner(self), model.joints() or None)

    def load_blocked(self, model):
        return "" if model.file_exists(self) else "The skeleton is not saved yet."

    def load(self, model):
        joints = bmaya.maya.assettools.load_skeleton(model.asset_id, model.owner(self))
        cmds.select(joints, replace=True)


class ModelAction(FileAction):
    key, label, owner_kind, saves, loads = "model", "Model", "look", True, True
    save_hint = "Every mesh in the scene, whatever is selected"

    def save_blocked(self, model):
        if model.context.look is None:
            return "The asset has no look. Add one with New > Look."
        return "" if model.meshes() else "There are no meshes in the scene."

    def save(self, model):
        return bmaya.maya.assettools.save_model(model.asset_id, model.context.look, model.meshes() or None)

    def load_blocked(self, model):
        if model.context.look is None:
            return "The asset has no look."
        return "" if model.file_exists(self) else "The model is not saved yet."

    def load(self, model):
        bmaya.maya.assethandlers.register()
        bmaya.core.asset.handlers.load(model.asset, "model", model.context.look)


class WeightsAction(FileAction):
    key, label, owner_kind, saves, loads = "weights", "Skin weights", "look", True, True
    loads_by_name = True
    save_hint = "Every skinned mesh in the rig's namespace"

    def _blocked(self, model):
        if model.context.look is None:
            return "The asset has no look. Add one with New > Look."
        return model.rig_blocked()

    def save_blocked(self, model):
        return self._blocked(model)

    def save(self, model):
        files = bmaya.maya.assettools.save_skin_weights(model.rig_root, model.context.look)
        return model.asset.path(self.key, model.context.look) if files is not None else ""

    def load_blocked(self, model):
        return self._blocked(model) or ("" if model.file_exists(self) else "The weights are not saved yet.")

    def load(self, model):
        bmaya.maya.assettools.load_skin_weights(model.rig_root, model.context.look)

    def load_by_name(self, model):
        bmaya.maya.assettools.load_skin_weights(model.rig_root, model.context.look, by_name=True)


class TexturesAction(FileAction):
    """A look's textures: the folder of images the artist copies in (right-click: Open Folder, which makes it when it is
    missing) and its sidecar, textures.json, which says what each image is for and which mesh wears it. The row is
    the sidecar: Save records the rig's shading into it, and Load builds the shading from it."""

    key, label, owner_kind, saves, loads, opens_folder = "textures", "Textures", "look", True, True, True
    imports_images = True
    save_hint = "The shading of every marked mesh in the rig's namespace: its images and what they are for"

    def path(self, model, owner):
        return bmaya.core.asset.textures.get_path(model.asset.path(self.key, owner))

    def open_blocked(self, model):
        return "" if model.context.look is not None else "The asset has no look. Add one with New > Look."

    def list_files(self, model):
        return bmaya.maya.assethandlers.TexturesHandler.files(model.asset.path(self.key, model.context.look))

    def note(self, model):
        path = self.path(model, model.context.look) if model.context.look is not None else ""
        if not os.path.isfile(path):
            return "not mapped to meshes yet"
        try:
            return f"{len(bmaya.core.asset.textures.read(path).meshes)} meshes mapped"
        except bmaya.core.asset.textures.TexturesError:
            return "textures.json is not valid"

    def save_blocked(self, model):
        if model.context.look is None:
            return "The asset has no look. Add one with New > Look."
        return model.rig_blocked()

    def save(self, model):
        return bmaya.maya.assettools.save_textures(model.rig_root, model.context.look)

    def load_blocked(self, model):
        return self.save_blocked(model) or ("" if model.file_exists(self) else "The textures are not saved yet.")

    def load(self, model):
        bmaya.maya.assettools.load_textures(model.rig_root, model.context.look)


class RigSceneAction(FileAction):
    key, label, owner_kind, saves = "rig", "Rig scene", "rig", True
    save_hint = "Saves the open scene as the rig's file and renames it. Build Rig loads it again"

    def save_blocked(self, model):
        return model.rig_blocked()

    def save(self, model):
        return bmaya.maya.assettools.save_rig(model.rig_root)


class ShapesAction(FileAction):
    key, label, owner_kind, saves, loads = "shapes", "Control shapes", "rig", True, True
    save_hint = "The shape of every control of the rig"

    def save_blocked(self, model):
        return model.rig_blocked()

    def save(self, model):
        return bmaya.maya.assettools.save_control_shapes(model.rig_root)

    def load_blocked(self, model):
        return model.rig_blocked() or ("" if model.file_exists(self) else "The shapes are not saved yet.")

    def load(self, model):
        bmaya.maya.assettools.load_control_shapes(model.rig_root)


class TemplateAction(FileAction):
    """The rig's template, edited by hand in the OS's default application for .json files. Load keeps a local version
    of the file as it is (unless that is already the newest) and opens it there. Save, after the edit, checks that it
    is a template and writes it through the template handler, which keeps a local version and sets its rigName. So
    every state before a hand edit and every saved edit can be restored. A template is not in the scene, so Load
    changes nothing there and Save asks nothing."""

    key, label, owner_kind, saves, loads = "template", "Template", "rig", True, True
    confirms = False
    save_hint = "Checks the hand-edited template and keeps a local version of it"

    def _blocked(self, model):
        if model.context.rig is None:
            return "The asset has no rig. Add one with New > Rig."
        return "" if model.file_exists(self) else "The rig has no template file."

    def save_blocked(self, model):
        return self._blocked(model)

    def load_blocked(self, model):
        return self._blocked(model)

    def save(self, model):
        path = self.path(model, model.owner(self))
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except ValueError as error:   # JSONDecodeError and UnicodeDecodeError. Checked before a version is made
            raise ValueError(f"{path} is not valid JSON, so it was not saved: {error}") from error
        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a rig template: it is not a JSON object, so it was not saved.")
        bmaya.maya.assethandlers.register()
        return bmaya.core.asset.handlers.save(model.asset, "template", model.owner(self), source=path)

    def load(self, model):
        path = self.path(model, model.owner(self))
        bmaya.core.asset.versions.version_if_changed(path, model.asset.root)
        model.opener(path)


ACTIONS: tuple[FileAction, ...] = (SkeletonAction(), ModelAction(), WeightsAction(), TexturesAction(), RigSceneAction(),
                                   ShapesAction(), TemplateAction())


class AssetFilesModel:
    """The files of the context's asset. changed emits with no arguments when rows or message changed.

    refresh() reads the disk and the scene again: the editor calls it when the context changes, a scene opens or is
    new, and after every save and load. No Save uses the selection: a skeleton is every joint in the scene and a
    model every visible mesh."""

    def __init__(self, context: bmaya.core.asset.context.AssetContext) -> None:
        self.context = context
        self.changed = bmaya.core.observable.Event()
        self.rows: list[FileRow] = []
        self.message = ""
        self.rig_root: str | None = None
        self.breaking: dict[str, list[str]] = {}   # per rig of the asset: what the saved skeleton breaks of its last publish
        self.opener: Callable[[str], object] = getattr(os, "startfile", lambda path: None)   # Windows: Explorer
        self.refresh()

    # ---- what the actions read -------------------------------------------------------------

    @property
    def asset_id(self) -> str:
        return self.context.asset_id

    @property
    def asset(self) -> bmaya.core.asset.Asset:
        return self.context.asset

    def owner(self, action: FileAction) -> str | None:
        """The skeleton, rig or look the action's file belongs to. A skeleton with none saved yet is "default"."""
        kind = action.owner_kind
        if kind == "skeleton":
            return self.context.skeleton or DEFAULT_NAME
        return getattr(self.context, kind) if kind else None

    def file_exists(self, action: FileAction) -> bool:
        owner = self.owner(action)
        return (owner is not None or action.owner_kind is None) and os.path.exists(action.path(self, owner))

    def joints(self) -> list[str]:
        """Every joint in the scene. The selection is not used: a stray selection once saved a skeleton of one joint
        over the real one."""
        return cmds.ls(type="joint", long=True) or []

    def meshes(self) -> list[str]:
        """Every visible mesh in the scene. The selection is not used: a stray selection once saved a model of one
        mesh over the real one."""
        return bmaya.maya.assethandlers.get_scene_meshes()

    @property
    def look_status(self) -> bmaya.core.asset.lookstatus.LookStatus | None:
        """What the rig's last look did with each mesh (RigModules D70), None before one was applied in this session."""
        return bmaya.maya.assettools.get_look_status(self.rig_root) if self.rig_root else None

    def rig_blocked(self) -> str:
        """Why a command that needs the rig in the scene can't run, or ""."""
        if self.context.rig is None:
            return "The asset has no rig. Add one with New > Rig."
        if self.rig_root is None:
            return f"The rig {self.context.rig!r} of {self.asset_id} is not in the scene. Build Rig puts it there."
        return ""

    # ---- reading ---------------------------------------------------------------------------

    def refresh(self) -> None:
        """Reads the asset's files and the scene's rig again."""
        self.rig_root = self._find_rig_root()
        self.rows, self.message, self.breaking = [], "", {}
        if self.context.asset_id is None:
            self.message = "Pick an asset."
        elif not self._asset_exists():
            self.message = f"{self.asset_id} has no asset.json in the projects root. Create it with New > Asset."
        else:
            self.rows = [self._row(action) for action in ACTIONS]
            self.breaking = self._breaking_changes()
        self.changed.emit()

    def row(self, key: str) -> FileRow:
        for row in self.rows:
            if row.key == key:
                return row
        raise RuntimeError(f"There is no {key!r} file row.")

    def _breaking_changes(self) -> dict[str, list[str]]:
        """What the chosen skeleton, as saved, breaks of the last publish of each rig built on it (RigModules D70).
        Computed from the files on every refresh, never stored."""
        skeleton = self.context.skeleton
        if skeleton is None:
            return {}
        try:
            return bmaya.core.asset.publishing.skeleton_breaking_changes(self.asset, skeleton)
        except (bmaya.core.asset.AssetError, bmaya.core.asset.ProjectError, OSError) as error:
            bmaya.core.log.warning(f"The skeleton could not be checked against the last publish: {error}")
            return {}

    def publish_rig(self, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
        """Publishes the chosen rig. Returns the folder, or None when the user declined the breaking changes."""
        if self.context.rig is None:
            raise RuntimeError("The asset has no rig. Add one with New > Rig.")
        folder = bmaya.maya.assettools.publish_rig(self.asset_id, self.context.rig, prompter)
        self.refresh()
        return folder

    def publish_look(self) -> str:
        """Publishes the chosen look from the rig in the scene. Raises when a mesh blocks it."""
        blocked = self.rig_blocked()
        if blocked:
            raise RuntimeError(blocked)
        folder = bmaya.maya.assettools.publish_look(self.rig_root, self.context.look)
        self.refresh()
        return folder

    def _asset_exists(self) -> bool:
        try:
            return self.asset.exists()
        except bmaya.core.asset.ProjectError as error:
            self.message = str(error)
            return False

    def _find_rig_root(self) -> str | None:
        """The rig root in the scene that is this asset's chosen rig, else None. A rig of another asset is not it."""
        context = self.context
        if context.asset_id is None or context.rig is None:
            return None
        try:
            rigs = rigmodules.query.get_rigs()
        except RuntimeError as error:
            bmaya.core.log.error(f"The Asset Editor could not read the scene's rigs: {error}")
            return None
        return next((rig.rig_root for rig in rigs if rig.asset_id == context.asset_id and rig.rig_name == context.rig),
                    None)

    def _row(self, action: FileAction) -> FileRow:
        owner = self.owner(action)
        has_owner = owner is not None or action.owner_kind is None   # a look or rig the asset lacks has no file yet
        path = action.path(self, owner) if has_owner else ""
        exists = has_owner and os.path.exists(path)
        try:
            # A sidecar's versions can't be restored from the row (the file type is the folder), so none are offered.
            count = 0 if action.opens_folder else len(bmaya.core.asset.versions.list_versions(path, self.asset.root))
        except ValueError:
            count = 0
        return FileRow(
            key=action.key, label=action.label, owner_kind=action.owner_kind, owner=owner, path=path, exists=exists,
            modified=os.path.getmtime(path) if exists else None, versions=count, saves=action.saves, loads=action.loads,
            save_blocked=action.save_blocked(self) if action.saves else "",
            load_blocked=action.load_blocked(self) if action.loads else "", loads_by_name=action.loads_by_name,
            opens_folder=action.opens_folder, imports_images=action.imports_images, open_blocked=action.open_blocked(self) if action.opens_folder else "",
            file_count=len(action.list_files(self)) if action.opens_folder and os.path.isdir(os.path.dirname(path)) else None,
            note=action.note(self) if action.opens_folder and has_owner else "")

    # ---- commands --------------------------------------------------------------------------

    def save(self, key: str, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
        """Saves the file of the row. A file that exists is replaced only after the prompter confirms, and the old one
        stays as a local version copy. Returns the path, or None when the user declined."""
        action, row = self._action(key), self.row(key)
        if not action.saves:
            raise RuntimeError(f"{row.label} is not saved from here.")
        if row.save_blocked:
            raise RuntimeError(row.save_blocked)
        prompter = prompter or bmaya.core.prompts.current()
        if row.exists and action.confirms and not prompter.confirm(f"Save {row.label}", f"The {row.label.lower()} of {self.asset_id} "
                                               "exists. Replace it? The old file is kept as a local version.",
                                               accept="Replace"):
            return None
        path = action.save(self)
        self.context.refresh()   # a first skeleton or rig makes a new owner to choose
        self.refresh()
        return path

    def restore(self, key: str, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
        """Asks which local version copy of the row's file to restore (the newest, offered), and copies it over the
        file. The file it replaces is kept as a new version, so restoring that one undoes it. The scene is not
        touched: load the file to see it. Returns the path, or None when the user cancelled."""
        row = self.row(key)
        if not row.versions:
            raise RuntimeError(f"The {row.label.lower()} of {self.asset_id} has no local versions.")
        numbers = [number for number, _ in bmaya.core.asset.versions.list_versions(row.path, self.asset.root)]
        prompter = prompter or bmaya.core.prompts.current()
        answer = prompter.ask_form(f"Restore {row.label} (versions {numbers[0]} to {numbers[-1]})",
                                   RestoreChoice(version=numbers[-1]))
        if answer is None:
            return None
        path = bmaya.core.asset.handlers.restore(self.asset, key, row.owner, answer.version)
        bmaya.core.log.info(f"Restored version {answer.version} of the {row.label.lower()} of {self.asset_id}: {path}")
        self.context.refresh()   # a restored skeleton or rig can be a new owner to choose
        self.refresh()
        return path

    def load(self, key: str) -> None:
        """Loads the file of the row into the scene."""
        action, row = self._action(key), self.row(key)
        if not action.loads:
            raise RuntimeError(f"{row.label} is not loaded from here.")
        if row.load_blocked:
            raise RuntimeError(row.load_blocked)
        action.load(self)
        self.refresh()

    def import_textures(self, key: str, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
        """Asks which images to bring into the row's folder (bmaya.maya.assettools.import_textures_interactive), puts
        them in under the naming convention, and builds the rig's shading from them. Returns the folder, or None when
        the user cancelled."""
        action, row = self._action(key), self.row(key)
        if not action.imports_images:
            raise RuntimeError(f"{row.label} takes no textures.")
        if row.save_blocked:
            raise RuntimeError(row.save_blocked)
        report = bmaya.maya.assettools.ask_and_import_textures(self.rig_root, self.context.look, prompter)
        self.refresh()
        return os.path.dirname(row.path) if report is not None else None

    def open_folder(self, key: str) -> str:
        """Makes the row's folder when it is missing (a textures folder is made when the artist first needs it) and
        shows it in the file browser. Returns its path. self.opener is what shows it: os.startfile, and tests replace it."""
        action, row = self._action(key), self.row(key)
        if not action.opens_folder:
            raise RuntimeError(f"{row.label} has no folder to open.")
        if row.open_blocked:
            raise RuntimeError(row.open_blocked)
        folder = os.path.dirname(row.path)
        os.makedirs(folder, exist_ok=True)
        self.opener(folder)
        self.refresh()
        return folder

    def load_by_name(self, key: str) -> None:
        """Loads the row's file matched by mesh name (skin weights: RigModules D68), giving each mesh its file's
        meshId. Save the model afterwards so the next build matches by meshId."""
        action, row = self._action(key), self.row(key)
        if not action.loads_by_name:
            raise RuntimeError(f"{row.label} has no Load by Name.")
        if row.load_blocked:
            raise RuntimeError(row.load_blocked)
        action.load_by_name(self)
        self.refresh()

    def build_rig(self) -> str:
        """Builds the chosen rig, wearing the chosen look when it fits, and selects its rig root. Returns the root.

        A weight file that no longer fits does not fail the build: apply_look folds or binds rigid and logs it."""
        context = self.context
        if context.rig is None:
            raise RuntimeError("The asset has no rig. Add one with New > Rig.")
        looks = bmaya.maya.assettools.get_rig_looks(self.asset, context.rig)
        look = context.look if context.look in looks else (looks[0] if len(looks) == 1 else None)
        rig_root = bmaya.maya.assettools.build_rig(self.asset_id, context.rig, look)
        cmds.select(rig_root, replace=True)
        self.refresh()
        return rig_root

    def _action(self, key: str) -> FileAction:
        for action in ACTIONS:
            if action.key == key:
                return action
        raise RuntimeError(f"There is no {key!r} file type.")
