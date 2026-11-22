"""The Asset Editor's view-model: the asset context, the callbacks that keep its view current, and the commands its
buttons call (RigModules design/asset-editor.md, D61).

No Qt. A view connects to changed and reads asset_ids, context, files and the header strings. The session starts the
asset context when it is made and stops it in close(), and everything it registers goes away there: its Maya callbacks
and its listeners. Closing is the only thing that clears the asset: a new, opened or saved scene never does.

Maya callbacks it registers, all under keys that carry the session's id:
    new scene, open scene   read the scene-derived state again (the rigs, the file rows). The asset stays.
    rig built               read the scene-derived state again, like a new scene (the user event assettools.build_rig
                            posts, eventsregistry.RIG_BUILT_EVENT)
    files changed           the same, after any asset file is saved, restored or loaded, from the editor or not (the user
                            event bmaya.maya.assethandlers posts from the core handlers' changed event)
    maya exiting            close the session
    selection changed       only while a view is showing (watch_selection), for the markup and shape models
"""

from __future__ import annotations

import maya.cmds as cmds
import rigmodules.query

import bmaya.core.asset
import bmaya.core.asset.catalog
import bmaya.core.asset.context
import bmaya.core.log
import bmaya.core.observable
import bmaya.core.prompts
import bmaya.maya.activerig
import bmaya.maya.assetfiles
import bmaya.maya.assettools
import bmaya.maya.markupmodel
import bmaya.maya.namingmodel
import bmaya.maya.shapemodel
import bmaya.maya.eventsregistry

LAST_ASSET_OPTION = "bmayaAssetEditorLastAsset"
CALLBACK_PREFIX = "asset_editor"


def read_last_asset() -> str | None:
    """The asset the editor was last on, for prefilling the next one. Nothing else uses it."""
    if not cmds.optionVar(exists=LAST_ASSET_OPTION):
        return None
    return cmds.optionVar(query=LAST_ASSET_OPTION) or None


def write_last_asset(asset_id: str) -> None:
    cmds.optionVar(stringValue=(LAST_ASSET_OPTION, asset_id))


