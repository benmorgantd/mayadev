"""Editors built from type hints, and the two forms made of them: a dataclass's fields (DataclassForm) and a
function's arguments (SignatureForm). Qt only, no Maya (RigModules design/mayadev-ui.md, D49).

field_widget makes one value's widget from its type hint, and show_value and read_value put a value in it and take
it out. A bool is a check box, an int or float a spin box, a str a line edit, a Literal or Enum a drop-down, and
anything else is JSON text.
"""

from __future__ import annotations

import dataclasses
import enum
import inspect
import json
import typing
from collections.abc import Callable

from PySide6 import QtCore, QtWidgets

from bmaya.core.tool_registry import unwrap_optional

SPIN_LIMIT = 1_000_000_000
ERROR_STYLE = "color: #e05555;"


def _is_enum(hint: object) -> bool:
    return inspect.isclass(hint) and issubclass(hint, enum.Enum)


def field_widget(hint: object, on_change: Callable[[], None] | None = None) -> QtWidgets.QWidget:
    """The editor for a value of this type. on_change is called, with no arguments, when the user edits it."""
    hint = unwrap_optional(hint)
    if hint is bool:
        widget = QtWidgets.QCheckBox()
        signal = widget.toggled
    elif hint is int:
        widget = QtWidgets.QSpinBox()
        widget.setRange(-SPIN_LIMIT, SPIN_LIMIT)
        signal = widget.valueChanged
    elif hint is float:
        widget = QtWidgets.QDoubleSpinBox()
        widget.setRange(-float(SPIN_LIMIT), float(SPIN_LIMIT))
        widget.setDecimals(6)
        signal = widget.valueChanged
    elif hint is str:
        widget = QtWidgets.QLineEdit()
        signal = widget.textChanged
    elif typing.get_origin(hint) is typing.Literal:
        widget = QtWidgets.QComboBox()
        for option in typing.get_args(hint):
            widget.addItem(str(option), option)
        signal = widget.currentIndexChanged
    elif _is_enum(hint):
        widget = QtWidgets.QComboBox()
        for member in hint:
            widget.addItem(member.name, member.value)
        signal = widget.currentIndexChanged
    else:
        widget = QtWidgets.QLineEdit()
        widget.setPlaceholderText("JSON value")
        signal = widget.textChanged
    if on_change is not None:
        signal.connect(lambda *_: on_change())
    return widget


def show_value(widget: QtWidgets.QWidget, hint: object, value: object) -> None:
    """Shows value in a widget made by field_widget for the same hint. An Enum field takes a member or a member's
    value."""
    hint = unwrap_optional(hint)
    if _is_enum(hint) and isinstance(value, hint):
        value = value.value
    if isinstance(widget, QtWidgets.QCheckBox):
        widget.setChecked(bool(value))
    elif isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
        widget.setValue(value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0)
    elif isinstance(widget, QtWidgets.QComboBox):
        widget.setCurrentIndex(max(widget.findData(value), 0))
    elif hint is str:
        widget.setText("" if value is None else str(value))
    else:
        widget.setText("" if value is None or value is inspect.Parameter.empty else json.dumps(value))


def read_value(widget: QtWidgets.QWidget, hint: object) -> object:
    """The widget's value: an Enum field's member, not its value. Raises ValueError for JSON text that isn't
    JSON."""
    hint = unwrap_optional(hint)
    if isinstance(widget, QtWidgets.QCheckBox):
        return widget.isChecked()
    if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
        return widget.value()
    if isinstance(widget, QtWidgets.QComboBox):
        return hint(widget.currentData()) if _is_enum(hint) else widget.currentData()
    if hint is str:
        return widget.text()
    try:
        return json.loads(widget.text())
    except json.JSONDecodeError as err:
        raise ValueError(f"not valid JSON: {err}") from None


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
        self.hints: dict[str, object] = {}
        self.widgets: dict[str, QtWidgets.QWidget] = {}
        for field in dataclasses.fields(value):
            hint = hints.get(field.name, field.type)
            widget = field_widget(hint, self.changed.emit)
            show_value(widget, hint, getattr(value, field.name))
            layout.addRow(field.name.replace("_", " ").capitalize() + ":", widget)
            self.hints[field.name] = hint
            self.widgets[field.name] = widget

    def value(self) -> object:
        """The edited copy. Raises ValueError naming the field whose JSON text isn't JSON."""
        changes = {}
        for name, widget in self.widgets.items():
            try:
                changes[name] = read_value(widget, self.hints[name])
            except ValueError as err:
                raise ValueError(f"{name}: {err}") from None
        return dataclasses.replace(self._value, **changes)


@dataclasses.dataclass
class ArgumentRow:
    """One parameter of a SignatureForm: its editor and a Set box. An unset row shows the default greyed, and it
    is not saved."""

    name: str
    hint: object
    widget: QtWidgets.QWidget
    set_check: QtWidgets.QCheckBox

    @property
    def is_set(self) -> bool:
        return self.set_check.isChecked()

    def value(self) -> object:
        """The editor's value as the registry's JSON keeps it: an Enum member's value. Raises ValueError for JSON
        text that isn't JSON."""
        try:
            value = read_value(self.widget, self.hint)
        except ValueError as err:
            raise ValueError(f"argument '{self.name}' is {err}") from None
        return value.value if isinstance(value, enum.Enum) else value


