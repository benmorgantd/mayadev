"""The active rig: the RigModules rig that the menu tools act on, so nobody has to select a rig root.

Selecting any node of a rig (a control, a joint the rig drives, a module or the rig root) makes that rig
active, and it stays active while other things are selected. A new or opened scene makes its first rig
active. ActiveRigTracker follows both through EventsRegistry callbacks, and startup creates it once the
RigModules plugin loads. Nodes are matched to rigs by rigmodules.query, which walks the rig's connections
(RigModules D24, D30).

Without a tracker (batch jobs, tests), get_active_rig works from the selection, then the scene.
"""

from __future__ import annotations

from typing import ClassVar

import maya.cmds as cmds
import rigmodules.query

import bmaya.core.log
import bmaya.core.observable
import bmaya.maya.eventsregistry

SELECTION_CALLBACK = "active_rig_selection_changed"
SCENE_NEW_CALLBACK = "active_rig_scene_new"
SCENE_OPEN_CALLBACK = "active_rig_scene_open"

# A selection callback runs on every selection change, so it checks only the most recently selected nodes.
# The last selected node normally decides it. The rest cover a rig node picked before a few other nodes.
MAX_SELECTED_NODES_CHECKED = 32


def rig_from_selection() -> rigmodules.query.RigInfo | None:
    """The rig of the most recently selected node that belongs to one, or None."""
    selection = cmds.ls(selection=True, objectsOnly=True) or []
    for node in reversed(selection[-MAX_SELECTED_NODES_CHECKED:]):
        try:
            info = rigmodules.query.find_rig_info(node)
        except RuntimeError:
            continue   # a broken rig: getRigInfo has already reported it
        if info is not None:
            return info
    return None


def first_rig_in_scene() -> rigmodules.query.RigInfo | None:
    rigs = rigmodules.query.get_rigs()
    return rigs[0] if rigs else None


def get_active_rig() -> rigmodules.query.RigInfo:
    """The tracker's rig while it still exists, else the selection's rig, else the scene's first rig. Raises
    RuntimeError when the scene has no rig."""
    tracker = ActiveRigTracker.current()
    if tracker is not None and tracker.rig_root and cmds.objExists(tracker.rig_root):
        info = rigmodules.query.find_rig_info(tracker.rig_root)
        if info is not None:
            return info
    info = rig_from_selection() or first_rig_in_scene()
    if info is None:
        raise RuntimeError("There is no RigModules rig in the scene.")
    if tracker is not None:
        tracker.set_rig_root(info.rig_root)
    return info


class ActiveRigTracker:
    """Singleton that follows the active rig through selection, file new and file open callbacks.

    changed emits the rig root (or None) whenever the active rig changes, and again on refresh() when the scene's
    rigs may have changed under the same active rig. It belongs to the class, not the instance, so a view that
    connected to it keeps listening across stop() and a new tracker (the dev reload restarts the tracker; RigModules
    design/active-rig-panel.md, D50).
    """

    changed: ClassVar[bmaya.core.observable.Event] = bmaya.core.observable.Event()
    _instance: ActiveRigTracker | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.rig_root: str | None = None
        registry = bmaya.maya.eventsregistry.EventsRegistry()
        registry.add_selection_changed_callback(SELECTION_CALLBACK, self._on_selection_changed)
        registry.add_maya_new_scene_callback(SCENE_NEW_CALLBACK, self._on_scene_changed)
        registry.add_maya_open_scene_callback(SCENE_OPEN_CALLBACK, self._on_scene_changed)
        self._initialized = True
        self.refresh()

    @classmethod
    def current(cls) -> ActiveRigTracker | None:
        """The running tracker, or None when none was started."""
        return cls._instance

    def stop(self) -> None:
        """Removes the callbacks. The next ActiveRigTracker() starts a new tracker."""
        registry = bmaya.maya.eventsregistry.EventsRegistry()
        for key in (SELECTION_CALLBACK, SCENE_NEW_CALLBACK, SCENE_OPEN_CALLBACK):
            registry.unregister(key)
        ActiveRigTracker._instance = None

    def set_rig_root(self, rig_root: str | None) -> None:
        if rig_root != self.rig_root:
            self.rig_root = rig_root
            bmaya.core.log.info(f"Active rig: {rig_root or 'none'}")
            self.changed.emit(rig_root)

    def refresh(self) -> None:
        """Makes the selection's rig active, else the scene's first rig, else none. Emits changed even when the
        active rig stays the same, because the scene's rigs may not: a build or a deleted rig calls this."""
        previous = self.rig_root
        info = rig_from_selection() or first_rig_in_scene()
        self.set_rig_root(info.rig_root if info else None)
        if self.rig_root == previous:
            self.changed.emit(self.rig_root)

    def _on_selection_changed(self, *args) -> None:
        info = rig_from_selection()
        if info is not None:
            self.set_rig_root(info.rig_root)

    def _on_scene_changed(self, *args) -> None:
        self.refresh()
