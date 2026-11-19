"""Widgets of the Asset Editor, each over a plain list or value so another window can use them (RigModules
design/asset-editor.md, D61): AssetPicker, FileStatusTable and OwnerCombo. Qt only, no Maya.

They hold no asset logic. The editor window binds them to an AssetEditorSession.
"""

from __future__ import annotations

import datetime

from PySide6 import QtCore, QtWidgets

from bmaya.maya_ui.widgets import ListModel

FILE, NAME, STATUS, VERSIONS, SAVE, LOAD = range(6)
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
    if not row.exists:
        return "Not saved"
    return datetime.datetime.fromtimestamp(row.modified).strftime("%Y-%m-%d %H:%M")


class FileStatusTable(QtWidgets.QTableView):
    """A table of FileRow, one per file, with a Save and a Load button in each row that has the command. A button is
    disabled when the row says it is blocked, and its tool tip says why. save_requested and load_requested emit the
    row's key. set_rows replaces the rows."""

    save_requested = QtCore.Signal(str)
    load_requested = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.row_model = ListModel(
            {QtCore.Qt.ItemDataRole.ToolTipRole: lambda row: row.path},
            columns=[(COLUMNS[FILE], lambda row: row.label),
                     (COLUMNS[NAME], lambda row: row.owner or ""),
                     (COLUMNS[STATUS], _status),
                     (COLUMNS[VERSIONS], lambda row: str(row.versions) if row.exists else ""),
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
        button = QtWidgets.QPushButton(name.capitalize())
        button.setEnabled(not blocked)
        button.setToolTip(blocked or ("Replaces the saved file. The old one is kept as a local version."
                                      if name == "save" and row.exists else f"{name.capitalize()} the {row.label.lower()}"))
        button.clicked.connect(lambda checked=False, key=row.key: signal.emit(key))
        self.setIndexWidget(self.row_model.index(number, column), button)
        self.buttons[(row.key, name)] = button
