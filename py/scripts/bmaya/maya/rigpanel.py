"""The active rig panel's view-model: the rigs in the scene, the active rig's controls grouped by module and side,
and the commands the panel's buttons call (RigModules design/active-rig-panel.md, D50).

No Qt. A view connects to changed and reads rigs, rig and groups. Every command is a call into posetools or a
RigModules command, so mayapy and tests run the same code the buttons do. The controls are read once per refresh,
never per selection change.
"""

from __future__ import annotations

import dataclasses

import maya.cmds as cmds
import rigmodules.query

import bmaya.core.log
import bmaya.core.observable
import bmaya.maya.activerig
import bmaya.maya.posetools


@dataclasses.dataclass(frozen=True)
class ControlGroup:
    """The controls of one module on one side, in the module's control order. A module with controls on two
    sides gives two groups. Names are the controls' names as the commands return them."""

    module: str
    module_type: str
    side: str
    controls: tuple[str, ...]


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
    rig except through set_active.
    """

    def __init__(self) -> None:
        self.changed = bmaya.core.observable.Event()
        self.rigs: list[rigmodules.query.RigInfo] = []
        self.rig: rigmodules.query.RigInfo | None = None
        self.groups: list[ControlGroup] = []
        bmaya.maya.activerig.ActiveRigTracker()   # the singleton: starts the callbacks when none runs
        bmaya.maya.activerig.ActiveRigTracker.changed.connect(self._on_active_rig_changed)
        self.refresh()

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

    def set_active(self, rig_root: str) -> None:
        """Makes a rig of the scene the active rig. The tracker announces it and the session refreshes."""
        if all(rig.rig_root != rig_root for rig in self.rigs):
            raise RuntimeError(f"{rig_root} is not a rig in the scene. Refresh the panel.")
        bmaya.maya.activerig.ActiveRigTracker().set_rig_root(rig_root)

    def select_controls(self, controls: list[str] | tuple[str, ...], add: bool = False) -> None:
        """Selects the controls, or adds them to the selection."""
        if add:
            cmds.select(list(controls), add=True)
        else:
            cmds.select(list(controls), replace=True)

    def select_group(self, group: ControlGroup, add: bool = False) -> None:
        """Selects the group's controls, or adds them to the selection."""
        self.select_controls(group.controls, add)

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
