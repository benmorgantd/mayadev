"""Widgets of the Asset Editor, each over a plain list or value so another window can use them (RigModules
design/asset-editor.md, D61): AssetPicker, FileStatusTable, OwnerCombo and MixedFieldForm. Qt only, no Maya.

They hold no asset logic. The editor window binds them to an AssetEditorSession.
"""

from __future__ import annotations

import datetime

from PySide6 import QtCore, QtGui, QtWidgets

from bmaya.core.fieldset import FieldSpec, FieldState
from bmaya.maya_ui import theme
from bmaya.maya_ui.widgets import ListModel, menu_action

FILE, NAME, STATUS, VERSIONS, SAVE, LOAD = range(6)
ICON_SIZE = 32   # the Save and Load buttons show only an icon, so it fills the button
COLUMNS = ("File", "Name", "Status", "Versions", "", "")


class AssetPicker(QtWidgets.QComboBox):
    """A searchable list of asset ids: type to narrow it, pick one or press Return on a typed id. asset_picked emits the
    id the user chose, never one set from code. An id that is not in the list can be typed, so an asset that is not
    made yet can be named."""

    asset_picked = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(24)
        self.lineEdit().setPlaceholderText("Asset id: game\\project\\type\\name")
        completer = self.completer()
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.activated.connect(self._on_activated)
        self.lineEdit().returnPressed.connect(self._on_return)

    def set_ids(self, ids: list[str], current: str | None) -> None:
        """Fills the list and shows current (or nothing) without emitting asset_picked."""
        self.blockSignals(True)
        self.clear()
        self.addItems(ids)
        self.set_current(current)
        self.blockSignals(False)

    def set_current(self, asset_id: str | None) -> None:
        self.blockSignals(True)
        index = self.findText(asset_id) if asset_id else -1
        self.setCurrentIndex(index)
        self.setEditText(asset_id or "")
        self.blockSignals(False)

    def _on_activated(self, index: int) -> None:
        self.asset_picked.emit(self.itemText(index))

    def _on_return(self) -> None:
        text = self.currentText().strip()
        if text:
            self.asset_picked.emit(text)


class OwnerCombo(QtWidgets.QComboBox):
    """The skeletons, rigs or looks of an asset to choose from. owner_picked emits the name the user chose. With none, it
    shows the text given to set_names and is disabled."""

    owner_picked = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.activated.connect(lambda index: self.owner_picked.emit(self.itemText(index)))

    def set_names(self, names: list[str], current: str | None, empty_text: str) -> None:
        self.blockSignals(True)
        self.clear()
        self.addItems(names)
        if names:
            self.setCurrentIndex(max(0, self.findText(current)) if current else 0)
        else:
            self.addItem(empty_text)
        self.setEnabled(bool(names))
        self.blockSignals(False)


def _status(row) -> str:
    if row.opens_folder:
        files = "No folder" if row.file_count is None else f"{row.file_count} file" + ("" if row.file_count == 1 else "s")
        return f"{files}, {row.note}" if row.note else files
    if not row.exists:
        return "Not saved"
    return datetime.datetime.fromtimestamp(row.modified).strftime("%Y-%m-%d %H:%M")


