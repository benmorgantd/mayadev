"""Tool management interface for the master tools registry.

A tool is an id, labels and one function call. The call is picked here: a module (typed, with a completer), a
function (a drop-down of the module's public functions) and its arguments (a form built from the function's
signature, where only the arguments that are ticked are saved).
"""

from __future__ import annotations

import enum
import importlib
import importlib.util
import inspect
import json
import os
import types
import typing

from PySide6 import QtWidgets, QtCore, QtGui

from bmaya.core import log
from bmaya.core import tool_registry
from bmaya.core.tool_registry import Registry, Tool, ToolCall
import bmaya.maya.constants
import bmaya.maya_ui.tool_views.tool_menu
import bmaya.maya_ui.widgets
from bmaya.maya_ui.qtbase import SimpleWindow, get_maya_main_window

PACKAGES = ("bmaya", "rigmodules")
STATUS_OK = "OK"


def list_modules() -> list[str]:
    """Every module under the tool packages, for the module completer. Reads the folders and imports nothing:
    pkgutil skips folders without an __init__.py, and bmaya and bmaya.maya are namespace packages."""
    names: list[str] = []
    for package in PACKAGES:
        spec = importlib.util.find_spec(package)
        if spec is None or not spec.submodule_search_locations:
            continue
        names.append(package)
        for location in spec.submodule_search_locations:
            for folder, folders, files in os.walk(location):
                folders[:] = [f for f in folders if not f.startswith(("_", "."))]
                relative = os.path.relpath(folder, location)
                prefix = package if relative == "." else f"{package}.{relative.replace(os.sep, '.')}"
                if relative != ".":
                    names.append(prefix)
                names += [f"{prefix}.{f[:-3]}" for f in files if f.endswith(".py") and f != "__init__.py"]
    return sorted(set(names))


def list_functions(module: types.ModuleType) -> list[str]:
    """The public functions defined in a module, in the order they are written."""
    functions = [
        (function.__code__.co_firstlineno, name)
        for name, function in inspect.getmembers(module, inspect.isfunction)
        if function.__module__ == module.__name__ and not name.startswith("_")
    ]
    return [name for _, name in sorted(functions)]


class ArgumentRow(QtCore.QObject):
    """One parameter: an editor chosen by annotation and a Set check box. An unset row shows the default greyed and
    is not saved."""

    changed = QtCore.Signal()

    def __init__(self, name: str, parameter: inspect.Parameter, hint: object, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.has_default = parameter.default is not inspect.Parameter.empty
        self.default = None if not self.has_default else parameter.default
        self.editor = bmaya.maya_ui.widgets.FieldEditor(hint, self)
        self.editor.changed.connect(self.changed)
        self.widget = self.editor.widget
        self.set_check = QtWidgets.QCheckBox("Set")
        self.set_check.setChecked(not self.has_default)
        self.set_check.setEnabled(self.has_default)
        self.set_check.toggled.connect(self._on_set_toggled)
        self.editor.show_value(self.default)
        self._on_set_toggled(self.set_check.isChecked())

    def _on_set_toggled(self, checked: bool) -> None:
        self.widget.setEnabled(checked)
        self.changed.emit()

    def load(self, value: object) -> None:
        """Shows a saved kwarg: the row is set to it."""
        self.set_check.setChecked(True)
        self.editor.show_value(value)

    @property
    def is_set(self) -> bool:
        return self.set_check.isChecked()

    def value(self) -> object:
        """The editor's value as the registry's JSON keeps it: an Enum member's value. Raises ValueError for JSON
        text that isn't JSON."""
        try:
            value = self.editor.value()
        except ValueError as err:
            raise ValueError(f"argument '{self.name}' is {err}") from None
        return value.value if isinstance(value, enum.Enum) else value


class ArgumentForm(QtWidgets.QWidget):
    """The arguments of the picked function, as one row per parameter."""

    changed = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QtWidgets.QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._rows: list[ArgumentRow] = []
        self._stale: dict[str, object] = {}

    def clear(self) -> None:
        self._rows = []
        self._stale = {}
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def set_function(self, function: typing.Callable | None, kwargs: dict[str, object]) -> None:
        """Builds the rows for a function and shows the saved kwargs. A kwarg the function no longer has gets a red
        row with a Remove button."""
        self.clear()
        parameters = {}
        hints: dict[str, object] = {}
        if function is not None:
            try:
                parameters = dict(inspect.signature(function).parameters)
            except (TypeError, ValueError):
                parameters = {}
            try:
                hints = typing.get_type_hints(function)
            except Exception:
                hints = {}

        row_index = 0
        for name, parameter in parameters.items():
            if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY):
                continue
            row = ArgumentRow(name, parameter, hints.get(name), self)
            row.changed.connect(self.changed)
            if name in kwargs:
                row.load(kwargs[name])
            self._rows.append(row)
            default = "" if parameter.default is inspect.Parameter.empty else f"  (default {parameter.default!r})"
            label = QtWidgets.QLabel(f"{name}{default}")
            self._layout.addWidget(label, row_index, 0)
            self._layout.addWidget(row.widget, row_index, 1)
            self._layout.addWidget(row.set_check, row_index, 2)
            row_index += 1

        for name, value in kwargs.items():
            if name not in parameters:
                self._add_stale_row(row_index, name, value)
                row_index += 1

    def _add_stale_row(self, row_index: int, name: str, value: object) -> None:
        self._stale[name] = value
        label = QtWidgets.QLabel(f"{name} = {json.dumps(value)}  (not a parameter any more)")
        label.setStyleSheet("color: #e05555;")
        remove = QtWidgets.QPushButton("Remove")
        remove.clicked.connect(lambda: self._remove_stale(name, label, remove))
        self._layout.addWidget(label, row_index, 0, 1, 2)
        self._layout.addWidget(remove, row_index, 2)

    def _remove_stale(self, name: str, label: QtWidgets.QWidget, button: QtWidgets.QWidget) -> None:
        self._stale.pop(name, None)
        label.deleteLater()
        button.deleteLater()
        self.changed.emit()

    def kwargs(self) -> dict[str, object]:
        """Only what was chosen: the set rows, and the stale kwargs not yet removed. Raises ValueError for JSON text
        that isn't JSON."""
        result = {row.name: row.value() for row in self._rows if row.is_set}
        result.update(self._stale)
        return result


