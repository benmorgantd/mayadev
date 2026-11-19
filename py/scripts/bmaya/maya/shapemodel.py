"""The Asset Editor's Shapes tab view-model: the shape of the selected rig controls, edited across all of them
(RigModules design/asset-editor.md, D61).

No Qt. A view connects to changed and reads summary, fields and enum_names. A control's shape is plain attributes on its
rigControlNode (RigModules D26): shapeType, shapeTransform (a matrix), filled and wireframeAlpha. The model shows the
matrix as translate, rotate and scale, and sets them with setAttr, so RigModules changes nothing. An edit is either
"set" (every selected control gets the value) or "adjust" (each control's own value is changed by it: translate,
rotate and alpha add, scale multiplies), and is one undo step.

The model reads the scene only while it is active, which the window sets for the tab that is showing.
"""

from __future__ import annotations

import maya.cmds as cmds
import rigmodules.query

import bmaya.core.observable
from bmaya.core import shapemath
from bmaya.core.fieldset import FieldSpec, FieldState, combine

SET, ADJUST = "set", "adjust"
AXES = ("X", "Y", "Z")
MAX_CONTROLS = 2000   # a bigger selection is not read


def _transform_fields() -> tuple[FieldSpec, ...]:
    specs = [FieldSpec("scale", "Scale", "float", tip="All three axes at once")]
    for group, label in (("scale", "Scale"), ("translate", "Translate"), ("rotate", "Rotate")):
        specs.extend(FieldSpec(f"{group}{axis}", f"{label} {axis}", "float") for axis in AXES)
    return tuple(specs)


SHAPE_TYPE_FIELD = FieldSpec("shapeType", "Shape", "choice", tip="Its choices are the plugin's shape list: enum_names")
APPEARANCE_FIELDS = (
    SHAPE_TYPE_FIELD,
    FieldSpec("filled", "Filled", "bool", tip="Fill the shape at 0.75 of the wire's alpha"),
    FieldSpec("wireframeAlpha", "Alpha", "float", tip="0 to 1"),
)
TRANSFORM_FIELDS = _transform_fields()
_COMPONENTS = {f"{group}{axis}": (group, index) for group in ("translate", "rotate", "scale")
               for index, axis in enumerate(AXES)}


