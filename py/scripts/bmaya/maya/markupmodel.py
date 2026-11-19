"""The Asset Editor's Markup tab view-model: the joint markup and rig control markup of the selection, and the commands
that edit it across all of the selected joints (RigModules design/asset-editor.md, D61).

No Qt. A view connects to changed and reads summary, fields, marked, unmarked, controls, usages and warnings. Joint
markup is edited through RigModules' rigJointMarkup. Control markup is shown and never edited, because the build owns it
and it is unique per rig (RigModules D25). The model reads the scene only while it is active, which the window sets for
the tab that is showing, so selecting in a big scene costs nothing when the tab is not.

An edit is one undo step. A (side, usage) pair is unique per skeleton, so an edit that would give two joints of one
namespace the same pair is refused before it touches anything.
"""

from __future__ import annotations

import json

import maya.cmds as cmds
import rigmodules.query

import bmaya.core.log
import bmaya.core.observable
import bmaya.core.prompts
import bmaya.maya.assettools
from bmaya.core.fieldset import FieldSpec, FieldState, combine

SIDES = ("Center", "Left", "Right")
JOINT_FIELDS = (
    FieldSpec("usage", "Usage", "text", tip="What the joint is, for example upperArm. Templates select joints by it."),
    FieldSpec("side", "Side", "choice", SIDES),
    FieldSpec("export", "Export", "bool", tip="The joint is exported to the engine."),
    FieldSpec("skin", "Skin", "bool", tip="The joint is a skin joint."),
)
MAX_SELECTED = 2000   # a bigger selection is not read: select all costs nothing
MAX_CONTROLS_LISTED = 200


def namespace_of(node: str) -> str:
    """The namespace of a node's leaf name, without the trailing colon: "" for the root namespace."""
    leaf = node.rsplit("|", 1)[-1]
    return leaf.rpartition(":")[0]


