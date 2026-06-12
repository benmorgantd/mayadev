"""Tool management interface for managing the master tools registry."""

import os
import uuid
from PySide6 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds

from bmaya.core.tool_registry import Tool, ToolRegistry
from bmaya.core import log
import bmaya.maya.constants
from bmaya.maya_ui.qtbase import SimpleWindow, get_maya_main_window, PythonSyntaxHighlighter


class ToolManagerWindow(SimpleWindow):
    """UI controller providing creation, modification, and execution capabilities for tools."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        parent = parent or get_maya_main_window()
        super().__init__(parent=parent, title="Master Tool Registry Manager")

        self.registry = ToolRegistry()
        self.current_filepath = None
        self.active_tool_guid = None
        self._block_ui_updates = False

        self.resize(950, 650)
        self._build_menu_bar()
        self._build_ui_layout()
        self._connect_signals()
        self._set_view_state(enabled=False)
        self._load_registry(bmaya.maya.constants.TOOL_REGISTRY_PATH)

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

        self.input_name = QtWidgets.QLineEdit()
        self.input_short_name = QtWidgets.QLineEdit()
        self.input_icon = QtWidgets.QLineEdit()
        self.check_enabled = QtWidgets.QCheckBox("Active in menus")

        form_layout.addRow("Full Name:", self.input_name)
        form_layout.addRow("Short Name:", self.input_short_name)
        form_layout.addRow("Icon Path/Name:", self.input_icon)
        form_layout.addRow("Status:", self.check_enabled)
        right_layout.addWidget(form_group)

        # Script Workspace Allocation
        editor_group = QtWidgets.QGroupBox("Python Execution Payload")
        editor_layout = QtWidgets.QVBoxLayout(editor_group)

        self.script_editor = QtWidgets.QPlainTextEdit()
        # Apply clean monospaced font spacing mechanics
        font = QtGui.QFont("Consolas" if os.name == "nt" else "Monospace", 10)
        self.script_editor.setFont(font)
        self.highlighter = PythonSyntaxHighlighter(self.script_editor.document())

        editor_layout.addWidget(self.script_editor)

        self.btn_execute = QtWidgets.QPushButton("Execute Script View Block")
        self.btn_execute.setMinimumHeight(30)
        editor_layout.addWidget(self.btn_execute)
        right_layout.addWidget(editor_group)

        # Assemble foundational layout panes
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([300, 650])

    def _connect_signals(self) -> None:
        """Wires up all functional event triggers to internal tracking logic."""
        # Menu Actions
        self.action_open.triggered.connect(self._on_open_registry)
        self.action_save.triggered.connect(self._on_save_registry)
        self.action_save_as.triggered.connect(self._on_save_registry_as)
        self.action_exit.triggered.connect(self.close)

        # Management and Exploration Hooks
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
        self.script_editor.textChanged.connect(self._sync_form_to_memory)

    def _set_view_state(self, enabled: bool) -> None:
        """Safely locks or opens the form editing side based on tracking state context."""
        self.input_name.setEnabled(enabled)
        self.input_short_name.setEnabled(enabled)
        self.input_icon.setEnabled(enabled)
        self.check_enabled.setEnabled(enabled)
        self.script_editor.setEnabled(enabled)
        self.btn_execute.setEnabled(enabled)
        self.btn_delete_tool.setEnabled(enabled)

    def _refresh_list_view(self) -> None:
        """Flushes and rebuilds the tool column matching cached state changes."""
        self._block_ui_updates = True
        self.tool_list.clear()

        for guid, tool in self.registry.tools.items():
            item = QtWidgets.QListWidgetItem(tool.name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, guid)
            self.tool_list.addItem(item)

        self._block_ui_updates = False
        self._filter_list_items(self.search_input.text())

    def _filter_list_items(self, search_text: str) -> None:
        """Hides items in the list layout which fail to match filter strings."""
        search_text = search_text.lower()
        for i in range(self.tool_list.count()):
            item = self.tool_list.item(i)
            guid = item.data(QtCore.Qt.ItemDataRole.UserRole)
            tool = self.registry.tools.get(guid)
            
            if tool:
                match = (search_text in tool.name.lower() or 
                         search_text in tool.short_name.lower())
                item.setHidden(not match)

    def _on_tool_selection_changed(self, current: QtWidgets.QListWidgetItem, previous: QtWidgets.QListWidgetItem) -> None:
        """Maps specific tool attributes downstream into the interface layout values."""
        if not current or self._block_ui_updates:
            return

        guid = current.data(QtCore.Qt.ItemDataRole.UserRole)
        tool = self.registry.tools.get(guid)

        if not tool:
            return

        self.active_tool_guid = guid
        self._block_ui_updates = True

        self.input_name.setText(tool.name)
        self.input_short_name.setText(tool.short_name)
        self.input_icon.setText(tool.icon or "")
        self.check_enabled.setChecked(tool.enabled)
        self.script_editor.setPlainText(tool.script)

        self._set_view_state(enabled=True)
        self._block_ui_updates = False

    def _sync_form_to_memory(self) -> None:
        """Directly cascades interface modifications into the database record structures."""
        if self._block_ui_updates or not self.active_tool_guid:
            return

        tool = self.registry.tools.get(self.active_tool_guid)
        if not tool:
            return

        tool.name = self.input_name.text()
        tool.short_name = self.input_short_name.text()
        tool.icon = self.input_icon.text() if self.input_icon.text().strip() else None
        tool.enabled = self.check_enabled.isChecked()
        tool.script = self.script_editor.toPlainText()

        # Update the live name tracking inside the list widget row representation
        current_item = self.tool_list.currentItem()
        if current_item:
            current_item.setText(tool.name)

    def _on_add_new_tool(self) -> None:
        """Instantiates a template tool registration record within memory space."""
        new_guid = str(uuid.uuid4())
        new_tool = Tool(
            name="New Tool Base Entry",
            script="# Enter execution scripts here\nimport maya.cmds as cmds\n",
            guid=new_guid
        )
        self.registry.register_tool(new_tool)
        self._refresh_list_view()

        # Isolate and select the new tool element record row automatically
        for i in range(self.tool_list.count()):
            item = self.tool_list.item(i)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == new_guid:
                self.tool_list.setCurrentItem(item)
                break

    def _on_delete_selected_tool(self) -> None:
        """Purges active registration record instances completely from system tracking maps."""
        if not self.active_tool_guid:
            return

        current_item = self.tool_list.currentItem()
        if not current_item:
            return

        res = QtWidgets.QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to remove '{current_item.text()}' from registration entries?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if res == QtWidgets.QMessageBox.StandardButton.Yes:
            self.registry.tools.pop(self.active_tool_guid, None)
            self.active_tool_guid = None
            self._set_view_state(enabled=False)
            self._refresh_list_view()

            # Clean blank field displays
            self._block_ui_updates = True
            self.input_name.clear()
            self.input_short_name.clear()
            self.input_icon.clear()
            self.check_enabled.setChecked(False)
            self.script_editor.clear()
            self._block_ui_updates = False

    def _on_execute_payload(self) -> None:
        """Directly parses script content out of the view layer into the Maya session."""
        payload = self.script_editor.toPlainText()
        if not payload.strip():
            return
        
        log.info(f"Executing manual view text block for context evaluation...")
        try:
            exec(payload, globals())
        except Exception as err:
            cmds.warning(f"Script execution run failed: {err}")

    def _on_open_registry(self) -> None:
        """Handles external system targeting to load and map tool collection configurations."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Tool Registry File", bmaya.maya.constants.TOOL_REGISTRY_PATH, "JSON Files (*.json)"
        )
        if not filepath:
            return
        
        self._load_registry(filepath)
    
    def _load_registry(self, filepath: str) -> None:
        if self.registry.load_registry(filepath):
            self.current_filepath = filepath
            self.active_tool_guid = None
            self._set_view_state(enabled=False)
            self._refresh_list_view()
        else:
            QtWidgets.QMessageBox.warning(self, "Load Error", f"Target file tracking error context: {filepath}")

    def _on_save_registry(self) -> None:
        """Flushes memory structures to disk paths if explicitly assigned previously."""
        if not self.current_filepath:
            self._on_save_registry_as()
            return

        try:
            self.registry.save_registry(self.current_filepath)
            log.info(f"Successfully saved master tools file system to: {self.current_filepath}")
        except Exception as err:
            QtWidgets.QMessageBox.critical(self, "Save Error", f"Failed parsing database manifest to path destination: {err}")

    def _on_save_registry_as(self) -> None:
        """Prompts targets explicitly prior to serialization output functions."""
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Master Tool Registry As", "", "JSON Files (*.json)"
        )
        if not filepath:
            return

        self.current_filepath = filepath
        self._on_save_registry()


def show_ui() -> ToolManagerWindow:
    """Helper creation entry standardizing initialization logic."""
    window = ToolManagerWindow()
    window.show()
    return window