class SignatureForm(QtWidgets.QWidget):
    """The arguments of a function, as one row per parameter, filled from the saved kwargs. A required parameter is
    always set. A kwarg the function no longer has gets a red row with a Remove button. Build a new form when the
    function changes."""

    changed = QtCore.Signal()

    def __init__(self, function: Callable | None = None, kwargs: dict[str, object] | None = None,
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        kwargs = kwargs or {}
        self._layout = QtWidgets.QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.rows: list[ArgumentRow] = []
        self._stale: dict[str, tuple[object, QtWidgets.QLabel, QtWidgets.QPushButton]] = {}

        parameters, hints = self._read_signature(function)
        for name, parameter in parameters.items():
            if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD,
                                  inspect.Parameter.POSITIONAL_ONLY):
                continue
            self._add_row(name, parameter, hints.get(name), kwargs)
        for name, value in kwargs.items():
            if name not in parameters:
                self._add_stale_row(name, value)

    @staticmethod
    def _read_signature(function: Callable | None) -> tuple[dict[str, inspect.Parameter], dict[str, object]]:
        if function is None:
            return {}, {}
        try:
            parameters = dict(inspect.signature(function).parameters)
        except (TypeError, ValueError):
            parameters = {}
        try:
            hints = typing.get_type_hints(function)
        except Exception:  # an annotation that can't be evaluated gives JSON text
            hints = {}
        return parameters, hints

    def _add_row(self, name: str, parameter: inspect.Parameter, hint: object, kwargs: dict[str, object]) -> None:
        has_default = parameter.default is not inspect.Parameter.empty
        widget = field_widget(hint, self.changed.emit)
        set_check = QtWidgets.QCheckBox("Set")
        set_check.setEnabled(has_default)
        show_value(widget, hint, parameter.default if has_default else None)
        row = ArgumentRow(name, hint, widget, set_check)
        if name in kwargs:
            show_value(widget, hint, kwargs[name])
        set_check.setChecked(not has_default or name in kwargs)
        widget.setEnabled(set_check.isChecked())
        set_check.toggled.connect(lambda checked, widget=widget: self._on_set_toggled(widget, checked))
        self.rows.append(row)
        index = len(self.rows) + len(self._stale) - 1
        default = f"  (default {parameter.default!r})" if has_default else ""
        self._layout.addWidget(QtWidgets.QLabel(f"{name}{default}"), index, 0)
        self._layout.addWidget(widget, index, 1)
        self._layout.addWidget(set_check, index, 2)

    def _on_set_toggled(self, widget: QtWidgets.QWidget, checked: bool) -> None:
        widget.setEnabled(checked)
        self.changed.emit()

    def _add_stale_row(self, name: str, value: object) -> None:
        label = QtWidgets.QLabel(f"{name} = {json.dumps(value)}  (not a parameter any more)")
        label.setStyleSheet(ERROR_STYLE)
        remove = QtWidgets.QPushButton("Remove")
        remove.clicked.connect(lambda: self.remove_stale(name))
        self._stale[name] = (value, label, remove)
        index = len(self.rows) + len(self._stale) - 1
        self._layout.addWidget(label, index, 0, 1, 2)
        self._layout.addWidget(remove, index, 2)

    @property
    def stale(self) -> dict[str, object]:
        """The saved kwargs the function no longer has, which are kept until removed."""
        return {name: entry[0] for name, entry in self._stale.items()}

    def remove_stale(self, name: str) -> None:
        _, label, button = self._stale.pop(name)
        label.deleteLater()
        button.deleteLater()
        self.changed.emit()

    def kwargs(self) -> dict[str, object]:
        """Only what was chosen: the set rows, and the stale kwargs not yet removed. Raises ValueError for JSON text
        that isn't JSON."""
        result = {row.name: row.value() for row in self.rows if row.is_set}
        result.update(self.stale)
        return result


class CollapsibleSection(QtWidgets.QFrame):
    """A framed section with a title that folds it: a down arrow when open, a right arrow when folded. Put the
    section's widgets in content_layout. The whole title bar is the button."""

    toggled = QtCore.Signal(bool)   # True when the section is now open

    def __init__(self, title: str, expanded: bool = True, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.header = QtWidgets.QToolButton()
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setAutoRaise(True)
        self.header.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        font = self.header.font()
        font.setBold(True)
        self.header.setFont(font)
        self.body = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.body)
        self.content_layout.setContentsMargins(6, 0, 6, 6)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.body)

        self.header.toggled.connect(self._on_toggled)
        self.header.setChecked(expanded)
        self._on_toggled(expanded)

    @property
    def is_expanded(self) -> bool:
        return self.header.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        self.header.setChecked(expanded)

    def _on_toggled(self, expanded: bool) -> None:
        self.header.setArrowType(QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow)
        self.body.setVisible(expanded)
        self.toggled.emit(expanded)