class MarkupModel:
    """The markup of the selection. changed emits with no arguments after a read."""

    def __init__(self, selection_changed: bmaya.core.observable.Event) -> None:
        self.changed = bmaya.core.observable.Event()
        self.active = False
        self.joints: list[str] = []                 # the selected joints, long names, in selection order
        self.marked: dict[str, dict] = {}           # the marked ones among them, with their markup
        self.unmarked: list[str] = []
        self.controls: list[rigmodules.query.RigControl] = []
        self.controls_selected = 0
        self.fields: dict[str, FieldState] = {}
        self.usages: list[str] = []                 # the usages in the scene, for suggestions
        self.warnings: list[str] = []
        self.summary = ""
        self._scene: dict[str, dict] = {}           # every marked joint in the scene, long name to markup
        selection_changed.connect(self._on_selection_changed)

    # ---- reading ---------------------------------------------------------------------------

    def set_active(self, active: bool) -> None:
        """A view calls it with True while the tab shows (and reads the selection then), False when it hides."""
        self.active = active
        if active:
            self.refresh()

    def refresh(self) -> None:
        """Reads the selection and the scene's markup again."""
        selected = cmds.ls(selection=True, long=True) or []
        self.joints, self.marked, self.unmarked = [], {}, []
        self.controls, self.controls_selected, self.fields, self.warnings = [], 0, {}, []
        if len(selected) > MAX_SELECTED:
            self.summary = f"{len(selected)} objects are selected. Select fewer to see their markup."
            self.changed.emit()
            return
        self.joints = cmds.ls(selected, type="joint", long=True) or []
        control_nodes = cmds.ls(selected, type=rigmodules.query.RIG_CONTROL_TYPE, long=True) or []
        self.controls_selected = len(control_nodes)
        self.controls = self._read_controls(control_nodes[:MAX_CONTROLS_LISTED])
        if self.joints:
            self._scene = self._read_scene()
            self.marked = {joint: self._scene[joint] for joint in self.joints if joint in self._scene}
            self.unmarked = [joint for joint in self.joints if joint not in self._scene]
            self.usages = sorted({markup["usage"] for markup in self._scene.values()})
            self.fields = {spec.name: combine([markup[spec.name] for markup in self.marked.values()])
                           for spec in JOINT_FIELDS}
            self.warnings = self._duplicate_warnings(self._scene)
        self.summary = self._summary()
        self.changed.emit()

    def _summary(self) -> str:
        parts = []
        if self.joints:
            parts.append(f"{len(self.joints)} joint(s): {len(self.marked)} marked, {len(self.unmarked)} not")
        if self.controls_selected:
            parts.append(f"{self.controls_selected} rig control(s)")
        return ", ".join(parts) if parts else "Select joints or rig controls."

    def _read_scene(self) -> dict[str, dict]:
        """The markup of every marked joint in the scene, by long name: one command, so a selection change in a
        scene with many joints stays cheap."""
        joints = cmds.ls(type="joint", long=True) or []
        if not joints:
            return {}
        raw = cmds.rigJointMarkup(*joints, query=True) or []
        return {joint: json.loads(text) for joint, text in zip(joints, raw) if text}

    def _read_controls(self, nodes: list[str]) -> list[rigmodules.query.RigControl]:
        controls = []
        for node in nodes:
            try:
                control = rigmodules.query.find_control(node)
            except RuntimeError as error:
                bmaya.core.log.error(f"The Asset Editor could not read the markup of {node}: {error}")
                continue
            if control is not None:
                controls.append(control)
        return controls

    @staticmethod
    def _duplicate_groups(scene: dict[str, dict]) -> dict[tuple[str, str, str], list[str]]:
        """The joints that share a (namespace, side, usage), keyed by it. The build fails on them."""
        holders: dict[tuple[str, str, str], list[str]] = {}
        for joint, markup in scene.items():
            holders.setdefault((namespace_of(joint), markup["side"], markup["usage"]), []).append(joint)
        return {key: joints for key, joints in sorted(holders.items()) if len(joints) > 1}

    @classmethod
    def _duplicate_warnings(cls, scene: dict[str, dict]) -> list[str]:
        return [f"{len(joints)} joints share side {side} and usage {usage!r}: "
                + ", ".join(joint.rsplit("|", 1)[-1] for joint in joints)
                for (_namespace, side, usage), joints in cls._duplicate_groups(scene).items()]

    # ---- editing ---------------------------------------------------------------------------

    def set_field(self, name: str, value: object) -> None:
        """Sets one markup value on every selected joint that has markup. Raises RuntimeError when no selected joint
        has markup, the value is not valid, or the edit would give two joints one side and usage."""
        if name not in {spec.name for spec in JOINT_FIELDS}:
            raise RuntimeError(f"{name!r} is not a markup field.")
        self.refresh()   # the scene may have changed since the last selection
        targets = list(self.marked)
        if not targets:
            raise RuntimeError("None of the selected joints has markup. Add markup first.")
        value = self._check_value(name, value)
        if name in ("usage", "side"):
            self._check_unique({joint: {**self.marked[joint], name: value} for joint in targets})
        self._undoable("Set Joint Markup", lambda: cmds.rigJointMarkup(*targets, edit=True, **{name: value}))
        self.refresh()

    def add_markup(self, usage: str, side: str = "Center", export: bool = True, skin: bool = True,
                   numbered: bool = False) -> list[str]:
        """Gives markup to the selected joints that have none. With numbered, the joints are named usage_00, usage_01
        and so on in selection order, which is how Add Twist Joints names its usages. Without it, only one joint can be
        marked, since two joints may not share a side and usage. Returns the joints marked."""
        self.refresh()
        targets = list(self.unmarked)
        if not targets:
            raise RuntimeError("Every selected joint already has markup.")
        usage = self._check_value("usage", usage)
        side = self._check_value("side", side)
        if len(targets) > 1 and not numbered:
            raise RuntimeError(f"{len(targets)} joints can't all be {usage!r} on one side. Tick Number them, or "
                               "mark one joint at a time.")
        usages = [f"{usage}_{index:02d}" for index in range(len(targets))] if numbered else [usage]
        self._check_unique({joint: {"usage": name, "side": side} for joint, name in zip(targets, usages)})

        def create() -> None:
            for joint, name in zip(targets, usages):
                cmds.rigJointMarkup(joint, usage=name, side=side, export=bool(export), skin=bool(skin))

        self._undoable("Add Joint Markup", create)
        self.refresh()
        return targets

    def remove(self) -> list[str]:
        """Removes the markup of the selected joints that have it. Returns them."""
        self.refresh()
        targets = list(self.marked)
        if not targets:
            raise RuntimeError("None of the selected joints has markup.")
        self._undoable("Remove Joint Markup", lambda: cmds.rigJointMarkup(*targets, remove=True))
        self.refresh()
        return targets

    def mirror_joints(self) -> list[str]:
        """Mirrors the selected _L_JNT joints onto _R_JNT joints (assettools.mirror_joints)."""
        if not self.joints:
            raise RuntimeError("Select joints.")
        mirrored = bmaya.maya.assettools.mirror_joints(self.joints)
        self.refresh()
        return mirrored

    def add_twist_joints(self, prompter: bmaya.core.prompts.Prompter | None = None) -> list[str] | None:
        """Asks for the twist settings and adds the joints between the two selected joints (the start, then the end).
        Returns the new joints, or None when cancelled."""
        joints = bmaya.maya.assettools.add_twist_joints_interactive(prompter)
        self.refresh()
        return joints

    # ---- helpers ---------------------------------------------------------------------------

    @staticmethod
    def _check_value(name: str, value: object) -> object:
        if name == "usage":
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError("A usage can't be empty.")
            return value.strip()
        if name == "side":
            if value not in SIDES:
                raise RuntimeError(f"The side must be one of {', '.join(SIDES)}, not {value!r}.")
            return value
        return bool(value)

    def _check_unique(self, changes: dict[str, dict]) -> None:
        """Raises when, after the changes (long name to the new markup values), two joints of one namespace would
        have the same side and usage."""
        final = {joint: {"side": markup["side"], "usage": markup["usage"]} for joint, markup in self._scene.items()}
        for joint, values in changes.items():
            final[joint] = {"side": values.get("side", final.get(joint, {}).get("side")),
                            "usage": values.get("usage", final.get(joint, {}).get("usage"))}
        for (_namespace, side, usage), joints in self._duplicate_groups(final).items():
            if any(joint in changes for joint in joints):
                names = ", ".join(joint.rsplit("|", 1)[-1] for joint in joints)
                raise RuntimeError(f"That would give {len(joints)} joints side {side} and usage {usage!r}, and a side "
                                   f"and usage must be unique on a skeleton: {names}")

    @staticmethod
    def _undoable(name: str, command) -> None:
        cmds.undoInfo(openChunk=True, chunkName=name)
        try:
            command()
        finally:
            cmds.undoInfo(closeChunk=True)

    def _on_selection_changed(self) -> None:
        if self.active:
            self.refresh()
