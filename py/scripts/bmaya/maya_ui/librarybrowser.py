"""The library browser's window: widgets bound to a LibrarySession (RigModules design/library-browser.md, D51).

One docked window for the active rig's pose and animation library: a search over the files, a list of them as List or
Details, what the selected file holds, Apply onto a scope, and Save into the user's own library. Every button is one
call on the session, which holds the state and does the work. The window only shows it and asks the questions a
session must not ask (replace, rename, delete). Qt only, no Maya (host.py docks it).
"""

from __future__ import annotations

import datetime
from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

import bmaya.core.asset.library
import bmaya.core.log
import bmaya.core.prompts
import bmaya.maya.librarybrowser
from bmaya.maya_ui import host, prompter, theme
from bmaya.maya_ui.widgets import ListModel, TagsEdit

LIBRARY = bmaya.core.asset.library
SESSION = bmaya.maya.librarybrowser

OBJECT_NAME = "bmayaLibraryBrowser"
KIND_TITLES = {LIBRARY.POSE: "Poses", LIBRARY.ANIMATION: "Animations"}
SCOPE_AUTO_TEXT = "Auto (selection, else rig)"
NAME, TAGS, SOURCE, TEMPLATE, AUTHOR, DATE, FRAMES = range(7)
LIST_COLUMNS = (NAME, SOURCE)   # List shows these, Details all of them
SORT_ROLE = QtCore.Qt.ItemDataRole.UserRole


def source_label(key: str) -> str:
    """The text of a source in the Source column and on its chip."""
    return key.capitalize()


def menu_action(menu: QtWidgets.QMenu, text: str) -> QtGui.QAction:
    """A new action of the menu. It is made here and parented to the menu, because the action addAction(text) makes was
    found deleted in a GUI Maya while the window still held it."""
    action = QtGui.QAction(text, menu)
    menu.addAction(action)
    return action


def _show_text(label: QtWidgets.QLabel, text: str) -> None:
    """Sets a label's text, and shows the label only while it has some, so an empty one takes no room."""
    label.setText(text)
    label.setVisible(bool(text))


def _modified(entry: LIBRARY.LibraryEntry) -> str:
    return datetime.datetime.fromtimestamp(entry.file.modified).strftime("%Y-%m-%d")


def _frames(entry: LIBRARY.LibraryEntry) -> str:
    return f"{entry.info.start_frame:g}-{entry.info.end_frame:g}" if entry.kind == LIBRARY.ANIMATION and not entry.info.error else ""


# header, the text of a column, and what a click on the header sorts by
COLUMNS = (
    ("Name", lambda entry: entry.name, lambda entry: entry.name.casefold()),
    ("Tags", lambda entry: ", ".join(entry.tags), lambda entry: ", ".join(entry.tags).casefold()),
    ("Source", lambda entry: source_label(entry.source), lambda entry: entry.source),
    ("Template", lambda entry: entry.meta("template"), lambda entry: entry.meta("template").casefold()),
    ("Author", lambda entry: entry.meta("author"), lambda entry: entry.meta("author").casefold()),
    ("Date", _modified, lambda entry: entry.file.modified),
    ("Frames", _frames, lambda entry: entry.info.start_frame),
)


class EntryModel(ListModel):
    """The list's rows: one entry each. The kind icon sits in the Name column only, and a click on a header sorts by
    the column's sort key, which a proxy reads through SORT_ROLE."""

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> object:
        if role == QtCore.Qt.ItemDataRole.DecorationRole and index.column() != NAME:
            return None
        if role == SORT_ROLE and index.isValid():
            return COLUMNS[index.column()][2](self.item(index.row()))
        return super().data(index, role)


class EntryTable(QtWidgets.QTableView):
    """The table of entries. A double click or Return asks for an apply, and nothing else does: a click, a hover or an
    arrow key only selects (section 7)."""

    apply_requested = QtCore.Signal()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.indexAt(event.position().toPoint()).isValid():
            self.apply_requested.emit()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter) and self.currentIndex().isValid():
            self.apply_requested.emit()
            return
        super().keyPressEvent(event)


