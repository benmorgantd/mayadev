"""The Asset Editor's Naming tab view-model: renames the selected joints, rig controls, modules and constraints into the
naming convention (RigModules docs/naming.md, D58), numbered and sided, and mirrors a side onto the other.

No Qt. A view connects to changed and reads nodes, base, side, start_index and summary. Every rule lives in RigModules'
renameRigNodes (through rigmodules.naming), so this model only reads the selection and calls it. The model reads the
scene only while it is active, which the window sets for the tab that is showing.

The nodes are numbered in selection order, which Maya tracks only while selectPref(trackSelectionOrder) is on, so the
model turns it on when it becomes active. A rename is one undo step.
"""

from __future__ import annotations

import maya.cmds as cmds
import rigmodules.naming

import bmaya.core.observable

SIDES = ("Left", "Right", "Center")
OPPOSITE = {"Left": "Right", "Right": "Left"}
MAX_SELECTED = 2000   # a bigger selection is not read


class NamingModel:
    """The naming of the selection. changed emits with no arguments after a read.

    base, side and start_index are what the view shows and the user edits. A selection change fills base and side from
    the first selected node that is already in the convention, and leaves them alone when none is."""

    def __init__(self, selection_changed: bmaya.core.observable.Event) -> None:
        self.changed = bmaya.core.observable.Event()
        self.active = False
        self.nodes: list[str] = []           # the selected nodes, long names, in selection order
        self.base = ""
        self.side = "Center"
        self.start_index = 0
        self.summary = ""
        selection_changed.connect(self._on_selection_changed)

    # ---- reading ---------------------------------------------------------------------------

    def set_active(self, active: bool) -> None:
        """A view calls it with True while the tab shows (and reads the selection then), False when it hides."""
        self.active = active
        if active:
            cmds.selectPref(trackSelectionOrder=True)
            self.refresh()

    def refresh(self) -> None:
        """Reads the selection again, and fills base, side and the start index from its first named node."""
        selected = cmds.ls(selection=True, long=True) or []
        if len(selected) > MAX_SELECTED:
            self.nodes = []
            self.summary = f"{len(selected)} objects are selected. Select fewer to rename them."
            self.changed.emit()
            return
        self.nodes = selected
        first = next((parts for parts in map(self._parse, selected) if parts is not None), None)
        if first is not None:
            self.base, self.side, self.start_index = first.base, first.side, first.index
        self.summary = self._summary()
        self.changed.emit()

    def _summary(self) -> str:
        if not self.nodes:
            return "Select joints, rig controls, modules, constraints or meshes."
        leaf = self.nodes[0].rsplit("|", 1)[-1]
        more = f" and {len(self.nodes) - 1} more" if len(self.nodes) > 1 else ""
        return f"{len(self.nodes)} node(s): {leaf}{more}"

    @staticmethod
    def _parse(node: str) -> rigmodules.naming.RigName | None:
        try:
            return rigmodules.naming.parse(node.rsplit("|", 1)[-1])   # the query reads a name, not a DAG path
        except RuntimeError:   # a node with no name the convention can read, such as a mesh
            return None

    # ---- editing ---------------------------------------------------------------------------

    def rename(self, base: str, side: str, start_index: int) -> list[str]:
        """Renames the selected nodes to base_##_side_KIND, counting up from start_index in selection order. Returns the
        new names. Raises RuntimeError for an empty selection, a side that is not one of SIDES or a bad base, and when a
        name is taken (renameRigNodes changes nothing then)."""
        self.refresh()
        if not self.nodes:
            raise RuntimeError("Select the nodes to rename.")
        base = base.strip()
        if not base:
            raise RuntimeError("Type a name root, such as upperArm.")
        if side not in SIDES:
            raise RuntimeError(f"The side must be one of {', '.join(SIDES)}, not {side!r}.")
        if start_index < 0:
            raise RuntimeError("The start number can't be negative.")
        names = rigmodules.naming.rename_nodes(self.nodes, base=base, side=side, start_index=start_index)
        self.base, self.side, self.start_index = base, side, start_index
        self.refresh()
        return names

    def mirror(self) -> list[str]:
        """Swaps Left and Right in the name of every selected node, keeping its root and number: arm_01_L_JNT becomes
        arm_01_R_JNT. Raises RuntimeError when a selected node is not in the convention or is Center, and when a
        mirrored name is taken. Either nothing is renamed or every node is. Returns the new names."""
        self.refresh()
        if not self.nodes:
            raise RuntimeError("Select the nodes to mirror.")
        parts = {node: self._parse(node) for node in self.nodes}
        for node, name in parts.items():
            if name is None:
                raise RuntimeError(f"{node.rsplit('|', 1)[-1]} is not in the naming convention. Rename it first.")
            if name.side not in OPPOSITE:
                raise RuntimeError(f"{node.rsplit('|', 1)[-1]} is on the Center, so it has no other side.")
        names: list[str] = []
        cmds.undoInfo(openChunk=True, chunkName="Mirror Names")
        try:
            for node, name in parts.items():
                names += rigmodules.naming.rename_nodes([node], base=name.base, side=OPPOSITE[name.side],
                                                        start_index=name.index)
        except RuntimeError:
            cmds.undoInfo(closeChunk=True)
            cmds.undo()   # the nodes renamed before the failure
            self.refresh()
            raise
        cmds.undoInfo(closeChunk=True)
        self.refresh()
        return names

    def _on_selection_changed(self) -> None:
        if self.active:
            self.refresh()