class NewToolDialog(QtWidgets.QDialog):
    """Asks for a new tool's id, checked as it is typed, and its name."""

    def __init__(self, existing_ids: typing.Collection[str], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Tool")
        self._existing = set(existing_ids)

        layout = QtWidgets.QFormLayout(self)
        self.input_id = QtWidgets.QLineEdit()
        self.input_id.setPlaceholderText("area.topic.action, for example rigmodules.pose.flip")
        self.input_name = QtWidgets.QLineEdit()
        self.problem = QtWidgets.QLabel("")
        self.problem.setStyleSheet("color: #e05555;")
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
        well_formed = bool(tool_registry.ID_PATTERN.match(tool_id))
        if tool_id and not well_formed:
            message = "The id is dot-separated lowercase segments, such as rigmodules.pose.flip."
        elif tool_id in self._existing:
            message = f"The id '{tool_id}' is already used."
        else:
            message = ""
        self.problem.setText(message)
        valid = well_formed and not message and bool(self.input_name.text().strip())
        self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(valid)

    def values(self) -> tuple[str, str]:
        return self.input_id.text(), self.input_name.text().strip()


class ToolManagerWindow(SimpleWindow):
    """UI controller providing creation, modification, and execution capabilities for tools."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        parent = parent or get_maya_main_window()
        super().__init__(parent=parent, title="Master Tool Registry Manager")

        self.registry = Registry()
        self.current_filepath = None
        self.active_tool_id = None
        self.dirty = False
        self._block_ui_updates = False
        self._module_names: list[str] | None = None

        self.resize(950, 750)
        self._build_menu_bar()
        self._build_ui_layout()
        self._connect_signals()
        self._set_view_state(enabled=False)
        self._load_registry(bmaya.maya.constants.TOOL_REGISTRY_PATH)

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

        self.argument_form = ArgumentForm()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.argument_form)
        call_layout.addWidget(scroll)

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
        """Wires up all functional event triggers to internal tracking logic."""
        self.action_open.triggered.connect(self._on_open_registry)
        self.action_save.triggered.connect(self._on_save_registry)
        self.action_save_as.triggered.connect(self._on_save_registry_as)
        self.action_exit.triggered.connect(self.close)

        self.tool_list.currentItemChanged.connect(self._on_tool_selection_changed)
        self.search_input.textChanged.connect(self._filter_list_items)
        self.btn_add_tool.clicked.connect(self._on_add_new_tool)
        self.btn_delete_tool.clicked.connect(self._on_delete_selected_tool)
        self.btn_execute.clicked.connect(self._on_execute_payload)

        # Live Form Modifications
        self.input_name.textChanged.connect(self._sync_form_to_memory)
        self.input_short_name.textChanged.connect(self._sync_form_to_memory)
        self.input_icon.textChanged.connect(self._sync_form_to_memory)
        self.check_enabled.toggled.connect(self._sync_form_to_memory)
        self.input_module.editingFinished.connect(self._on_module_changed)
        self.input_module.textEdited.connect(self._on_module_typing)
        self.combo_function.currentIndexChanged.connect(self._on_function_changed)
        self.argument_form.changed.connect(self._sync_form_to_memory)

    def _set_view_state(self, enabled: bool) -> None:
        """Safely locks or opens the form editing side based on tracking state context."""
        for widget in (self.input_name, self.input_short_name, self.input_icon, self.check_enabled, self.input_module,
                       self.combo_function, self.argument_form, self.btn_delete_tool):
            widget.setEnabled(enabled)
        self.btn_execute.setEnabled(False)  # Run waits for a status of OK

    # --- the list --------------------------------------------------------------------------------------------

    def _refresh_list_view(self, select: str | None = None) -> None:
        """Flushes and rebuilds the tool column matching cached state changes."""
        self._block_ui_updates = True
        self.tool_list.clear()

        for tool_id, tool in self.registry.tools.items():
            item = QtWidgets.QListWidgetItem(tool.name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, tool_id)
            item.setToolTip(tool_id)
            self.tool_list.addItem(item)

        self._block_ui_updates = False
        self._filter_list_items(self.search_input.text())
        if select:
            for i in range(self.tool_list.count()):
                if self.tool_list.item(i).data(QtCore.Qt.ItemDataRole.UserRole) == select:
                    self.tool_list.setCurrentItem(self.tool_list.item(i))
                    break

    def _filter_list_items(self, search_text: str) -> None:
        """Hides items in the list layout which fail to match filter strings."""
        search_text = search_text.lower()
        for i in range(self.tool_list.count()):
            item = self.tool_list.item(i)
            tool = self.registry.tools.get(item.data(QtCore.Qt.ItemDataRole.UserRole))
            if tool:
                match = search_text in tool.name.lower() or search_text in tool.short_name.lower() or search_text in tool.id
                item.setHidden(not match)

    def _on_tool_selection_changed(self, current: QtWidgets.QListWidgetItem, previous: QtWidgets.QListWidgetItem) -> None:
        """Maps specific tool attributes downstream into the interface layout values."""
        if not current or self._block_ui_updates:
            return

        tool = self.registry.tools.get(current.data(QtCore.Qt.ItemDataRole.UserRole))
        if not tool:
            return

        self.active_tool_id = tool.id
        self._block_ui_updates = True
        self.input_id.setText(tool.id)
        self.input_name.setText(tool.name)
        self.input_short_name.setText(tool.short_name)
        self.input_icon.setText(tool.icon or "")
        self.check_enabled.setChecked(tool.enabled)
        self.input_module.setText(tool.call.module)
        self._fill_functions(tool.call.module, tool.call.function)
        self._set_view_state(enabled=True)
        self._show_arguments(tool.call.kwargs)
        self._block_ui_updates = False
        self._update_status()

    # --- the call picker -------------------------------------------------------------------------------------

    def _on_module_typing(self, _text: str) -> None:
        """The completer lists modules, found on first use because walking the packages imports each package."""
        if self._module_names is None:
            self._module_names = list_modules()
            self.module_completer.setModel(QtCore.QStringListModel(self._module_names, self.module_completer))

    def _import_module(self, name: str) -> tuple[types.ModuleType | None, str]:
        """The module, or None and the reason."""
        if not name:
            return None, "no module"
        try:
            return importlib.import_module(name), ""
        except Exception as err:  # a tool module can fail to import in any way
            return None, f"cannot import module '{name}': {err}"

    def _fill_functions(self, module_name: str, current: str) -> None:
        """Fills the function drop-down from a module, keeping the saved function even when it isn't listed."""
        self.combo_function.blockSignals(True)
        self.combo_function.clear()
        module, _ = self._import_module(module_name)
        names = list_functions(module) if module else []
        if current and current not in names:
            names.append(current)
        for name in names:
            self.combo_function.addItem(name)
        self.combo_function.setCurrentIndex(self.combo_function.findText(current) if current else -1)
        self.combo_function.blockSignals(False)
        self._fit_function_width()
        self._show_doc()

    def _fit_function_width(self) -> None:
        """Sets the drop-down's minimum width to its size hint, which AdjustToContents sizes to the longest function
        name, so it follows the module as the call path changes."""
        self.combo_function.setMinimumWidth(0)
        self.combo_function.setMinimumWidth(self.combo_function.sizeHint().width())

    def _on_module_changed(self) -> None:
        if self._block_ui_updates or not self.active_tool_id:
            return
        self._block_ui_updates = True
        self._fill_functions(self.input_module.text().strip(), "")
        self._block_ui_updates = False
        self._on_function_changed()

    def _on_function_changed(self, *_args) -> None:
        if self._block_ui_updates or not self.active_tool_id:
            return
        self._block_ui_updates = True
        self._show_doc()
        self._show_arguments({})
        self._block_ui_updates = False
        self._sync_form_to_memory()

    def _current_function(self) -> typing.Callable | None:
        module, _ = self._import_module(self.input_module.text().strip())
        function = getattr(module, self.combo_function.currentText(), None) if module else None
        return function if callable(function) else None

    def _show_doc(self) -> None:
        function = self._current_function()
        doc = inspect.getdoc(function) if function else None
        self.label_doc.setText(doc.splitlines()[0] if doc else "")

    def _show_arguments(self, kwargs: dict[str, object]) -> None:
        self.argument_form.set_function(self._current_function(), kwargs)

    # --- editing ---------------------------------------------------------------------------------------------

    def _sync_form_to_memory(self, *_args) -> None:
        """Directly cascades interface modifications into the database record structures."""
        if self._block_ui_updates or not self.active_tool_id:
            return

        tool = self.registry.tools.get(self.active_tool_id)
        if not tool:
            return

        tool.name = self.input_name.text()
        tool.short_name = self.input_short_name.text()
        tool.icon = self.input_icon.text() if self.input_icon.text().strip() else None
        tool.enabled = self.check_enabled.isChecked()
        tool.call.module = self.input_module.text().strip()
        tool.call.function = self.combo_function.currentText()
        self.dirty = True

        problem = ""
        try:
            tool.call.kwargs = self.argument_form.kwargs()
        except ValueError as err:
            problem = str(err)
        self._update_status(problem)

        current_item = self.tool_list.currentItem()
        if current_item:
            current_item.setText(tool.name)

    def _update_status(self, problem: str = "") -> None:
        """OK, or the first problem of the tool's call. Run is enabled only on OK."""
        tool = self.registry.tools.get(self.active_tool_id)
        if tool is None:
            return
        message = problem or next(iter(tool_registry.check_call(tool.call)), "") or STATUS_OK
        ok = message == STATUS_OK
        self.label_status.setText(message)
        self.label_status.setStyleSheet("" if ok else "color: #e05555;")
        self.btn_execute.setEnabled(ok)

    def _on_add_new_tool(self) -> None:
        """Adds a tool with an id and a name. Its call is empty, and Save refuses until one is picked."""
        dialog = NewToolDialog(self.registry.tools, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        tool_id, name = dialog.values()
        self.registry.tools[tool_id] = Tool(tool_id, name, name, ToolCall("", ""))
        self.dirty = True
        self._refresh_list_view(select=tool_id)

    def _on_delete_selected_tool(self) -> None:
        """Removes the tool. A layout that still uses it is reported when the registry is saved."""
        current_item = self.tool_list.currentItem()
        if not self.active_tool_id or not current_item:
            return

        res = QtWidgets.QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to remove '{current_item.text()}' from registration entries?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if res != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self.registry.tools.pop(self.active_tool_id, None)
        self.active_tool_id = None
        self.dirty = True
        self._set_view_state(enabled=False)
        self._refresh_list_view()

        self._block_ui_updates = True
        for field in (self.input_id, self.input_name, self.input_short_name, self.input_icon, self.input_module):
            field.clear()
        self.combo_function.clear()
        self.argument_form.clear()
        self.label_doc.setText("")
        self.label_status.setText("")
        self.check_enabled.setChecked(False)
        self._block_ui_updates = False

    def _on_execute_payload(self) -> None:
        """Runs the tool as it is being edited, the way a menu item does."""
        tool = self.registry.tools.get(self.active_tool_id)
        if tool is None:
            return
        log.info(f"Running {tool.id} from the registry editor")
        try:
            tool_registry.run_tool(tool)
        except Exception as err:
            QtWidgets.QMessageBox.warning(self, "Run Failed", f"{tool.id}: {err}")

    # --- files -----------------------------------------------------------------------------------------------

    def _confirm_discard(self) -> bool:
        """True when there are no unsaved edits, or the user accepts losing them."""
        if not self.dirty:
            return True
        answer = QtWidgets.QMessageBox.question(
            self,
            "Unsaved Edits",
            "This registry has unsaved edits. Discard them?",
            QtWidgets.QMessageBox.StandardButton.Discard | QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        return answer == QtWidgets.QMessageBox.StandardButton.Discard

    def _on_open_registry(self) -> None:
        """Handles external system targeting to load and map tool collection configurations."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Tool Registry File", bmaya.maya.constants.TOOL_REGISTRY_PATH, "JSON Files (*.json)"
        )
        if filepath and self._confirm_discard():
            self._load_registry(filepath)

    def _load_registry(self, filepath: str) -> None:
        """Replaces the registry with a file's. A file that fails its check is refused with every problem."""
        try:
            registry = tool_registry.read_registry(filepath)
        except (FileNotFoundError, tool_registry.ToolDataError) as err:
            QtWidgets.QMessageBox.warning(self, "Load Error", str(err))
            return
        self.registry = registry
        self.current_filepath = filepath
        self.active_tool_id = None
        self.dirty = False
        self._set_view_state(enabled=False)
        self._refresh_list_view()

    def check_everything(self) -> tool_registry.ToolDataError | None:
        """The structure check and the calls check of the whole registry, and every menu layout against it when
        this is the master registry. None when all pass."""
        path = self.current_filepath or ""
        errors = []
        issues = tool_registry.check_registry(tool_registry.registry_to_dict(self.registry))
        issues += tool_registry.check_calls(self.registry)
        if issues:
            errors.append(tool_registry.ToolDataError(issues, path))
        if os.path.normcase(path) == os.path.normcase(bmaya.maya.constants.TOOL_REGISTRY_PATH):
            for layout_path in bmaya.maya_ui.tool_views.tool_menu.menu_layout_paths().values():
                try:
                    tool_registry.read_layout(layout_path, self.registry.tools)
                except FileNotFoundError as err:
                    errors.append(tool_registry.ToolDataError([tool_registry.Issue("", str(err))], layout_path))
                except tool_registry.ToolDataError as err:
                    errors.append(err)
        return tool_registry.ToolDataError.combine(errors) if errors else None

    def _on_save_registry(self) -> None:
        """Checks the whole registry and the layouts, and refuses with the full report. Otherwise writes atomically."""
        if not self.current_filepath:
            self._on_save_registry_as()
            return

        report = self.check_everything()
        if report is not None:
            QtWidgets.QMessageBox.critical(self, "Save Refused", str(report))
            return
        try:
            tool_registry.write_registry(self.registry, self.current_filepath)
        except (OSError, tool_registry.ToolDataError) as err:
            QtWidgets.QMessageBox.critical(self, "Save Error", str(err))
            return
        self.dirty = False
        log.info(f"Successfully saved master tools file system to: {self.current_filepath}")

    def _on_save_registry_as(self) -> None:
        """Prompts targets explicitly prior to serialization output functions."""
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Master Tool Registry As", "", "JSON Files (*.json)"
        )
        if not filepath:
            return

        self.current_filepath = filepath
        self._on_save_registry()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._confirm_discard():
            super().closeEvent(event)
        else:
            event.ignore()


def show_window() -> ToolManagerWindow:
    """Opens the Registry Editor."""
    window = ToolManagerWindow()
    window.show()
    return window