class EditMetaDialog(QtWidgets.QDialog):
    """The tags and the description of one file, the two fields that can change after a save."""

    def __init__(self, name: str, tags: list[str], description: str, tags_in_use: list[str],
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Tags and Description - {name}")
        theme.apply(self)
        self.tags_edit = TagsEdit()
        self.tags_edit.set_tags_in_use(tags_in_use)
        self.tags_edit.set_tags(tags)
        self.description_edit = QtWidgets.QPlainTextEdit(description)
        self.description_edit.setFixedHeight(80)
        form = QtWidgets.QFormLayout(self)
        form.addRow("Tags", self.tags_edit)
        form.addRow("Description", self.description_edit)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def tags(self) -> list[str]:
        return self.tags_edit.tags()

    def description(self) -> str:
        return self.description_edit.toPlainText().strip()


class LibraryBrowser(QtWidgets.QWidget):
    """The window. Reads the session's state whenever its changed event emits, and calls its commands."""

    def __init__(self, session: SESSION.LibrarySession, parent: QtWidgets.QWidget | None = None,
                 asker: bmaya.core.prompts.Prompter | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Library Browser")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.session = session
        self.asker = asker or prompter.QtPrompter(host.parent_window)
        # A docked window is destroyed with its workspace control, often without a closeEvent. Its session then stops
        # following the tracker, or the next active rig change would call a deleted widget.
        self.destroyed.connect(session.close)
        self._syncing = False   # the window is filling its widgets from the session: that is not the user acting
        self._shown_before = False
        self._suggested = ""
        self._source_keys: list[str] = []
        self._mask_keys: list[tuple[str, str]] = []
        self._scope_values: list[str | None] = [None, SESSION.SCOPE_SELECTION, SESSION.SCOPE_RIG]
        self.source_buttons: dict[str, QtWidgets.QPushButton] = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(self._build_header())
        self.empty_label = QtWidgets.QLabel()
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)
        self.body = QtWidgets.QWidget()
        body = QtWidgets.QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        body.addLayout(self._build_search())
        body.addLayout(self._build_sources())
        body.addWidget(self._build_table(), 1)
        body.addLayout(self._build_details())
        body.addLayout(self._build_apply())
        body.addLayout(self._build_save())
        layout.addWidget(self.body, 1)
        self.status_label = QtWidgets.QLabel()
        self.status_label.setProperty("muted", True)
        self.status_error_label = QtWidgets.QLabel()
        self.status_error_label.setProperty("error", True)
        for label in (self.status_label, self.status_error_label):
            label.setWordWrap(True)
            label.hide()
            layout.addWidget(label)

        self.session.changed.connect(self.reload)
        self.reload()

    # ---- building -----------------------------------------------------------------------------------------

    def _build_header(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        self.rig_label = QtWidgets.QLabel()
        self.refresh_button = self._button("Refresh", self.session.refresh, "Read the rig and the library again", "rotate")
        row.addWidget(self.rig_label, 1)
        row.addWidget(self.refresh_button)
        return row

    def _build_search(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        self.kind_tabs = QtWidgets.QTabBar()
        self.kind_tabs.setExpanding(False)
        for kind in LIBRARY.KINDS:
            self.kind_tabs.addTab(KIND_TITLES[kind])
        self.kind_tabs.currentChanged.connect(self._on_kind_picked)
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText("Search name, tag, description. tag:fist template:Human")
        self.search_edit.textChanged.connect(self._on_query_edited)
        self.filter_button = QtWidgets.QPushButton("Filter")
        self.filter_button.setToolTip("Filter by a tag, template, region, status or category in use")
        self.filter_menu = QtWidgets.QMenu(self.filter_button)
        self.filter_menu.aboutToShow.connect(self.fill_filter_menu)
        self.filter_button.setMenu(self.filter_menu)
        row.addWidget(self.kind_tabs)
        row.addWidget(self.search_edit, 1)
        row.addWidget(self.filter_button)
        return row

    def _build_sources(self) -> QtWidgets.QHBoxLayout:
        self.sources_layout = QtWidgets.QHBoxLayout()
        self.sources_layout.addStretch(1)
        self.view_buttons: dict[str, QtWidgets.QPushButton] = {}
        group = QtWidgets.QButtonGroup(self)
        for name, tip in (("List", "Name and source"), ("Details", "Every column")):
            button = QtWidgets.QPushButton(name)
            button.setCheckable(True)
            button.setToolTip(tip)
            button.clicked.connect(lambda checked=False, name=name: self._show_columns(name == "Details"))
            group.addButton(button)
            self.sources_layout.addWidget(button)
            self.view_buttons[name] = button
        self.view_buttons["List"].setChecked(True)
        return self.sources_layout

    def _build_table(self) -> QtWidgets.QTableView:
        self.model = EntryModel(
            {QtCore.Qt.ItemDataRole.DecorationRole: self._icon, QtCore.Qt.ItemDataRole.ForegroundRole: self._colour,
             QtCore.Qt.ItemDataRole.ToolTipRole: self._tooltip},
            columns=[(header, text) for header, text, _sort in COLUMNS])
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(SORT_ROLE)
        self.table = EntryTable()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(NAME, QtCore.Qt.SortOrder.AscendingOrder)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.apply_requested.connect(self._apply)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._show_columns(False)
        return self.table

    def _build_details(self) -> QtWidgets.QVBoxLayout:
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(2)
        self.summary_label = QtWidgets.QLabel()
        self.error_label = QtWidgets.QLabel()
        self.error_label.setProperty("error", True)
        self.warning_label = QtWidgets.QLabel()
        self.warning_label.setProperty("warning", True)
        self.origin_label = QtWidgets.QLabel()
        self.origin_label.setProperty("muted", True)
        self.description_label = QtWidgets.QLabel()
        for label in (self.summary_label, self.error_label, self.warning_label, self.origin_label, self.description_label):
            label.setWordWrap(True)
            label.hide()
            column.addWidget(label)
        return column

    def _build_apply(self) -> QtWidgets.QVBoxLayout:
        self.scope_combo = QtWidgets.QComboBox()
        self.scope_combo.setToolTip("The controls Apply and Save act on")
        self.scope_combo.currentIndexChanged.connect(self._on_scope_picked)
        self.masks_button = QtWidgets.QPushButton("Masks")
        self.masks_button.setToolTip("Make a mask of the selected controls, or delete one of yours")
        masks_menu = QtWidgets.QMenu(self.masks_button)
        self.save_mask_action = menu_action(masks_menu, "Save Selection as Mask...")
        self.save_mask_action.triggered.connect(lambda checked=False: self.run(self._save_mask))
        self.delete_mask_action = menu_action(masks_menu, "Delete Mask")
        self.delete_mask_action.triggered.connect(lambda checked=False: self.run(self._delete_mask))
        self.masks_button.setMenu(masks_menu)
        self.mirror_box = QtWidgets.QCheckBox("Mirror")
        self.mirror_box.setToolTip("Put the Left side on the Right and the Right on the Left")
        self.start_label = QtWidgets.QLabel("Start at")
        self.start_edit = QtWidgets.QLineEdit()
        self.start_edit.setPlaceholderText("own start")
        self.start_edit.setValidator(QtGui.QDoubleValidator(self.start_edit))
        self.start_edit.setFixedWidth(70)
        self.now_button = self._button("Now", self._fill_current_frame, "Start at the current frame")
        self.apply_button = self._button("Apply", self._apply, "Load the selected file onto the scope", "")
        self.apply_button.setProperty("primary", True)
        scope_row = QtWidgets.QHBoxLayout()
        scope_row.addWidget(self.scope_combo, 1)
        scope_row.addWidget(self.masks_button)
        # Two rows: the scope, then what Apply does with it. One row is wider than the docked window for an animation.
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.mirror_box)
        row.addWidget(self.start_label)
        row.addWidget(self.start_edit)
        row.addWidget(self.now_button)
        row.addStretch(1)
        row.addWidget(self.apply_button)
        column = QtWidgets.QVBoxLayout()
        column.addLayout(scope_row)
        column.addLayout(row)
        return column

    def _build_save(self) -> QtWidgets.QVBoxLayout:
        column = QtWidgets.QVBoxLayout()
        row = QtWidgets.QHBoxLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        self.name_edit.returnPressed.connect(self._save)
        self.tags_edit = TagsEdit()
        self.tags_edit.setPlaceholderText("Tags, separated by commas")
        self.tags_edit.returnPressed.connect(self._save)
        self.save_button = self._button("Save", self._save, "Save the scope into your own library", "")
        row.addWidget(self.name_edit, 1)
        row.addWidget(self.tags_edit, 1)
        row.addWidget(self.save_button)
        self.range_label = QtWidgets.QLabel()
        self.range_label.setProperty("muted", True)
        column.addLayout(row)
        column.addWidget(self.range_label)
        return column

    def _button(self, text: str, command: Callable[[], object], tip: str, icon: str = "") -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        if icon:
            button.setIcon(theme.icon(icon))
        button.setToolTip(tip)
        button.clicked.connect(lambda checked=False: self.run(command))
        return button

    # ---- running a command --------------------------------------------------------------------------------

    def run(self, command: Callable[[], object]) -> bool:
        """Runs a session command. A problem the session names goes to the log, where every tool's errors go, and to
        the status line, and never reaches Qt. Returns whether it ran."""
        try:
            command()
        except (RuntimeError, ValueError) as error:
            bmaya.core.log.error(str(error))
            self.set_status(str(error), error=True)
            return False
        return True

    def set_status(self, text: str, error: bool = False) -> None:
        """Shows a result or a problem on the line at the bottom. Two labels, not one whose style is changed: a style
        is only read again by a polish, and widget.style() hands back a deleted object in a GUI Maya."""
        _show_text(self.status_error_label if error else self.status_label, text)
        _show_text(self.status_label if error else self.status_error_label, "")

    # ---- showing the session ------------------------------------------------------------------------------

    def reload(self) -> None:
        """Fills every widget from the session."""
        session = self.session
        self._syncing = True
        try:
            has_rig = session.rig_root is not None
            self.rig_label.setText(session.asset_id or "")
            self.empty_label.setText(session.reason)
            self.empty_label.setVisible(not has_rig)
            self.body.setEnabled(has_rig)
            self.kind_tabs.setCurrentIndex(LIBRARY.KINDS.index(session.kind))
            if self.search_edit.text() != session.query:
                self.search_edit.setText(session.query)
            self._reload_sources()
            self._reload_scope()
            if session.entries != self.model.items:
                self.model.set_items(session.entries)
            self._show_selection(session.selected)
            self._reload_details()
            self._reload_save(has_rig)
        finally:
            self._syncing = False

    def _reload_sources(self) -> None:
        keys = [source.key for source in self.session.sources]
        if keys != self._source_keys:
            for button in self.source_buttons.values():
                self.sources_layout.removeWidget(button)
                button.deleteLater()
            self.source_buttons = {}
            for position, key in enumerate(keys):
                button = QtWidgets.QPushButton(source_label(key))
                button.setCheckable(True)
                button.setToolTip(f"Show the {source_label(key)} library")
                button.clicked.connect(lambda checked=False, key=key: self._on_source_clicked(key))
                self.sources_layout.insertWidget(position, button)
                self.source_buttons[key] = button
            self._source_keys = keys
        for key, button in self.source_buttons.items():
            button.setChecked(self.session.source_enabled.get(key, True))

    def _reload_scope(self) -> None:
        masks = [(mask.name, mask.source) for mask in self.session.masks]
        if masks != self._mask_keys:
            self.scope_combo.clear()
            for text in (SCOPE_AUTO_TEXT, "Selection", "Whole rig"):
                self.scope_combo.addItem(text)
            self._scope_values = [None, SESSION.SCOPE_SELECTION, SESSION.SCOPE_RIG]
            for name, source in masks:
                suffix = {LIBRARY.TEAM: " (team)", LIBRARY.USER: " (mine)"}.get(source, "")
                self.scope_combo.addItem(f"Mask: {name}{suffix}")
                self._scope_values.append(name)
            self._mask_keys = masks
        scope = self.session.scope
        self.scope_combo.setCurrentIndex(self._scope_values.index(scope) if scope in self._scope_values else 0)
        mask = next((mask for mask in self.session.masks if mask.name == self.session.scope), None)
        self.delete_mask_action.setEnabled(mask is not None and mask.source == LIBRARY.USER)

    def _show_selection(self, entry: LIBRARY.LibraryEntry | None) -> None:
        """Selects the row of entry, found by path since a reset made new rows."""
        if self._selected_entry() == entry:
            return
        row = self.model.row_of(lambda item: item.path == entry.path) if entry is not None else -1
        selection = self.table.selectionModel()
        if row < 0:
            selection.clearSelection()
            return
        index = self.proxy.mapFromSource(self.model.index(row, NAME))
        selection.select(index, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect |
                         QtCore.QItemSelectionModel.SelectionFlag.Rows)
        selection.setCurrentIndex(index, QtCore.QItemSelectionModel.SelectionFlag.NoUpdate)
        self.table.scrollTo(index)

    def _selected_entry(self) -> LIBRARY.LibraryEntry | None:
        rows = self.table.selectionModel().selectedRows()
        return self.model.item(self.proxy.mapToSource(rows[0]).row()) if rows else None

    def _reload_details(self) -> None:
        entry = self.session.selected
        lines = self.session.details(entry) if entry is not None else []
        failed = entry is not None and bool(entry.info.error)
        _show_text(self.summary_label, "" if failed or not lines else lines[0])
        _show_text(self.error_label, "\n".join(lines) if failed else "")   # a file that can't be read is a problem
        _show_text(self.warning_label, "" if failed else "\n".join(lines[1:]))
        origin = []
        if entry is not None and not failed:
            for label, key in (("Template", "template"), ("Skeleton", "skeleton")):
                if entry.meta(key):
                    origin.append(f"{label} {entry.meta(key)}.")
            if entry.meta("author"):
                created = entry.meta("created")[:10]
                origin.append(f"By {entry.meta('author')}{', ' + created if created else ''}.")
        _show_text(self.origin_label, " ".join(origin))
        _show_text(self.description_label, entry.description if entry is not None else "")
        self.apply_button.setEnabled(entry is not None and not failed)

    def _reload_save(self, has_rig: bool) -> None:
        is_animation = self.session.kind == LIBRARY.ANIMATION
        for widget in (self.start_label, self.start_edit, self.now_button, self.range_label):
            widget.setVisible(is_animation)
        self.tags_edit.set_tags_in_use(self.session.facets()["tag"] if has_rig else [])
        suggestion = ""
        if has_rig:
            try:
                suggestion = self.session.suggest_name()
            except RuntimeError as error:   # a library folder that can't be read
                bmaya.core.log.warning(str(error))
        if self.name_edit.text() in ("", self._suggested):   # a name the animator typed is theirs, a suggestion is not
            self.name_edit.setText(suggestion)
        self._suggested = suggestion
        if has_rig and is_animation:
            start, end = self.session.playback_range()
            self.range_label.setText(f"Saves frames {start}-{end}, the playback range.")

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """A window that opens again reads the library again: files may have changed on disk. The first show doesn't,
        because the session read it when it was made."""
        super().showEvent(event)
        if self._shown_before:
            self.run(self.session.refresh)
        self._shown_before = True

    # ---- the rows -----------------------------------------------------------------------------------------

    @staticmethod
    def _icon(entry: LIBRARY.LibraryEntry) -> QtGui.QIcon:
        return theme.icon("key" if entry.kind == LIBRARY.ANIMATION else "pose")

    @staticmethod
    def _colour(entry: LIBRARY.LibraryEntry) -> QtGui.QColor | None:
        if entry.info.error:
            return QtGui.QColor(theme.DARK.error)
        return QtGui.QColor(theme.DARK.warning) if entry.info.unmatched_controls else None

    def _tooltip(self, entry: LIBRARY.LibraryEntry) -> str:
        lines = self.session.details(entry)
        return "\n".join(([entry.description] if entry.description and not entry.info.error else []) + lines)

    def _show_columns(self, details: bool) -> None:
        """List gives the name the room that is left. Details sizes it to its text and lets the table scroll."""
        for column in range(len(COLUMNS)):
            self.table.setColumnHidden(column, not details and column not in LIST_COLUMNS)
        mode = QtWidgets.QHeaderView.ResizeMode.ResizeToContents if details else QtWidgets.QHeaderView.ResizeMode.Stretch
        self.table.horizontalHeader().setSectionResizeMode(NAME, mode)

    # ---- what the user does -------------------------------------------------------------------------------

    def _on_kind_picked(self, index: int) -> None:
        if not self._syncing:
            self.run(lambda: self.session.set_kind(LIBRARY.KINDS[index]))

    def _on_query_edited(self, text: str) -> None:
        if not self._syncing:
            self.run(lambda: self.session.set_query(text))

    def _on_source_clicked(self, key: str) -> None:
        self.run(lambda: self.session.set_source_enabled(key, self.source_buttons[key].isChecked()))

    def _on_scope_picked(self, index: int) -> None:
        if not self._syncing and index >= 0:
            self.run(lambda: self.session.set_scope(self._scope_values[index]))

    def _on_selection_changed(self) -> None:
        if not self._syncing:
            self.run(lambda: self.session.select(self._selected_entry()))

    def fill_filter_menu(self) -> None:
        """One submenu per facet, listing the values in use. A pick adds the search term, a second takes it out."""
        self.filter_menu.clear()
        for field, values in self.session.facets().items():
            submenu = QtWidgets.QMenu(field.capitalize(), self.filter_menu)   # parented here: addMenu(str) hands PySide the ownership
            self.filter_menu.addMenu(submenu)
            submenu.setEnabled(bool(values))
            for value in values:
                action = menu_action(submenu, value)
                action.setCheckable(True)
                action.setChecked(LIBRARY.has_term(self.session.query, field, value))
                action.triggered.connect(lambda checked=False, field=field, value=value: self._toggle_term(field, value))

    def _toggle_term(self, field: str, value: str) -> None:
        self.search_edit.setText(LIBRARY.toggle_term(self.search_edit.text(), field, value))

    def _fill_current_frame(self) -> None:
        self.start_edit.setText(f"{self.session.current_frame():g}")

    def _start_frame(self) -> float | None:
        """The Start at field: None for an empty field, which means the animation's own start."""
        text = self.start_edit.text().strip()
        if not text or self.session.kind != LIBRARY.ANIMATION:
            return None
        try:
            return float(text)
        except ValueError:
            raise ValueError(f"Start at is a frame number, not {text!r}.") from None

    def _apply(self) -> None:
        entry = self.session.selected
        changed = self.session.apply(mirror=self.mirror_box.isChecked(), start_frame=self._start_frame())
        self.set_status(f"Applied {entry.name} to {len(changed)} controls.")

    def _save(self) -> None:
        session = self.session
        name = self.name_edit.text().strip()
        replace = False
        if session.name_taken(name):
            if not self.asker.confirm("Replace", f"You already have a {session.kind} called {name!r}. Replace it?", "Replace"):
                return
            replace = True
        session.save(name, tuple(self.tags_edit.tags()), replace=replace)
        self.tags_edit.clear()   # the next save is a different file: stale tags would be a surprise
        self.name_edit.setText(self._suggested)   # the save's reload kept the name, which the animator typed
        self.set_status(f"Saved {name}.")

    def _save_mask(self) -> None:
        name = self.asker.ask_text("Save Mask", "Name of the mask:")
        if name is None:
            return
        mask = self.session.mask_from_selection(name)
        self.session.save_mask(mask)
        self.session.set_scope(mask.name)
        self.set_status(f"Saved the mask {mask.name}.")

    def _delete_mask(self) -> None:
        name = self.session.scope
        if name is not None and self.asker.confirm("Delete Mask", f"Delete the mask {name!r}?", "Delete"):
            self.session.delete_mask(name)

    # ---- the context menu ---------------------------------------------------------------------------------

    def _on_context_menu(self, position: QtCore.QPoint) -> None:
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        entry = self.model.item(self.proxy.mapToSource(index).row())
        self.run(lambda: self.session.select(entry))
        menu = self.entry_menu(entry)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def entry_menu(self, entry: LIBRARY.LibraryEntry) -> QtWidgets.QMenu:
        """The menu of one file. What the user can't do to its source is disabled, not hidden, so it is clear why."""
        menu = QtWidgets.QMenu(self)
        writable = entry.file.writable
        actions = (
            ("Apply", True, self._apply),
            ("Copy to My Library", not writable, lambda: self.session.copy_to_user(entry)),
            ("Rename...", writable, lambda: self._rename(entry)),
            ("Edit Tags and Description...", writable, lambda: self._edit_meta(entry)),
            ("Delete", writable, lambda: self._delete(entry)),
        )
        for text, enabled, command in actions:
            action = menu_action(menu, text)
            action.setEnabled(enabled)
            action.triggered.connect(lambda checked=False, command=command: self.run(command))
        return menu

    def _rename(self, entry: LIBRARY.LibraryEntry) -> None:
        name = self.asker.ask_text("Rename", "New name:", entry.name)
        if name is not None and name != entry.name:
            self.session.rename(entry, name)

    def _edit_meta(self, entry: LIBRARY.LibraryEntry) -> None:
        dialog = EditMetaDialog(entry.name, entry.tags, entry.description, self.session.facets()["tag"], self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.session.set_meta(entry, tags=dialog.tags(), description=dialog.description())

    def _delete(self, entry: LIBRARY.LibraryEntry) -> None:
        if self.asker.confirm("Delete", f"Delete {entry.name!r}? A local version copy is kept.", "Delete"):
            self.session.delete(entry)


def show_window() -> QtWidgets.QWidget:
    """Opens the library browser, docked beside the Attribute Editor in a GUI Maya."""
    return host.show(LibraryBrowser(SESSION.LibrarySession(), parent=host.parent_window()),
                     object_name=OBJECT_NAME, dock=True)