class FileStatusTable(QtWidgets.QTableView):
    """A table of FileRow, one per file, with a Save and a Load button in each row that has the command. A button is
    disabled when the row says it is blocked, and its tool tip says why. Right-clicking a row (its Versions cell, say)
    offers Restore Version... when it has local versions, and Load by Name when its file type has it.
    save_requested, load_requested, load_by_name_requested and restore_requested emit the row's key. set_rows replaces
    the rows."""

    save_requested = QtCore.Signal(str)
    load_requested = QtCore.Signal(str)
    load_by_name_requested = QtCore.Signal(str)
    restore_requested = QtCore.Signal(str)
    open_requested = QtCore.Signal(str)   # a folder row's Open Folder menu item
    import_requested = QtCore.Signal(str)   # a folder row's Import Textures menu item

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.row_model = ListModel(
            {QtCore.Qt.ItemDataRole.ToolTipRole: lambda row: row.path},
            columns=[(COLUMNS[FILE], lambda row: row.label),
                     (COLUMNS[NAME], lambda row: row.owner or ""),
                     (COLUMNS[STATUS], _status),
                     (COLUMNS[VERSIONS], lambda row: str(row.versions) if row.versions else ""),
                     (COLUMNS[SAVE], lambda row: ""),
                     (COLUMNS[LOAD], lambda row: "")],
            parent=self)
        self.setModel(self.row_model)
        self.buttons: dict[tuple[str, str], QtWidgets.QPushButton] = {}
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(STATUS, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.setShowGrid(False)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def row_menu(self, key: str) -> QtWidgets.QMenu | None:
        """A row's right-click menu: Open Folder for a row with a folder the artist fills, Restore Version... when it
        has local versions, and Load by Name (off, with the reason as its tool tip, when Load is blocked) when its file
        type has it. None when it has none."""
        row = next((row for row in self.row_model.items if row.key == key), None)
        if row is None or not (row.versions or row.loads_by_name or row.opens_folder or row.imports_images):
            return None
        menu = QtWidgets.QMenu(self)
        menu.setToolTipsVisible(True)
        if row.imports_images:
            action = menu_action(menu, "Import Textures...")
            action.setEnabled(not row.save_blocked)
            action.setToolTip(row.save_blocked or "Select the meshes that wear a material, then name it and pick its "
                                                  "images. They are copied in and renamed "
                                                  "<asset>_<look>_<material>_<kind>.")
            action.triggered.connect(lambda checked=False: self.import_requested.emit(key))
        if row.opens_folder:
            action = menu_action(menu, "Open Folder")
            action.setEnabled(not row.open_blocked)
            action.setToolTip(row.open_blocked or "Make the folder if it is missing and show it. Copy the images in "
                                                  "by hand.")
            action.triggered.connect(lambda checked=False: self.open_requested.emit(key))
        if row.versions:
            action = menu_action(menu, "Restore Version...")
            action.setToolTip("Copies a local version over the file. The file it replaces is kept as a new version.")
            action.triggered.connect(lambda checked=False: self.restore_requested.emit(key))
        if row.loads_by_name:
            action = menu_action(menu, "Load by Name")
            action.setEnabled(not row.load_blocked)
            action.setToolTip(row.load_blocked or "Matches each file to the mesh with its name and gives the mesh the "
                                                  "file's meshId. Save the model afterwards.")
            action.triggered.connect(lambda checked=False: self.load_by_name_requested.emit(key))
        return menu

    def _on_context_menu(self, position: QtCore.QPoint) -> None:
        index = self.indexAt(position)
        if not index.isValid():
            return
        menu = self.row_menu(self.row_model.item(index.row()).key)
        if menu is not None:
            menu.exec(self.viewport().mapToGlobal(position))

    def set_rows(self, rows: list) -> None:
        self.row_model.set_items(rows)
        self.buttons = {}
        for number, row in enumerate(rows):
            self._add_button(number, row, "save", SAVE, row.saves, row.save_blocked, self.save_requested)
            self._add_button(number, row, "load", LOAD, row.loads, row.load_blocked, self.load_requested)
        self.resizeRowsToContents()

    def _add_button(self, number: int, row, name: str, column: int, has: bool, blocked: str,
                    signal: QtCore.SignalInstance) -> None:
        if not has:
            return
        button = QtWidgets.QPushButton()
        button.setIcon(theme.sized_icon(name, ICON_SIZE))
        button.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))
        button.setAccessibleName(name.capitalize())
        button.setEnabled(not blocked)
        button.setToolTip(blocked or ("Replaces the saved file. The old one is kept as a local version."
                                      if name == "save" and row.exists else f"{name.capitalize()} the {row.label.lower()}"))
        button.clicked.connect(lambda checked=False, key=row.key: signal.emit(key))
        self.setIndexWidget(self.row_model.index(number, column), button)
        self.buttons[(row.key, name)] = button


MIXED_TEXT = "Mixed"
PLACEHOLDER = "placeholder"   # the item data of a choice's Mixed or blank row


