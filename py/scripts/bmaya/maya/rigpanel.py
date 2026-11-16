"""The active rig panel's view-model: the rigs in the scene, the active rig's controls grouped by module and side,
and the commands the panel's buttons call (RigModules design/active-rig-panel.md, D50).

No Qt. A view connects to changed and reads rigs, rig and groups, and to spaces_changed and reads space. Every
command is a call into posetools or a RigModules command, so mayapy and tests run the same code the buttons do. The
controls are read once per refresh. The one thing read on a selection change is the selected control's space, and
only while a view is watching (watch_selection).
"""

from __future__ import annotations

import dataclasses

import maya.cmds as cmds
import rigmodules.pose
import rigmodules.query

import bmaya.core.log
import bmaya.core.observable
import bmaya.maya.activerig
import bmaya.maya.eventsregistry
import bmaya.maya.posetools

SELECTION_CALLBACK = "rig_panel_selection_changed"


@dataclasses.dataclass(frozen=True)
class ControlGroup:
    """The controls of one module on one side, in the module's control order. A module with controls on two
    sides gives two groups. Names are the controls' names as the commands return them."""

    module: str
    module_type: str
    side: str
    controls: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class SpaceState:
    """The space switch of the one selected control: the control, its constraint ("" for a module-owned space such
    as the TwoBoneIk pole's), the space labels in order, and the index of the space the control is in."""

    control: str
    constraint: str
    labels: tuple[str, ...]
    current: int


def group_controls(controls: list[rigmodules.query.RigControl]) -> list[ControlGroup]:
    """Groups controls by (module, side), in the order each group first appears."""
    members: dict[tuple[str, str], list[rigmodules.query.RigControl]] = {}
    for control in controls:
        members.setdefault((control.module, control.side), []).append(control)
    return [ControlGroup(module, group[0].module_type, side, tuple(control.node for control in group))
            for (module, side), group in members.items()]


