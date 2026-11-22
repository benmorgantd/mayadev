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

from PySide6 import QtCore, QtGui, QtWidgets

from bmaya.core.asset.textures import IMAGE_EXTENSIONS
from bmaya.core.prompts import ImagePath
from bmaya.core.tool_registry import unwrap_optional
from bmaya.maya_ui import theme

SPIN_LIMIT = 1_000_000_000
ERROR_STYLE = f"color: {theme.DARK.error};"


def menu_action(menu: QtWidgets.QMenu, text: str) -> QtGui.QAction:
    """A new action of the menu. It is made here and parented to the menu, because the action addAction(text) makes was
    found deleted in a GUI Maya while the window still held it."""
    action = QtGui.QAction(text, menu)
    menu.addAction(action)
    return action


class PathEdit(QtWidgets.QWidget):
    """A line for a file's path with a Browse button, for an ImagePath field. line is the editable text."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.line = QtWidgets.QLineEdit()
        self.line.setPlaceholderText("none")
        self.browse_button = QtWidgets.QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse)
        layout.addWidget(self.line, 1)
        layout.addWidget(self.browse_button)

    def browse(self) -> None:
        """Asks for an image file, starting beside the current one. Cancel changes nothing."""
        patterns = " ".join("*" + extension for extension in IMAGE_EXTENSIONS)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Pick an image", self.line.text(), f"Images ({patterns})")
        if path:
            self.line.setText(path)


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
    elif hint is ImagePath:
        widget = PathEdit()
        signal = widget.line.textChanged
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
    elif isinstance(widget, PathEdit):
        widget.line.setText("" if value is None else str(value))
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
    if isinstance(widget, PathEdit):
        return ImagePath(widget.line.text().strip())
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
    """A framed section with a title bar that folds it: a down chevron when open, a right chevron when folded. Put
    the section's widgets in content_layout. The whole title bar is the button. theme.py styles it by its object
    names."""

    toggled = QtCore.Signal(bool)   # True when the section is now open

    def __init__(self, title: str, expanded: bool = True, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("collapsibleSection")
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)   # theme.py draws the frame
        self.header = QtWidgets.QPushButton()
        self.header.setObjectName("sectionHeader")
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.header.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.header.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.body = QtWidgets.QWidget()
        self.body.setObjectName("collapsibleBody")
        self.content_layout = QtWidgets.QVBoxLayout(self.body)
        self.content_layout.setContentsMargins(8, 8, 8, 8)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
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
        self.header.setIcon(theme.icon("chevron_down" if expanded else "chevron_right"))
        self.body.setVisible(expanded)
        self.toggled.emit(expanded)


class TagsEdit(QtWidgets.QLineEdit):
    """A line of comma-separated tags. While the animator types a tag, a pop-up offers the tags in use that start with
    it (set_tags_in_use), and picking one replaces the word under the cursor, so a library keeps one spelling of a tag.

        edit.set_tags_in_use(["hands", "fist"])
        edit.tags()          # ["hands", "fist"] for the text "hands, fist,"
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = QtCore.QStringListModel(self)
        self._completer = QtWidgets.QCompleter(self._model, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self._completer.activated[str].connect(self.complete_word)
        self.textEdited.connect(self._offer)

    def set_tags_in_use(self, tags: list[str]) -> None:
        self._model.setStringList(list(tags))

    def tags(self) -> list[str]:
        """The tags in the text, trimmed, with no empty ones and no repeats, in order."""
        return list(dict.fromkeys(tag.strip() for tag in self.text().split(",") if tag.strip()))

    def set_tags(self, tags: list[str]) -> None:
        self.setText(", ".join(tags))

    def word_before_cursor(self) -> str:
        """The part of the tag being typed that is left of the cursor."""
        head = self.text()[:self.cursorPosition()]
        return head[head.rfind(",") + 1:].lstrip()

    def complete_word(self, completion: str) -> None:
        """Replaces the tag under the cursor with completion."""
        text, cursor = self.text(), self.cursorPosition()
        start = text[:cursor].rfind(",") + 1
        head = text[:start] + (" " if start else "") + completion
        self.setText(head + text[cursor:])
        self.setCursorPosition(len(head))

    def _offer(self) -> None:
        word = self.word_before_cursor()
        if not word:
            self._completer.popup().hide()
            return
        self._completer.setCompletionPrefix(word)
        self._completer.complete()


class ListModel(QtCore.QAbstractTableModel):
    """A Qt item model over a Python list: the rows are the items, and each role is a function of an item. It holds no
    logic of the list's owner, so a view-model sets the items and a view shows them, as a QListView (one column), or a
    QTableView (columns). The search box is a QSortFilterProxyModel over it, or the view-model's own filtering.

        model = ListModel({QtCore.Qt.ItemDataRole.DisplayRole: lambda entry: entry.name}, entries)
        model.set_items(new_entries)          # a reset: a view keeps its selection by finding the row again

    columns is a list of (header, display function). With none, there is one column whose text comes from roles.
    A role other than the display one (decoration, tool tip, UserRole) applies to every column.
    """

    def __init__(
        self,
        roles: dict[int, Callable[[object], object]],
        items: list | tuple = (),
        columns: list[tuple[str, Callable[[object], object]]] | None = None,
        parent: QtCore.QObject | None = None,
    ):
        super().__init__(parent)
        self._roles = dict(roles)
        self._columns = list(columns or [])
        self._items = list(items)

    @property
    def items(self) -> list:
        return list(self._items)

    def set_items(self, items: list | tuple) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def item(self, row: int) -> object:
        return self._items[row]

    def row_of(self, matches: Callable[[object], bool]) -> int:
        """The row of the first item for which matches is true, or -1. How a view finds its selection after a reset."""
        return next((row for row, item in enumerate(self._items) if matches(item)), -1)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else max(1, len(self._columns))

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        if role == QtCore.Qt.ItemDataRole.DisplayRole and self._columns:
            return self._columns[index.column()][1](item)
        function = self._roles.get(role)
        return function(item) if function else None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation,
                   role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> object:
        is_header_text = orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole
        if is_header_text and 0 <= section < len(self._columns):
            return self._columns[section][0]
        return None
