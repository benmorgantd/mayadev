"""Editors built from type hints, shared by every form: a dataclass's fields (DataclassForm) and a function's
arguments (the Registry Editor's argument form). Qt only, no Maya (RigModules design/mayadev-ui.md, D49)."""

from __future__ import annotations

import dataclasses
import enum
import inspect
import json
import types
import typing

from PySide6 import QtCore, QtWidgets

SPIN_LIMIT = 1_000_000_000


def unwrap_optional(hint: object) -> object:
    """X | None -> X. Anything else is returned as it is."""
    if typing.get_origin(hint) in (typing.Union, types.UnionType):
        options = [a for a in typing.get_args(hint) if a is not type(None)]
        if len(options) == 1:
            return options[0]
    return hint


class FieldEditor(QtCore.QObject):
    """One value's widget, chosen by its type hint: a check box for bool, spin boxes for int and float, a line edit
    for str, a drop-down for Literal and Enum, and JSON text for anything else."""

    changed = QtCore.Signal()

    def __init__(self, hint: object, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.hint = unwrap_optional(hint)
        self.is_json = False
        self.widget = self._make_widget()

    def _make_widget(self) -> QtWidgets.QWidget:
        hint = self.hint
        if hint is bool:
            widget = QtWidgets.QCheckBox()
            widget.toggled.connect(self.changed)
        elif hint is int:
            widget = QtWidgets.QSpinBox()
            widget.setRange(-SPIN_LIMIT, SPIN_LIMIT)
            widget.valueChanged.connect(self.changed)
        elif hint is float:
            widget = QtWidgets.QDoubleSpinBox()
            widget.setRange(-float(SPIN_LIMIT), float(SPIN_LIMIT))
            widget.setDecimals(6)
            widget.valueChanged.connect(self.changed)
        elif hint is str:
            widget = QtWidgets.QLineEdit()
            widget.textChanged.connect(self.changed)
        elif typing.get_origin(hint) is typing.Literal:
            widget = QtWidgets.QComboBox()
            for option in typing.get_args(hint):
                widget.addItem(str(option), option)
            widget.currentIndexChanged.connect(self.changed)
        elif inspect.isclass(hint) and issubclass(hint, enum.Enum):
            widget = QtWidgets.QComboBox()
            for member in hint:
                widget.addItem(member.name, member.value)
            widget.currentIndexChanged.connect(self.changed)
        else:
            self.is_json = True
            widget = QtWidgets.QLineEdit()
            widget.setPlaceholderText("JSON value")
            widget.textChanged.connect(self.changed)
        return widget

    @property
    def is_enum(self) -> bool:
        return inspect.isclass(self.hint) and issubclass(self.hint, enum.Enum)

    def show_value(self, value: object) -> None:
        """Shows value. An Enum field takes a member or a member's value."""
        widget = self.widget
        if self.is_enum and isinstance(value, self.hint):
            value = value.value
        if isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            widget.setValue(value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.setCurrentIndex(max(widget.findData(value), 0))
        elif self.is_json:
            widget.setText("" if value is None or value is inspect.Parameter.empty else json.dumps(value))
        else:
            widget.setText("" if value is None else str(value))

    def value(self) -> object:
        """The widget's value: an Enum field's member, not its value. Raises ValueError for JSON text that isn't
        JSON."""
        widget = self.widget
        if isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()
        if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            return widget.value()
        if isinstance(widget, QtWidgets.QComboBox):
            return self.hint(widget.currentData()) if self.is_enum else widget.currentData()
        if self.is_json:
            try:
                return json.loads(widget.text())
            except json.JSONDecodeError as err:
                raise ValueError(f"not valid JSON: {err}") from None
        return widget.text()


class DataclassForm(QtWidgets.QWidget):
    """A form for a dataclass instance: one labelled editor per field, in field order. value() returns a copy with
    the edited fields."""

    changed = QtCore.Signal()

    def __init__(self, value: object, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        if not dataclasses.is_dataclass(value) or isinstance(value, type):
            raise TypeError(f"DataclassForm needs a dataclass instance, not {value!r}")
        self._value = value
        hints = typing.get_type_hints(type(value))
        layout = QtWidgets.QFormLayout(self)
        self.editors: dict[str, FieldEditor] = {}
        for field in dataclasses.fields(value):
            editor = FieldEditor(hints.get(field.name, field.type), self)
            editor.show_value(getattr(value, field.name))
            editor.changed.connect(self.changed)
            layout.addRow(field.name.replace("_", " ").capitalize() + ":", editor.widget)
            self.editors[field.name] = editor

    def value(self) -> object:
        """The edited copy. Raises ValueError naming the field whose JSON text isn't JSON."""
        changes = {}
        for name, editor in self.editors.items():
            try:
                changes[name] = editor.value()
            except ValueError as err:
                raise ValueError(f"{name}: {err}") from None
        return dataclasses.replace(self._value, **changes)
