"""The library browser's view-model: the active rig's pose and animation library, its search, the scope an apply or
a save acts on, and the commands behind the buttons (RigModules design/library-browser.md, D51).

No Qt. A view connects to changed and reads the attributes. The listing follows the active rig through
ActiveRigTracker.changed, and the files come from bmaya.core.asset.library, whose index reads each file once through
RigModules' getRigDataFileInfo. Every command is a call into posetools, assettools or the library, so mayapy and tests
run the same code the buttons do. A command raises on a problem and the view shows the message. What never raises is
the listing: a rig with no asset on disk, or a broken library file, is an empty state with a reason or an entry with an
error.

    session = bmaya.maya.librarybrowser.LibrarySession()
    session.set_query("tag:fist")
    session.select(session.entries[0])
    session.apply(mirror=True)
"""

from __future__ import annotations

import dataclasses
import os

import maya.cmds as cmds
import maya.mel
import rigmodules.library
import rigmodules.query

import bmaya.core.asset
import bmaya.core.asset.library
import bmaya.core.asset.versions
import bmaya.core.log
import bmaya.core.observable
import bmaya.maya.activerig
import bmaya.maya.assettools
import bmaya.maya.posetools

LIBRARY = bmaya.core.asset.library
SCOPE_SELECTION = "selection"
SCOPE_RIG = "rig"
FACET_FIELDS = ("tag", "template", "region", "status", "category")   # search terms a facet can set


def read_file_infos(paths: list[str], rig_root: str) -> list[LIBRARY.FileInfo]:
    """The Index's reader: what each file holds, and how well it fits rig_root, in one RigModules command call."""
    names = [field.name for field in dataclasses.fields(LIBRARY.FileInfo)]
    return [LIBRARY.FileInfo(**{name: getattr(info, name) for name in names})
            for info in rigmodules.library.get_data_file_info(rig_root, paths)]


def rig_masks(controls: list[rigmodules.query.RigControl]) -> list[LIBRARY.Mask]:
    """The masks a rig gives with no authoring: one per module type present, one per side, and one per module, which
    holds the module's controls by (side, usage), unique in a rig (D25)."""
    masks: dict[str, LIBRARY.Mask] = {}

    def add(name: str, items: list[LIBRARY.MaskItem]) -> None:
        masks.setdefault(name.casefold(), LIBRARY.Mask(name, tuple(items), LIBRARY.RIG))

    for module_type in dict.fromkeys(control.module_type for control in controls):
        add(module_type, [LIBRARY.MaskItem(module_type=module_type)])
    for side in dict.fromkeys(control.side for control in controls):
        add(side, [LIBRARY.MaskItem(side=side)])
    for module in dict.fromkeys(control.module for control in controls):
        add(_short_name(module), [LIBRARY.MaskItem(side=control.side, usage=control.usage)
                                  for control in controls if control.module == module])
    return list(masks.values())