class RigPanelSession:
    """State and commands of the active rig panel.

    changed emits with no arguments when the panel should read rigs, rig and groups again: the active rig
    changed, or the scene's rigs did. The session follows ActiveRigTracker.changed and never changes the active
    rig except through set_active. spaces_changed emits when space does: the selected control's space switch, or
    None unless exactly one control is selected and it has one.
    """

    def __init__(self) -> None:
        self.changed = bmaya.core.observable.Event()
        self.spaces_changed = bmaya.core.observable.Event()
        self.space: SpaceState | None = None
        self.rigs: list[rigmodules.query.RigInfo] = []
        self.rig: rigmodules.query.RigInfo | None = None
        self.groups: list[ControlGroup] = []
        bmaya.maya.activerig.ActiveRigTracker()   # the singleton: starts the callbacks when none runs
        bmaya.maya.activerig.ActiveRigTracker.changed.connect(self._on_active_rig_changed)
        self.refresh()

    def close(self) -> None:
        """Stops following the tracker and the selection. A view calls it when its window is destroyed, so a closed
        panel isn't refreshed on every active rig change."""
        bmaya.maya.activerig.ActiveRigTracker.changed.disconnect(self._on_active_rig_changed)
        self.watch_selection(False)

    def watch_selection(self, watch: bool) -> None:
        """Follows the selection for the space switch while a view is showing, and stops when it isn't. Safe to
        call with the same value twice."""
        registry = bmaya.maya.eventsregistry.EventsRegistry()
        key = f"{SELECTION_CALLBACK}_{id(self)}"
        if watch and key not in registry.callbacks:
            registry.add_selection_changed_callback(key, self._on_selection_changed)
        elif not watch:
            registry.unregister(key)
        if watch:
            self.refresh_space()

    def refresh_space(self) -> None:
        """Reads the space switch of the selected control, and emits spaces_changed when it differs from before.
        Exactly one selected rig control is read, with one query. Nothing else is."""
        space = None
        controls = cmds.ls(selection=True, type=rigmodules.query.RIG_CONTROL_TYPE)
        if len(controls) == 1:
            try:
                found = rigmodules.query.find_control_space(controls[0])
            except RuntimeError as error:
                bmaya.core.log.error(f"The rig panel could not read the space of {controls[0]}: {error}")
                found = None
            if found is not None:
                space = SpaceState(controls[0], found.constraint, found.labels, found.current)
        if space != self.space:
            self.space = space
            self.spaces_changed.emit()

    def set_space(self, label: str, key: bool = False) -> None:
        """Switches the selected control to the space labelled label. The control keeps its place in the world
        (setRigControlSpace). With key, the control's channels are keyed on the previous frame first and on the
        current frame after, so the animation holds the old space up to the cut. One undo reverts all of it."""
        space = self.space
        if space is None:
            raise RuntimeError("Select one control that has a space switch.")
        if label not in space.labels:
            raise RuntimeError(f"{space.control} has no space labelled {label!r}. It has: {', '.join(space.labels)}.")
        if space.labels.index(label) == space.current:
            return
        cmds.undoInfo(openChunk=True, chunkName="Switch space")
        try:
            if key:
                rigmodules.pose.key_controls([space.control], time=cmds.currentTime(query=True) - 1)
            cmds.setRigControlSpace(space.control, label=label)
            if key:
                rigmodules.pose.key_controls([space.control])
        finally:
            cmds.undoInfo(closeChunk=True)
        self.refresh_space()

    def refresh(self) -> None:
        """Reads the scene's rigs and the active rig's controls. A broken rig is logged and shown as no rig, so
        a Qt slot never raises."""
        self.rigs = []
        self.rig = None
        self.groups = []
        try:
            self.rigs = rigmodules.query.get_rigs()
            tracker = bmaya.maya.activerig.ActiveRigTracker.current()
            rig_root = tracker.rig_root if tracker is not None else None
            self.rig = next((rig for rig in self.rigs if rig.rig_root == rig_root), None)
            if self.rig is not None:
                self.groups = group_controls(rigmodules.query.get_rig_controls(self.rig.rig_root))
        except RuntimeError as error:
            bmaya.core.log.error(f"The rig panel could not read the rig: {error}")
            self.rigs, self.rig, self.groups = [], None, []
        self.changed.emit()
        self.refresh_space()   # the selected control may belong to another rig now

    def set_active(self, rig_root: str) -> None:
        """Makes a rig of the scene the active rig. The tracker announces it and the session refreshes."""
        if all(rig.rig_root != rig_root for rig in self.rigs):
            raise RuntimeError(f"{rig_root} is not a rig in the scene. Refresh the panel.")
        bmaya.maya.activerig.ActiveRigTracker().set_rig_root(rig_root)

    def select_group(self, group: ControlGroup, add: bool = False) -> None:
        """Selects the group's controls, or adds them to the selection."""
        if add:
            cmds.select(list(group.controls), add=True)
        else:
            cmds.select(list(group.controls), replace=True)

    def select_all(self) -> None:
        bmaya.maya.posetools.select_all_controls_interactive()

    def select_mirrors(self) -> None:
        bmaya.maya.posetools.select_mirror_controls_interactive()

    def zero(self) -> None:
        bmaya.maya.posetools.zero_pose(bmaya.maya.posetools.get_scope())

    def mirror(self, left_to_right: bool | None = None) -> None:
        bmaya.maya.posetools.mirror_pose(bmaya.maya.posetools.get_scope(), left_to_right)

    def flip(self) -> None:
        bmaya.maya.posetools.flip_pose(bmaya.maya.posetools.get_scope())

    def key_rig(self) -> None:
        bmaya.maya.posetools.key_all_controls_interactive()

    def key_modules(self) -> None:
        bmaya.maya.posetools.key_selected_modules_interactive()

    def _on_active_rig_changed(self, rig_root: str | None) -> None:
        self.refresh()

    def _on_selection_changed(self, *args) -> None:
        self.refresh_space()
