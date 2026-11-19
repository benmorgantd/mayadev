"""A set of named fields edited across several objects at once: what each field is, and what its values are over the
selection (RigModules design/asset-editor.md, D61). No Maya, no Qt.

A view-model describes its fields with FieldSpec and reports each field's value over the selection with FieldState:
one value when every object agrees, "mixed" when they don't. A form widget (bmaya.maya_ui.assetwidgets.MixedFieldForm)
draws them and reports an edit as (name, value), so the joint markup and the control shapes share one editor.

    state = combine([1.0, 1.0, 2.0])      # FieldState(value=None, mixed=True, count=3)
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

KINDS = ("choice", "text", "bool", "float")
FLOAT_TOLERANCE = 1e-6


@dataclasses.dataclass(frozen=True)
class FieldSpec:
    """One field. kind is "choice" (one of options), "text" (free text, options are suggestions), "bool" or "float"."""

    name: str
    label: str
    kind: str
    options: tuple[str, ...] = ()
    tip: str = ""

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"Field {self.name!r} has kind {self.kind!r}, not one of {KINDS}.")


@dataclasses.dataclass(frozen=True)
class FieldState:
    """A field's value over count objects. value is None when count is 0 or the values are mixed."""

    value: object = None
    mixed: bool = False
    count: int = 0


def same(a: object, b: object) -> bool:
    """Whether two field values are one value: floats within FLOAT_TOLERANCE, anything else equal."""
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= FLOAT_TOLERANCE
        except (TypeError, ValueError):
            return False
    return a == b


def combine(values: Sequence[object]) -> FieldState:
    """The state of a field whose value on each object is in values."""
    if not values:
        return FieldState()
    first = values[0]
    if all(same(first, other) for other in values[1:]):
        return FieldState(first, False, len(values))
    return FieldState(None, True, len(values))