class LibrarySession:
    """State and commands of the library browser.

    changed emits with no arguments when the view should read the attributes again: the active rig changed, the files
    or the query did, the selection moved. The session follows ActiveRigTracker.changed and never changes the active rig.

    kind          POSE or ANIMATION: which of the two libraries is listed.
    query         the search box. entries is the files of the enabled sources that match it, sorted by name.
    scope         None (the selected controls, else the whole rig), SCOPE_SELECTION, SCOPE_RIG or a mask's name.
    reason        why there is nothing to list, "" when there is.
    """

    def __init__(self, index: LIBRARY.Index | None = None) -> None:
        self.changed = bmaya.core.observable.Event()
        self._index = index or LIBRARY.Index(read_file_infos)
        self.kind = LIBRARY.POSE
        self.query = ""
        self.scope: str | None = None
        self.reason = ""
        self.asset_id: str | None = None
        self.rig_name: str | None = None      # the library is the rig's: poses are keyed by a rig's control markup
        self.rig_root: str | None = None
        self.sources: list[LIBRARY.LibrarySource] = []
        self.source_enabled: dict[str, bool] = {}
        self.entries: list[LIBRARY.LibraryEntry] = []
        self.selected: LIBRARY.LibraryEntry | None = None
        self.masks: list[LIBRARY.Mask] = []
        self._asset: bmaya.core.asset.Asset | None = None
        self._all: list[LIBRARY.LibraryEntry] = []
        bmaya.maya.activerig.ActiveRigTracker()   # the singleton: starts the callbacks when none runs
        bmaya.maya.activerig.ActiveRigTracker.changed.connect(self._on_active_rig_changed)
        self._load()

    def close(self) -> None:
        """Stops following the tracker. A view calls it when its window is destroyed."""
        bmaya.maya.activerig.ActiveRigTracker.changed.disconnect(self._on_active_rig_changed)

    # ---- reading --------------------------------------------------------------------------------------

    def refresh(self) -> None:
        """Reads the rig and the library again. Only files that are new or changed are read."""
        self._load()
        self.changed.emit()

    def _load(self) -> None:
        previous = self.selected.path if self.selected else None
        self._empty("There is no active rig.")
        tracker = bmaya.maya.activerig.ActiveRigTracker.current()
        rig_root = tracker.rig_root if tracker is not None else None
        if rig_root is None or not cmds.objExists(rig_root):
            return
        try:
            info = rigmodules.query.find_rig_info(rig_root)
            if info is None:
                return
            self.rig_root, self.asset_id, self.rig_name = rig_root, info.asset_id, info.rig_name
            self._asset = bmaya.core.asset.Asset(info.asset_id)
            self.sources = LIBRARY.sources(self._asset, info.rig_name)
            self.source_enabled = {source.key: self.source_enabled.get(source.key, True) for source in self.sources}
            files = [item for source in self.sources for item in LIBRARY.list_files(source, self.kind)]
            self._all = self._index.entries(files, rig_root)
            self.masks = self._read_masks(rig_root)
            self.reason = ""
        except (RuntimeError, ValueError) as error:   # a rig with no projects root, a broken file, a bad asset id
            self._empty(str(error))
            bmaya.core.log.warning(f"The library could not be read: {error}")
            return
        self._filter()
        self.selected = next((entry for entry in self.entries if entry.path == previous), None)

    def _empty(self, reason: str) -> None:
        self.reason = reason
        self.asset_id = self.rig_name = self.rig_root = self._asset = None
        self.sources, self._all, self.entries, self.masks, self.selected = [], [], [], [], None

    def _read_masks(self, rig_root: str) -> list[LIBRARY.Mask]:
        masks = rig_masks(rigmodules.query.get_rig_controls(rig_root))
        try:
            saved = LIBRARY.saved_masks(self._asset, self.rig_name)
        except LIBRARY.LibraryError as error:
            bmaya.core.log.warning(f"The saved masks could not be read: {error}")
            saved = []
        taken = {mask.name.casefold() for mask in masks}
        return masks + [mask for mask in saved if mask.name.casefold() not in taken]

    def _filter(self) -> None:
        enabled = [entry for entry in self._all if self.source_enabled.get(entry.source, True)]
        self.entries = LIBRARY.filter_entries(enabled, LIBRARY.parse_query(self.query))

    # ---- what the view sets -----------------------------------------------------------------------------

    def set_kind(self, kind: str) -> None:
        if kind not in LIBRARY.KINDS:
            raise ValueError(f"kind is {' or '.join(LIBRARY.KINDS)}, not {kind!r}.")
        if kind != self.kind:
            self.kind = kind
            self.refresh()

    def set_query(self, text: str) -> None:
        self.query = text
        self._after_filter()

    def set_source_enabled(self, key: str, enabled: bool) -> None:
        self.source_enabled[key] = enabled
        self._after_filter()

    def set_scope(self, scope: str | None) -> None:
        """None, SCOPE_SELECTION, SCOPE_RIG or the name of one of masks. Raises ValueError for any other name."""
        if scope not in (None, SCOPE_SELECTION, SCOPE_RIG) and all(mask.name != scope for mask in self.masks):
            raise ValueError(f"{scope!r} is not a scope. Use None, {SCOPE_SELECTION!r}, {SCOPE_RIG!r} or a mask: "
                             f"{', '.join(mask.name for mask in self.masks) or 'none'}.")
        self.scope = scope
        self.changed.emit()

    def select(self, entry: LIBRARY.LibraryEntry | None) -> None:
        self.selected = entry
        self.changed.emit()

    def _after_filter(self) -> None:
        self._filter()
        if self.selected and all(entry.path != self.selected.path for entry in self.entries):
            self.selected = None
        self.changed.emit()

    # ---- the scope ----------------------------------------------------------------------------------------

    def scope_controls(self) -> list[str]:
        """What an apply or a save acts on, for the scope: the rig root for the whole rig, else controls. A mask
        keeps only the selected controls when some of the rig's are selected. Raises RuntimeError when it is empty."""
        rig_root = self._require_rig()
        selected = self._selected_controls(rig_root)
        scope = self.scope or (SCOPE_SELECTION if selected else SCOPE_RIG)
        if scope == SCOPE_RIG:
            return [rig_root]
        if scope == SCOPE_SELECTION:
            if not selected:
                raise RuntimeError("Select controls of the active rig, or choose another scope.")
            return selected
        mask = next(mask for mask in self.masks if mask.name == scope)
        controls = [control.node for control in rigmodules.query.get_rig_controls(rig_root)
                    if mask.matches(control.module_type, control.side, control.usage)]
        if selected:
            wanted = set(cmds.ls(selected, long=True))
            controls = [control for control in controls if cmds.ls(control, long=True)[0] in wanted]
        if not controls:
            raise RuntimeError(f"The mask {mask.name!r} has no controls{' in the selection' if selected else ''}.")
        return controls

    @staticmethod
    def _selected_controls(rig_root: str) -> list[str]:
        """The selected controls that belong to the rig."""
        selected = cmds.ls(selection=True, long=True, type=rigmodules.query.RIG_CONTROL_TYPE)
        if not selected:
            return []
        belongs = set(cmds.ls([control.node for control in rigmodules.query.get_rig_controls(rig_root)], long=True))
        return [control for control in selected if control in belongs]

    def _require_rig(self) -> str:
        if self.rig_root is None:
            raise RuntimeError(self.reason or "There is no active rig.")
        return self.rig_root

    # ---- what a selected entry says ---------------------------------------------------------------------

    def details(self, entry: LIBRARY.LibraryEntry) -> list[str]:
        """The line under the list for an entry, then a line for each warning: a file that can't be read, controls the
        rig lacks, and a frame rate the scene doesn't have (the load command would refuse it)."""
        info = entry.info
        if info.error:
            return [info.error]
        lines = [f"{info.control_count} controls, {info.channel_count} channels, {len(info.unmatched_controls)} unmatched."]
        if info.unmatched_controls:
            lines.append("The rig has no control for " + ", ".join(f"{side} {usage}" for side, usage in info.unmatched_controls) + ".")
        if entry.kind == LIBRARY.ANIMATION and info.frame_rate and abs(info.frame_rate - _scene_frame_rate()) > 1e-3:
            lines.append(f"The animation is {info.frame_rate:g} fps and the scene is {_scene_frame_rate():g} fps: it can't be loaded.")
        regions, statuses = self._vocabulary()
        for label, values, allowed in (("rig region", entry.regions, regions),
                                       ("status", [entry.meta("status")] if entry.meta("status") else [], statuses)):
            unknown = [value for value in values if allowed and value not in allowed]
            if unknown:
                lines.append(f"The {label} {', '.join(repr(value) for value in unknown)} is not one this project lists "
                             f"({', '.join(allowed)}).")
        return lines

    def _vocabulary(self) -> tuple[list[str], list[str]]:
        """The rig regions and the statuses the project declares in project.json. Both are empty for a project that
        declares none, or an asset with no project on disk, and then nothing is checked."""
        if self._asset is None:
            return [], []
        try:
            project = self._asset.project
            return list(project.rig_regions), list(project.library_statuses)
        except (RuntimeError, ValueError, OSError):
            return [], []

    def facets(self) -> dict[str, list[str]]:
        """The values in use for each facet of the search (a search term's field), across the enabled sources and
        before the search filters them: tag, template, region, status and category, each sorted. The view's Filter menu
        and the tag completer read it."""
        enabled = [entry for entry in self._all if self.source_enabled.get(entry.source, True)]
        found: dict[str, set[str]] = {field: set() for field in FACET_FIELDS}
        for entry in enabled:
            found["tag"].update(entry.tags)
            found["region"].update(entry.regions)
            for field, key in (("template", "template"), ("status", "status"), ("category", "category")):
                if entry.meta(key):
                    found[field].add(entry.meta(key))
        return {field: sorted(values, key=str.casefold) for field, values in found.items()}

    def _user_source(self) -> LIBRARY.LibrarySource:
        """The signed-in user's own library of the active rig, where saves go."""
        return LIBRARY.user_source(self._asset, self.rig_name)

    def name_taken(self, name: str) -> bool:
        """Whether the user's own library already has a file of this kind called name. Raises LibraryError for a name
        the rule refuses and RuntimeError with no rig."""
        self._require_rig()
        return LIBRARY.find_file(self._user_source().folders[self.kind], self.kind, LIBRARY.check_name(name)) is not None

    @staticmethod
    def current_frame() -> float:
        """The scene's current frame: what the Start at field takes."""
        return float(cmds.currentTime(query=True))

    @staticmethod
    def playback_range() -> tuple[int, int]:
        """The playback range, which an animation is saved over unless the caller says otherwise."""
        return int(cmds.playbackOptions(query=True, minTime=True)), int(cmds.playbackOptions(query=True, maxTime=True))

    # ---- looks (RigModules D54 phase 5) ------------------------------------------------------------------
    # Not a third kind of file in the list: a look is a model and its weights, not a library file with a meta block,
    # so the view-model offers the active rig's looks and applying one. The window has no tab for them yet.

    def look_entries(self) -> list[bmaya.core.asset.AssetLook]:
        """The looks of the active rig's asset that its skeleton can wear, sorted, with whether each is local. A look
        that is not synced is listed by name: its fit is checked when it is chosen and synced. Raises RuntimeError with
        no active rig."""
        self._require_rig()
        return bmaya.maya.assettools.list_rig_looks(self._asset, self.rig_name)

    def looks(self) -> list[str]:
        """The names in look_entries(). Raises RuntimeError with no active rig."""
        return [entry.name for entry in self.look_entries()]

    def worn_look(self) -> str | None:
        """The look the active rig wears, from its lookRoot, or None. Raises RuntimeError with no active rig."""
        info = rigmodules.query.get_rig_info(self._require_rig())
        return info.look.name if info.look is not None and info.look.asset_id == info.asset_id else None

    def apply_look(self, name: str) -> str:
        """Puts the active rig in the look, in one undo step (assettools.apply_look): the previous look's meshes go,
        the controls and animation stay. Raises RuntimeError for no rig or a look the rig can't wear, and what
        apply_look raises, including a failed sync of a look that is not local. Returns the lookRoot."""
        rig_root = self._require_rig()
        if name not in self.looks():
            raise RuntimeError(f"{self.asset_id} has no look {name!r} that the rig {self.rig_name!r} can wear: "
                               f"{', '.join(self.looks()) or 'none'}.")
        look_root = bmaya.maya.assettools.apply_look(rig_root, name)
        self.refresh()
        return look_root

    # ---- commands -----------------------------------------------------------------------------------------

    def apply(self, mirror: bool = False, start_frame: float | None = None) -> list[str]:
        """Loads the selected entry onto the scope, in one undo step. An animation's keys land on the frames they were
        saved on, or start at start_frame. mirror puts the Left side on the Right and the Right on the Left. Returns the
        controls it changed."""
        entry = self.selected
        if entry is None:
            raise RuntimeError("Select a pose or an animation first.")
        if entry.info.error:
            raise RuntimeError(entry.info.error)
        scope = self.scope_controls()
        if entry.kind == LIBRARY.POSE:
            return bmaya.maya.posetools.load_pose(scope, entry.path, mirror)
        offset = 0 if start_frame is None else start_frame - entry.info.start_frame
        return bmaya.maya.posetools.load_animation(scope, entry.path, offset, mirror)

    def suggest_name(self) -> str:
        """A free name for the next save: pose_001, animation_001, ..."""
        self._require_rig()
        return LIBRARY.free_name(self._user_source(), self.kind)

    def save(self, name: str, tags: tuple[str, ...] = (), description: str = "", replace: bool = False,
             start_frame: int | None = None, end_frame: int | None = None) -> LIBRARY.LibraryEntry | None:
        """Saves the scope to the user's own library under name, and selects the new entry (None when the search hides it). A pose is the scope's
        channels at their values, an animation its keys over the playback range (or start_frame to end_frame). An
        existing name is refused unless replace is set. Raises RuntimeError and LibraryError."""
        self._require_rig()
        user = self._user_source()
        if LIBRARY.find_file(user.folders[self.kind], self.kind, LIBRARY.check_name(name)) and not replace:
            raise LIBRARY.LibraryError(f"You already have a {self.kind} called {name!r}.")
        scope = self.scope_controls()
        if self.kind == LIBRARY.POSE:
            path = bmaya.maya.assettools.save_pose(self.asset_id, name, scope, tags, description)
        else:
            range_start, range_end = self.playback_range()
            start = range_start if start_frame is None else start_frame
            end = range_end if end_frame is None else end_frame
            path = bmaya.maya.assettools.save_animation(self.asset_id, name, scope, start, end, tags, description)
        self._index.forget(path)
        self.refresh()
        return self._select_path(path)

    def set_meta(self, entry: LIBRARY.LibraryEntry, tags: list[str] | None = None, description: str | None = None) -> None:
        """Edits the tags or the description of an entry in the user's own library, keeping a local version of the old
        file. Raises LibraryError for an entry in another source."""
        self._require_writable(entry)
        meta: dict[str, object] = {}
        if tags is not None:
            meta["tags"] = list(tags)
        if description is not None:
            meta["description"] = description
        bmaya.core.asset.versions.version(entry.path, self._asset.root)
        rigmodules.library.set_data_file_meta(entry.path, meta)
        self._index.forget(entry.path)
        self.refresh()
        self._select_path(entry.path)

    def rename(self, entry: LIBRARY.LibraryEntry, name: str) -> LIBRARY.LibraryEntry:
        """Renames an entry in the user's own library. A file written before the suffixes gets its suffix. Raises
        LibraryError for a taken name or an entry in another source."""
        renamed = LIBRARY.rename_file(entry.file, name)
        self._index.forget(entry.path)
        self.refresh()
        return self._select_path(renamed.path)

    def delete(self, entry: LIBRARY.LibraryEntry) -> None:
        """Deletes an entry in the user's own library. A local version copy stays. Raises LibraryError for an entry in
        another source."""
        self._require_rig()
        LIBRARY.delete_file(entry.file, self._asset.root)
        self._index.forget(entry.path)
        self.refresh()

    def copy_to_user(self, entry: LIBRARY.LibraryEntry) -> LIBRARY.LibraryEntry:
        """Copies an entry of Approved or Shared into the user's own library. Raises LibraryError when the name is taken."""
        self._require_rig()
        path = LIBRARY.copy_to_user(entry.file, self._user_source())
        self.refresh()
        return self._select_path(path)

    def save_mask(self, mask: LIBRARY.Mask) -> None:
        """Saves a mask of the user's own, replacing one of the same name. A name a rig mask has is refused."""
        self._require_rig()
        if any(existing.source == LIBRARY.RIG and existing.name.casefold() == mask.name.casefold() for existing in self.masks):
            raise LIBRARY.LibraryError(f"{mask.name!r} is the name of a mask the rig gives. Choose another.")
        LIBRARY.save_mask(self._asset, self.rig_name, mask)
        self.refresh()

    def mask_from_selection(self, name: str) -> LIBRARY.Mask:
        """A mask named name for the selected controls of the rig: one item per (side, usage), which is unique in a rig
        (D25), so it picks the same controls on any rig of the template. Save it with save_mask. Raises RuntimeError
        when no control of the rig is selected, and LibraryError for an empty name."""
        rig_root = self._require_rig()
        if not name.strip():
            raise LIBRARY.LibraryError("A mask needs a name.")
        selected = set(self._selected_controls(rig_root))
        if not selected:
            raise RuntimeError("Select controls of the active rig to make a mask of them.")
        controls = [control for control in rigmodules.query.get_rig_controls(rig_root)
                    if cmds.ls(control.node, long=True)[0] in selected]
        items = dict.fromkeys(LIBRARY.MaskItem(side=control.side, usage=control.usage) for control in controls)
        return LIBRARY.Mask(name.strip(), tuple(items), LIBRARY.USER)

    def delete_mask(self, name: str) -> None:
        self._require_rig()
        LIBRARY.delete_mask(self._asset, self.rig_name, name)
        if self.scope == name:
            self.scope = None
        self.refresh()

    # ---- helpers ------------------------------------------------------------------------------------------

    def _require_writable(self, entry: LIBRARY.LibraryEntry) -> None:
        self._require_rig()
        if not entry.file.writable:
            raise LIBRARY.LibraryError(
                f"{entry.name!r} is in the {entry.source} library, which can't be changed here. Copy it to your own first.")

    def _select_path(self, path: str) -> LIBRARY.LibraryEntry | None:
        """Selects the entry at path, when the filter shows it. Returns it, or None."""
        entry = next((entry for entry in self.entries if os.path.normcase(entry.path) == os.path.normcase(path)), None)
        self.select(entry)
        return entry

    def _on_active_rig_changed(self, rig_root: str | None) -> None:
        self.refresh()


def _short_name(node: str) -> str:
    return node.split("|")[-1].split(":")[-1]


def _scene_frame_rate() -> float:
    return float(maya.mel.eval("currentTimeUnitToFPS"))