class AssetEditorSession:
    """State and commands of the Asset Editor.

    changed emits with no arguments when the view should read asset_ids, the context's values, the header strings
    or the files again. The context's own changed event is forwarded to it, so a view connects to one event. markup
    and shapes have their own changed events, and read the scene only while a view marks them active."""

    def __init__(self, asset_id: str | None = None) -> None:
        self.changed = bmaya.core.observable.Event()
        self.selection_changed = bmaya.core.observable.Event()   # emits while watch_selection is on
        self.asset_ids: list[str] = []
        self.closed = False
        self._watching = False
        self._keys = {
            "new": f"{CALLBACK_PREFIX}_{id(self)}_scene_new",
            "open": f"{CALLBACK_PREFIX}_{id(self)}_scene_open",
            "exit": f"{CALLBACK_PREFIX}_{id(self)}_maya_exit",
            "rig_built": f"{CALLBACK_PREFIX}_{id(self)}_rig_built",
            "files": f"{CALLBACK_PREFIX}_{id(self)}_files",
            "selection": f"{CALLBACK_PREFIX}_{id(self)}_selection",
        }

        bmaya.maya.activerig.ActiveRigTracker()   # the singleton: starts its callbacks when none runs
        self.context = bmaya.core.asset.context.AssetContext.start(asset_id or self._initial_asset())
        self.files = bmaya.maya.assetfiles.AssetFilesModel(self.context)
        self.markup = bmaya.maya.markupmodel.MarkupModel(self.selection_changed)
        self.shapes = bmaya.maya.shapemodel.ShapeModel(self.selection_changed)
        self.naming = bmaya.maya.namingmodel.NamingModel(self.selection_changed)
        self.context.changed.connect(self._on_context_changed)
        bmaya.maya.activerig.ActiveRigTracker.changed.connect(self._on_active_rig_changed)

        registry = bmaya.maya.eventsregistry.EventsRegistry()
        registry.add_maya_new_scene_callback(self._keys["new"], self._on_scene_changed)
        registry.add_maya_open_scene_callback(self._keys["open"], self._on_scene_changed)
        registry.add_maya_closing_callback(self._keys["exit"], self._on_maya_exiting)
        registry.add_user_event_callback(self._keys["rig_built"], bmaya.maya.eventsregistry.RIG_BUILT_EVENT,
                                         self._on_scene_changed)
        registry.add_user_event_callback(self._keys["files"], bmaya.maya.eventsregistry.ASSET_FILES_CHANGED_EVENT,
                                         self._on_scene_changed)
        self.refresh_asset_ids()

    # ---- life ------------------------------------------------------------------------------

    def close(self) -> None:
        """Removes every callback and listener, and clears the asset context. A view calls it when it closes or is
        destroyed. Safe to call twice."""
        if self.closed:
            return
        self.closed = True
        registry = bmaya.maya.eventsregistry.EventsRegistry()
        for key in self._keys.values():
            registry.unregister(key)
        bmaya.maya.activerig.ActiveRigTracker.changed.disconnect(self._on_active_rig_changed)
        self.context.changed.disconnect(self._on_context_changed)
        self.context.stop()

    def watch_selection(self, watch: bool) -> None:
        """Follows the selection while a view that reads it is showing, and stops when it isn't. Safe to call with the
        same value twice. The markup and shape models connect to selection_changed."""
        if self.closed:
            return
        registry = bmaya.maya.eventsregistry.EventsRegistry()
        key = self._keys["selection"]
        if watch and key not in registry.callbacks:
            registry.add_selection_changed_callback(key, self._on_selection_changed)
        elif not watch:
            registry.unregister(key)
        self._watching = watch

    # ---- reading ---------------------------------------------------------------------------

    def refresh_asset_ids(self) -> None:
        """Lists the assets below the projects root again. A missing projects root gives an empty list and a message
        in the log."""
        try:
            self.asset_ids = bmaya.core.asset.catalog.asset_ids()
        except bmaya.core.asset.ProjectError as error:
            bmaya.core.log.warning(str(error))
            self.asset_ids = []
        self.changed.emit()

    def refresh(self) -> None:
        """Reads the asset list, the owners and the files again."""
        self.context.refresh()
        self.refresh_asset_ids()
        self.files.refresh()

    def active_rig(self) -> rigmodules.query.RigInfo | None:
        """The active rig, which the editor shows and may switch to but never follows, or None."""
        try:
            return bmaya.maya.activerig.get_active_rig()
        except RuntimeError:
            return None

    def rig_mismatch(self) -> str:
        """Text for the header when the active rig belongs to another asset than the editor's, else "". The editor
        keeps its asset: the user switches with use_active_rig."""
        rig = self.active_rig()
        if rig is None or rig.asset_id == self.context.asset_id:
            return ""
        return f"The active rig {rig.rig_name!r} belongs to {rig.asset_id}, and the editor is on {self.context.asset_id or 'no asset'}."

    # ---- commands --------------------------------------------------------------------------

    def set_asset(self, asset_id: str | None) -> None:
        """Works on another asset. Raises AssetIdError for an invalid id."""
        self.context.set_asset(asset_id)
        if asset_id:
            write_last_asset(asset_id)

    def use_active_rig(self) -> None:
        """Works on the asset of the active rig, and on the rig's own name."""
        rig = bmaya.maya.activerig.get_active_rig()   # raises RuntimeError when the scene has no rig
        self.set_asset(rig.asset_id)
        if rig.rig_name in self.context.rigs():
            self.context.set_rig(rig.rig_name)

    def create_project(self, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
        """Asks for a folder and makes it a project. Returns the folder, or None when cancelled."""
        folder = bmaya.maya.assettools.new_project_interactive(prompter)
        if folder:
            self.refresh()
        return folder

    def create_asset(self, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
        """Asks for a new asset and works on it. Returns its id, or None when cancelled."""
        asset_id = bmaya.maya.assettools.new_asset_interactive(prompter)
        if asset_id:
            self.set_asset(asset_id)
            self.refresh()
        return asset_id

    def create_rig(self, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
        """Adds a rig to the asset being worked on, and picks it. Returns its name, or None when cancelled."""
        asset_id = self._require_asset_id()
        rig = bmaya.maya.assettools.new_rig_interactive(prompter, asset_id=asset_id)
        if rig:
            self.refresh()
            self.context.set_rig(rig)
        return rig

    def create_look(self, prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
        """Adds a look to the asset being worked on, and picks it. Returns its name, or None when cancelled."""
        asset_id = self._require_asset_id()
        look = bmaya.maya.assettools.new_look_interactive(prompter, asset_id=asset_id)
        if look:
            self.refresh()
            self.context.set_look(look)
        return look

    def _require_asset_id(self) -> str:
        if self.context.asset_id is None:
            raise RuntimeError("Pick an asset first.")
        return self.context.asset_id

    def _initial_asset(self) -> str | None:
        """The active rig's asset, else the one the editor was last on."""
        rig = self.active_rig()
        return rig.asset_id if rig is not None else read_last_asset()

    # ---- events ----------------------------------------------------------------------------

    def _on_context_changed(self) -> None:
        self.files.refresh()
        self.changed.emit()

    def _on_active_rig_changed(self, rig_root: str | None) -> None:
        self.changed.emit()   # only the header's mismatch strip reads it

    def _on_scene_changed(self, *args) -> None:
        self.files.refresh()
        self.changed.emit()

    def _on_selection_changed(self, *args) -> None:
        self.selection_changed.emit()

    def _on_maya_exiting(self, *args) -> None:
        self.close()