class ShapeModel:
    """The shapes of the selected rig controls. changed emits with no arguments after a read."""

    def __init__(self, selection_changed: bmaya.core.observable.Event) -> None:
        self.changed = bmaya.core.observable.Event()
        self.active = False
        self.controls: list[str] = []
        self.fields: dict[str, FieldState] = {}
        self.enum_names: list[str] = []          # the shape types, in the order of the attribute's enum
        self.summary = ""
        selection_changed.connect(self._on_selection_changed)

    # ---- reading ---------------------------------------------------------------------------

    def set_active(self, active: bool) -> None:
        """A view calls it with True while the tab shows (and reads the selection then), False when it hides."""
        self.active = active
        if active:
            self.refresh()

    def refresh(self) -> None:
        """Reads the selected rig controls' shapes again."""
        selected = cmds.ls(selection=True, long=True) or []
        self.controls, self.fields = [], {}
        if len(selected) > MAX_CONTROLS:
            self.summary = f"{len(selected)} objects are selected. Select fewer to see their shapes."
            self.changed.emit()
            return
        self.controls = cmds.ls(selected, type=rigmodules.query.RIG_CONTROL_TYPE, long=True) or []
        if self.controls:
            self.enum_names = self._enum_names(self.controls[0])
            self.fields = self._read_fields()
            self.summary = f"{len(self.controls)} rig control(s)"
        else:
            self.summary = "Select rig controls."
        self.changed.emit()

    @staticmethod
    def _enum_names(control: str) -> list[str]:
        listed = cmds.attributeQuery("shapeType", node=control, listEnum=True) or [""]
        return listed[0].split(":")

    def _read_fields(self) -> dict[str, FieldState]:
        names = self.enum_names
        values: dict[str, list] = {"shapeType": [], "filled": [], "wireframeAlpha": [], "scale": []}
        for name in _COMPONENTS:
            values[name] = []
        for control in self.controls:
            values["shapeType"].append(names[cmds.getAttr(control + ".shapeType")])
            values["filled"].append(bool(cmds.getAttr(control + ".filled")))
            values["wireframeAlpha"].append(float(cmds.getAttr(control + ".wireframeAlpha")))
            translate, rotate, scale = shapemath.decompose(cmds.getAttr(control + ".shapeTransform"))
            parts = {"translate": translate, "rotate": rotate, "scale": scale}
            for name, (group, index) in _COMPONENTS.items():
                values[name].append(parts[group][index])
            values["scale"].append(scale[0] if abs(scale[0] - scale[1]) < 1e-6 and abs(scale[0] - scale[2]) < 1e-6 else None)
        return {name: combine(found) if None not in found else FieldState(None, True, len(found))
                for name, found in values.items()}

    # ---- editing ---------------------------------------------------------------------------

    def set_field(self, name: str, value: object, mode: str = SET) -> list[str]:
        """Sets one field on every selected control. mode is SET (the value replaces the field) or ADJUST (translate,
        rotate and alpha add the value to each control's own, scale multiplies it, and a shape type or a check box is
        set as in SET). Raises RuntimeError for no rig control selected, an unknown field or mode, or a value that is
        not valid, and changes nothing. Returns the controls changed."""
        if mode not in (SET, ADJUST):
            raise RuntimeError(f"The mode must be {SET!r} or {ADJUST!r}, not {mode!r}.")
        self.refresh()   # the scene may have changed since the last selection
        if not self.controls:
            raise RuntimeError("Select rig controls.")
        edit = self._make_edit(name, value, mode)
        controls = list(self.controls)
        cmds.undoInfo(openChunk=True, chunkName="Set Control Shapes")
        try:
            for control in controls:
                edit(control)
        finally:
            cmds.undoInfo(closeChunk=True)
        self.refresh()
        return controls

    def _make_edit(self, name: str, value: object, mode: str):
        """A function of a control that applies the edit. Every check is done here, before any control is touched."""
        if name == "shapeType":
            if value not in self.enum_names:
                raise RuntimeError(f"{value!r} is not a shape. The shapes are: {', '.join(self.enum_names)}.")
            index = self.enum_names.index(value)
            return lambda control: cmds.setAttr(control + ".shapeType", index)
        if name == "filled":
            flag = bool(value)
            return lambda control: cmds.setAttr(control + ".filled", flag)
        if name != "wireframeAlpha" and name != "scale" and name not in _COMPONENTS:
            raise RuntimeError(f"{name!r} is not a shape field.")
        number = self._number(name, value)
        if name == "wireframeAlpha":
            def alpha(control):
                current = cmds.getAttr(control + ".wireframeAlpha")
                new = current + number if mode == ADJUST else number
                cmds.setAttr(control + ".wireframeAlpha", min(1.0, max(0.0, new)))
            return alpha

        group, indexes = ("scale", (0, 1, 2)) if name == "scale" else (_COMPONENTS[name][0], (_COMPONENTS[name][1],))
        if group == "scale" and number == 0.0:
            raise RuntimeError("A scale of 0 flattens the shape. Use a small number.")

        def transform(control):
            translate, rotate, scale = (list(part) for part in
                                        shapemath.decompose(cmds.getAttr(control + ".shapeTransform")))
            target = {"translate": translate, "rotate": rotate, "scale": scale}[group]
            for index in indexes:
                if mode == SET:
                    target[index] = number
                elif group == "scale":
                    target[index] *= number
                else:
                    target[index] += number
            cmds.setAttr(control + ".shapeTransform", *shapemath.compose(translate, rotate, scale), type="matrix")
        return transform

    @staticmethod
    def _number(name: str, value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise RuntimeError(f"{name} needs a number, not {value!r}.") from None

    def mirror(self, left_to_right: bool, fallback_rig_root: str | None = None) -> list[str]:
        """Mirrors the control shapes of every rig the selected controls belong to, or of fallback_rig_root when
        none is selected: Left onto Right, or Right onto Left (mirrorRigControlShapes). Returns the controls changed."""
        roots: list[str] = []
        for control in self.controls:
            info = rigmodules.query.find_rig_info(control)
            if info is not None and info.rig_root not in roots:
                roots.append(info.rig_root)
        if not roots and fallback_rig_root:
            roots.append(fallback_rig_root)
        if not roots:
            raise RuntimeError("Select rig controls, or choose a rig that is in the scene.")
        changed: list[str] = []
        cmds.undoInfo(openChunk=True, chunkName="Mirror Control Shapes")
        try:
            for root in roots:
                changed.extend(cmds.mirrorRigControlShapes(root, leftToRight=left_to_right) or [])
        finally:
            cmds.undoInfo(closeChunk=True)
        self.refresh()
        return changed

    def _on_selection_changed(self) -> None:
        if self.active:
            self.refresh()