class MixedFieldForm(QtWidgets.QWidget):
    """A form for fields edited across several objects (bmaya.core.fieldset). set_states shows each field's value over
    the selection, and a field the objects disagree on says Mixed. field_edited emits (name, value) when the user
    changes a field, never when set_states does. A choice is a drop-down, text an editable drop-down of suggestions, a
    bool a check box (partly checked when mixed), a float a line edit. values() reads what is on screen: None for a
    field that is blank or mixed."""

    field_edited = QtCore.Signal(str, object)

    def __init__(self, specs: tuple[FieldSpec, ...], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.specs = {spec.name: spec for spec in specs}
        self.editors: dict[str, QtWidgets.QWidget] = {}
        self._shown: dict[str, object] = {}   # the value each field was last set to, to tell an edit from a refill
        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for spec in specs:
            editor = self._make_editor(spec)
            editor.setToolTip(spec.tip)
            self.editors[spec.name] = editor
            layout.addRow(spec.label, editor)

    # ---- building --------------------------------------------------------------------------

    def _make_editor(self, spec: FieldSpec) -> QtWidgets.QWidget:
        name = spec.name
        if spec.kind == "choice":
            combo = QtWidgets.QComboBox()
            combo.addItems(spec.options)
            combo.activated.connect(lambda index, name=name, combo=combo: self._emit_choice(name, combo))
            return combo
        if spec.kind == "text":
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
            combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
            combo.addItems(spec.options)
            combo.lineEdit().setPlaceholderText(MIXED_TEXT)
            combo.activated.connect(lambda index, name=name, combo=combo: self._emit_text(name, combo))
            combo.lineEdit().editingFinished.connect(lambda name=name, combo=combo: self._emit_text(name, combo))
            return combo
        if spec.kind == "bool":
            box = QtWidgets.QCheckBox()
            box.clicked.connect(lambda checked=False, name=name, box=box: self._emit_bool(name, box))
            return box
        edit = QtWidgets.QLineEdit()
        edit.setPlaceholderText(MIXED_TEXT)
        edit.setValidator(QtGui.QDoubleValidator(edit))
        edit.editingFinished.connect(lambda name=name, edit=edit: self._emit_float(name, edit))
        return edit

    def _emit_bool(self, name: str, box: QtWidgets.QCheckBox) -> None:
        """A click on a mixed box makes the value True for every object. A click on any other flips it."""
        if box.property("mixed"):
            box.setProperty("mixed", False)
            box.setCheckState(QtCore.Qt.CheckState.Checked)
        self.field_edited.emit(name, box.isChecked())

    def _emit_choice(self, name: str, combo: QtWidgets.QComboBox) -> None:
        text = combo.currentText()
        if text and text != MIXED_TEXT:
            self.field_edited.emit(name, text)

    def _emit_text(self, name: str, combo: QtWidgets.QComboBox) -> None:
        text = combo.currentText().strip()
        if text and text != self._shown.get(name):
            self.field_edited.emit(name, text)

    def _emit_float(self, name: str, edit: QtWidgets.QLineEdit) -> None:
        if edit.isModified() and edit.text().strip():
            edit.setModified(False)
            try:
                self.field_edited.emit(name, float(edit.text()))
            except ValueError:
                pass

    # ---- showing and reading ---------------------------------------------------------------

    def set_options(self, name: str, options: list[str]) -> None:
        """Replaces the suggestions of a text field, or the choices of a choice field. A choice field shows nothing
        until set_state gives it a value again."""
        combo = self.editors[name]
        text = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(options)
        if self.specs[name].kind == "text":
            combo.setEditText(text)
        combo.blockSignals(False)

    def set_states(self, states: dict[str, FieldState]) -> None:
        """Shows the state of each named field. A field with no state is blank."""
        self._shown = {}
        for name, spec in self.specs.items():
            self.set_state(name, states.get(name, FieldState()))

    def set_state(self, name: str, state: FieldState) -> None:
        spec, editor = self.specs[name], self.editors[name]
        editor.blockSignals(True)
        shown = None if state.mixed else state.value
        self._shown[name] = shown
        if spec.kind == "choice":
            for index in reversed(range(editor.count())):
                if editor.itemData(index) == PLACEHOLDER:   # the Mixed or blank row an earlier state put in
                    editor.removeItem(index)
            if shown is None:
                editor.insertItem(0, MIXED_TEXT if state.mixed else "", PLACEHOLDER)
                editor.setCurrentIndex(0)
            else:
                editor.setCurrentIndex(editor.findText(str(shown)))
        elif spec.kind == "text":
            editor.setEditText("" if shown is None else str(shown))
        elif spec.kind == "bool":
            editor.setProperty("mixed", state.mixed)
            editor.setCheckState(QtCore.Qt.CheckState.PartiallyChecked if state.mixed else
                                 (QtCore.Qt.CheckState.Checked if shown else QtCore.Qt.CheckState.Unchecked))
        else:
            editor.setText("" if shown is None else f"{shown:.6g}")
            editor.setModified(False)
        editor.blockSignals(False)

    def values(self) -> dict[str, object]:
        """What the form shows, by field name. None for a blank or mixed field."""
        out: dict[str, object] = {}
        for name, spec in self.specs.items():
            editor = self.editors[name]
            if spec.kind == "choice":
                text = editor.currentText()
                out[name] = text if text and text != MIXED_TEXT else None
            elif spec.kind == "text":
                out[name] = editor.currentText().strip() or None
            elif spec.kind == "bool":
                out[name] = None if editor.checkState() == QtCore.Qt.CheckState.PartiallyChecked else editor.isChecked()
            else:
                out[name] = float(editor.text()) if editor.text().strip() else None
        return out
