"""The Registry Editor window: widgets bound to a RegistryEditSession, which holds the state and every editing rule.

A tool is an id, labels and one function call. The call is picked here: a module (typed, with a completer), a
function (a drop-down of the module's public functions) and its arguments (a SignatureForm, where only the
arguments that are ticked are saved).
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtCore, QtGui

import bmaya.maya.constants
from bmaya.core import log
from bmaya.core import tool_registry
from bmaya.core.tool_registry_edit import RegistryEditSession, STATUS_OK
from bmaya.maya_ui import host
from bmaya.maya_ui.qtbase import SimpleWindow
from bmaya.maya_ui.widgets import ERROR_STYLE, SignatureForm

OBJECT_NAME = "bmayaRegistryEditor"
ID_ROLE = QtCore.Qt.ItemDataRole.UserRole


class NewToolDialog(QtWidgets.QDialog):
    """Asks for a new tool's id, checked as it is typed, and its name."""

    def __init__(self, session: RegistryEditSession, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Tool")
        self._session = session

        layout = QtWidgets.QFormLayout(self)
        self.input_id = QtWidgets.QLineEdit()
        self.input_id.setPlaceholderText("area.topic.action, for example rigmodules.pose.flip")
        self.input_name = QtWidgets.QLineEdit()
        self.problem = QtWidgets.QLabel("")
        self.problem.setStyleSheet(ERROR_STYLE)
        layout.addRow("Id:", self.input_id)
        layout.addRow("Name:", self.input_name)
        layout.addRow(self.problem)
        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

        self.input_id.textChanged.connect(self._validate)
        self.input_name.textChanged.connect(self._validate)
        self._validate()

    def _validate(self) -> None:
        tool_id = self.input_id.text()
        message = self._session.id_problem(tool_id) if tool_id else ""
        self.problem.setText(message)
        valid = bool(tool_id) and not message and bool(self.input_name.text().strip())
        self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(valid)

    def values(self) -> tuple[str, str]:
        return self.input_id.text(), self.input_name.text().strip()


class ToolManagerWindow(SimpleWindow):
    """Widgets over a RegistryEditSession: they show its state, and each edit is a call on it. The window keeps no
    state of its own, except that it ignores its own widgets' signals while it fills them from the session."""

    def __init__(self, session: RegistryEditSession, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent=parent, title="Master Tool Registry Manager")

        self.session = session
        self.argument_form = SignatureForm()
        self._filling = False

        self.resize(950, 750)
        self._build_menu_bar()
        self._build_ui_layout()
        self._connect_signals()
        self._show_tools()

    # --- UI --------------------------------------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        """Constructs the window's main pull-down menus."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        self.action_open = file_menu.addAction("Open Registry...")
        self.action_save = file_menu.addAction("Save Registry")
        self.action_save_as = file_menu.addAction("Save Registry As...")
        file_menu.addSeparator()
        self.action_exit = file_menu.addAction("Exit")

    def _build_ui_layout(self) -> None:
        """Generates the main interactive interface widgets and split layouts."""
        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.mainLayout.addWidget(main_splitter)

        # Left Column Layout (Browsing & Filtering)
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search tools...")
        left_layout.addWidget(self.search_input)

        self.tool_list = QtWidgets.QListWidget()
        left_layout.addWidget(self.tool_list)

        left_btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add_tool = QtWidgets.QPushButton("+ New Tool")
        self.btn_delete_tool = QtWidgets.QPushButton("- Delete")
        left_btn_layout.addWidget(self.btn_add_tool)
        left_btn_layout.addWidget(self.btn_delete_tool)
        left_layout.addLayout(left_btn_layout)

        # Right Column Layout (Editing Fields & Execution Context)
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        form_group = QtWidgets.QGroupBox("Tool Attributes")
        form_layout = QtWidgets.QFormLayout(form_group)

        self.input_id = QtWidgets.QLineEdit()
        self.input_id.setReadOnly(True)  # a rename is a hand edit of the registry and every layout
        self.input_name = QtWidgets.QLineEdit()
        self.input_short_name = QtWidgets.QLineEdit()
        self.input_icon = QtWidgets.QLineEdit()
        self.check_enabled = QtWidgets.QCheckBox("Active in menus")

        form_layout.addRow("Id:", self.input_id)
        form_layout.addRow("Full Name:", self.input_name)
        form_layout.addRow("Short Name:", self.input_short_name)
        form_layout.addRow("Icon Path/Name:", self.input_icon)
        form_layout.addRow("Status:", self.check_enabled)
        right_layout.addWidget(form_group)

        call_group = QtWidgets.QGroupBox("Call")
        call_layout = QtWidgets.QVBoxLayout(call_group)
        call_form = QtWidgets.QFormLayout()
        self.input_module = QtWidgets.QLineEdit()
        self.input_module.setPlaceholderText("bmaya.maya.posetools")
        self.module_completer = QtWidgets.QCompleter([], self)
        self.module_completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.module_completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.input_module.setCompleter(self.module_completer)
        self.combo_function = QtWidgets.QComboBox()
        self.combo_function.setEditable(False)
        self.combo_function.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.label_doc = QtWidgets.QLabel("")
        self.label_doc.setWordWrap(True)
        call_form.addRow("Module:", self.input_module)
        call_form.addRow("Function:", self.combo_function)
        call_form.addRow("", self.label_doc)
        call_layout.addLayout(call_form)

        self.argument_scroll = QtWidgets.QScrollArea()
        self.argument_scroll.setWidgetResizable(True)
        self.argument_scroll.setWidget(self.argument_form)
        call_layout.addWidget(self.argument_scroll)

        self.label_status = QtWidgets.QLabel("")
        self.label_status.setWordWrap(True)
        call_layout.addWidget(self.label_status)

        self.btn_execute = QtWidgets.QPushButton("Run")
        self.btn_execute.setMinimumHeight(30)
        call_layout.addWidget(self.btn_execute)
        right_layout.addWidget(call_group)

        # Assemble foundational layout panes
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([300, 650])

    def _connect_signals(self) -> None:
        """Widgets call the session, and the session's events call the window."""
        self.action_open.triggered.connect(self._on_open_registry)
        self.action_save.triggered.connect(self._on_save_registry)
        self.action_save_as.triggered.connect(self._on_save_registry_as)
        self.action_exit.triggered.connect(self.close)

        self.tool_list.currentItemChanged.connect(self._on_list_item_changed)
        self.search_input.textChanged.connect(self._filter_list)
        self.btn_add_tool.clicked.connect(self._on_add_new_tool)
        self.btn_delete_tool.clicked.connect(self._on_delete_selected_tool)
        self.btn_execute.clicked.connect(self._on_execute_payload)

        self.input_name.textChanged.connect(lambda text: self._edit_field("name", text))
        self.input_short_name.textChanged.connect(lambda text: self._edit_field("short_name", text))
        self.input_icon.textChanged.connect(lambda text: self._edit_field("icon", text))
        self.check_enabled.toggled.connect(lambda checked: self._edit_field("enabled", checked))
        self.input_module.editingFinished.connect(self._on_module_changed)
        self.input_module.textEdited.connect(self._on_module_typing)
        self.combo_function.currentIndexChanged.connect(self._on_function_changed)

        # The session holds these listeners weakly, which is right for a window that can close
        self.session.tools_changed.connect(self._show_tools)
        self.session.selection_changed.connect(self._show_selection)
        self.session.changed.connect(self._show_state)

    # --- showing the session ---------------------------------------------------------------------------------

    def _show_tools(self) -> None:
        """Rebuilds the tool list from the session."""
        self._filling = True
        self.tool_list.clear()
        for tool_id, tool in self.session.registry.tools.items():
            item = QtWidgets.QListWidgetItem(tool.name)
            item.setData(ID_ROLE, tool_id)
            item.setToolTip(tool_id)
            self.tool_list.addItem(item)
        self._filling = False
        self._filter_list(self.search_input.text())

    def _filter_list(self, text: str) -> None:
        shown = set(self.session.search(text))
        for i in range(self.tool_list.count()):
            item = self.tool_list.item(i)
            item.setHidden(item.data(ID_ROLE) not in shown)

    def _list_item(self, tool_id: str | None) -> QtWidgets.QListWidgetItem | None:
        for i in range(self.tool_list.count()):
            if self.tool_list.item(i).data(ID_ROLE) == tool_id:
                return self.tool_list.item(i)
        return None

    def _show_selection(self) -> None:
        """Fills every widget from the picked tool, or clears them when there is none."""
        tool = self.session.tool
        self._filling = True
        self.tool_list.setCurrentItem(self._list_item(self.session.active_tool_id))
        self.input_id.setText(tool.id if tool else "")
        self.input_name.setText(tool.name if tool else "")
        self.input_short_name.setText(tool.short_name if tool else "")
        self.input_icon.setText(tool.icon or "" if tool else "")
        self.check_enabled.setChecked(tool.enabled if tool else False)
        self.input_module.setText(tool.call.module if tool else "")
        self._fill_functions(tool.call.function if tool else "")
        self._show_arguments()
        for widget in (self.input_name, self.input_short_name, self.input_icon, self.check_enabled, self.input_module,
                       self.combo_function, self.argument_scroll, self.btn_delete_tool):
            widget.setEnabled(tool is not None)
        self._filling = False
        self._show_state()

    def _show_state(self) -> None:
        """The status line and Run, which wait for a status of OK, and the picked tool's name in the list."""
        status = self.session.status()
        ok = status == STATUS_OK
        self.label_status.setText(status)
        self.label_status.setStyleSheet("" if ok else ERROR_STYLE)
        self.btn_execute.setEnabled(ok)
        tool = self.session.tool
        item = self._list_item(tool.id) if tool else None
        if item is not None and item.text() != tool.name:
            item.setText(tool.name)

    def _fill_functions(self, current: str) -> None:
        """Fills the function drop-down from the module field, keeping the saved function even when it isn't
        listed."""
        self.combo_function.blockSignals(True)
        self.combo_function.clear()
        names = self.session.function_names(self.input_module.text(), current)
        self.combo_function.addItems(names)
        self.combo_function.setCurrentIndex(names.index(current) if current in names else -1)
        self.combo_function.blockSignals(False)
        # AdjustToContents sizes the drop-down to the longest function name, so its minimum follows the module
        self.combo_function.setMinimumWidth(0)
        self.combo_function.setMinimumWidth(self.combo_function.sizeHint().width())

    def _show_arguments(self) -> None:
        """Builds the argument form for the picked tool's function and saved kwargs."""
        tool = self.session.tool
        form = SignatureForm(self.session.function(), tool.call.kwargs if tool else {})
        form.changed.connect(self._on_arguments_edited)
        self.argument_form = form
        self.argument_scroll.setWidget(form)
        self.label_doc.setText(self.session.doc())

    # --- editing, through the session ------------------------------------------------------------------------

    def _on_list_item_changed(self, current: QtWidgets.QListWidgetItem | None, _previous) -> None:
        if not self._filling and current is not None:
            self.session.select(current.data(ID_ROLE))

    def _edit_field(self, name: str, value: object) -> None:
        if not self._filling:
            self.session.set_field(name, value)

    def _on_module_typing(self, _text: str) -> None:
        """The completer lists modules, found on first use."""
        if self.module_completer.model().rowCount() == 0:
            self.module_completer.setModel(QtCore.QStringListModel(self.session.module_names(), self.module_completer))

    def _on_module_changed(self) -> None:
        """A new module has other functions, so the call starts again with none picked."""
        if self._filling or self.session.tool is None:
            return
        self.session.set_call(self.input_module.text(), "")
        self._filling = True
        self._fill_functions("")
        self._show_arguments()
        self._filling = False

    def _on_function_changed(self, *_args) -> None:
        if self._filling or self.session.tool is None:
            return
        self.session.set_call(self.input_module.text(), self.combo_function.currentText())
        self._show_arguments()

    def _on_arguments_edited(self) -> None:
        try:
            kwargs = self.argument_form.kwargs()
        except ValueError as err:
            self.session.report_input_problem(str(err))
            return
        self.session.set_kwargs(kwargs)

    def _on_add_new_tool(self) -> None:
        """Adds a tool with an id and a name. Its call is empty, and Save refuses until one is picked."""
        dialog = NewToolDialog(self.session, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.session.add_tool(*dialog.values())

    def _on_delete_selected_tool(self) -> None:
        tool = self.session.tool
        if tool is None:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to remove '{tool.name}' from registration entries?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self.session.delete_tool()

    def _on_execute_payload(self) -> None:
        """Runs the tool as it is being edited, the way a menu item does."""
        tool = self.session.tool
        if tool is None:
            return
        log.info(f"Running {tool.id} from the registry editor")
        try:
            self.session.run()
        except Exception as err:
            QtWidgets.QMessageBox.warning(self, "Run Failed", f"{tool.id}: {err}")

    # --- files -----------------------------------------------------------------------------------------------

    def _confirm_discard(self) -> bool:
        """True when there are no unsaved edits, or the user accepts losing them."""
        if not self.session.dirty:
            return True
        answer = QtWidgets.QMessageBox.question(
            self,
            "Unsaved Edits",
            "This registry has unsaved edits. Discard them?",
            QtWidgets.QMessageBox.StandardButton.Discard | QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        return answer == QtWidgets.QMessageBox.StandardButton.Discard

    def _on_open_registry(self) -> None:
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Tool Registry File", bmaya.maya.constants.TOOL_REGISTRY_PATH, "JSON Files (*.json)"
        )
        if filepath and self._confirm_discard():
            self._load_registry(filepath)

    def _load_registry(self, filepath: str) -> None:
        """Replaces the registry with a file's. A file that fails its check is refused with every problem."""
        try:
            self.session.load(filepath)
        except (FileNotFoundError, tool_registry.ToolDataError) as err:
            QtWidgets.QMessageBox.warning(self, "Load Error", str(err))

    def _on_save_registry(self) -> None:
        """Saves to the file the registry came from, refusing with the full report when a check fails."""
        if not self.session.path:
            self._on_save_registry_as()
        else:
            self._save(None)

    def _on_save_registry_as(self) -> None:
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Master Tool Registry As", "", "JSON Files (*.json)"
        )
        if filepath:
            self._save(filepath)

    def _save(self, path: str | None) -> None:
        try:
            self.session.save(path)
        except tool_registry.ToolDataError as err:
            QtWidgets.QMessageBox.critical(self, "Save Refused", str(err))
        except OSError as err:
            QtWidgets.QMessageBox.critical(self, "Save Error", str(err))
        else:
            log.info(f"Successfully saved master tools file system to: {self.session.path}")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._confirm_discard():
            super().closeEvent(event)
        else:
            event.ignore()


def master_session() -> RegistryEditSession:
    """A session on the master registry, checked against every menu layout. A registry that fails its check is
    reported, and the session is empty."""
    paths = (bmaya.maya.constants.TOOL_REGISTRY_PATH, list(bmaya.maya.constants.menu_layout_paths().values()))
    try:
        return RegistryEditSession.open(paths[0], *paths)
    except (FileNotFoundError, tool_registry.ToolDataError) as err:
        QtWidgets.QMessageBox.warning(host.parent_window(), "Load Error", str(err))
        return RegistryEditSession(master_path=paths[0], layout_paths=paths[1])


def show_window() -> QtWidgets.QWidget:
    """Opens the Registry Editor."""
    return host.show(ToolManagerWindow(master_session(), parent=host.parent_window()), object_name=OBJECT_NAME)
