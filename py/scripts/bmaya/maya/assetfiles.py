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
import os

import maya.cmds as cmds
import rigmodules.query

import bmaya.core.asset
import bmaya.core.asset.context
import bmaya.core.asset.handlers
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


class FileAction:
    """What one file type needs and does. A subclass sets key, label and owner_kind, and overrides the commands it has.
    Every method receives the model, for its asset, owners, the rig in the scene and the scene's selection."""

    key = ""
    label = ""
    owner_kind: str | None = None
    saves = False
    loads = False
    save_hint = ""   # what Save writes, shown in the button's tool tip

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
    """The rig's template: shown for its status. It is written by the template tool, so there is no Save here."""

    key, label, owner_kind = "template", "Template", "rig"


ACTIONS: tuple[FileAction, ...] = (SkeletonAction(), ModelAction(), WeightsAction(), RigSceneAction(), ShapesAction(),
                                   TemplateAction())


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
        return (owner is not None or action.owner_kind is None) and self.asset.file_exists(action.key, owner)

    def joints(self) -> list[str]:
        """Every joint in the scene. The selection is not used: a stray selection once saved a skeleton of one joint
        over the real one."""
        return cmds.ls(type="joint", long=True) or []

    def meshes(self) -> list[str]:
        """Every visible mesh in the scene. The selection is not used: a stray selection once saved a model of one
        mesh over the real one."""
        return bmaya.maya.assethandlers.get_scene_meshes()

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
        self.rows, self.message = [], ""
        if self.context.asset_id is None:
            self.message = "Pick an asset."
        elif not self._asset_exists():
            self.message = f"{self.asset_id} has no asset.json in the projects root. Create it with New > Asset."
        else:
            self.rows = [self._row(action) for action in ACTIONS]
        self.changed.emit()

    def row(self, key: str) -> FileRow:
        for row in self.rows:
            if row.key == key:
                return row
        raise RuntimeError(f"There is no {key!r} file row.")

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
        path = self.asset.path(action.key, owner) if has_owner else ""
        exists = has_owner and os.path.exists(path)
        try:
            count = len(bmaya.core.asset.versions.list_versions(path, self.asset.root))
        except ValueError:
            count = 0
        return FileRow(
            key=action.key, label=action.label, owner_kind=action.owner_kind, owner=owner, path=path, exists=exists,
            modified=os.path.getmtime(path) if exists else None, versions=count, saves=action.saves, loads=action.loads,
            save_blocked=action.save_blocked(self) if action.saves else "",
            load_blocked=action.load_blocked(self) if action.loads else "")

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
        if row.exists and not prompter.confirm(f"Save {row.label}", f"The {row.label.lower()} of {self.asset_id} "
                                               "exists. Replace it? The old file is kept as a local version.",
                                               accept="Replace"):
            return None
        path = action.save(self)
        self.context.refresh()   # a first skeleton or rig makes a new owner to choose
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

    def build_rig(self) -> str:
        """Builds the chosen rig, wearing the chosen look when it fits, and selects its rig root. Returns the root."""
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
