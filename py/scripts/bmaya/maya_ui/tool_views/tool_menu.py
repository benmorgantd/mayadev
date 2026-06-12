"""Layout management interface for generating and configuring cascading Maya menus."""

import os
import json
import uuid
import maya.cmds as cmds
from PySide6 import QtWidgets, QtCore, QtGui
from bmaya.core import log
from bmaya.core.tool_registry import ToolRegistry
import bmaya.maya.constants
from bmaya.maya_ui.qtbase import SimpleWindow, Tree, TreeItem, get_maya_main_window


class ToolMenu(object):
    """Generates an editable, cascading Maya native window menu from a layout file."""

    def __init__(self, menu_id=None):
        self.menu_id = (
            menu_id if menu_id else f"ToolMenu_{str(uuid.uuid4())}".replace("-", "_")
        )
        self.hierarchy = []

    def load_layout(self, filepath):
        """Loads the view structural configuration file."""
        if not os.path.exists(filepath):
            return False

        with open(filepath, "r") as f:
            data = json.load(f)

        # NOTE: Maya will need this to be unique. We should append a guid.
        self.label = data.get("label", "Tool Menu")
        self.hierarchy = data.get("items", [])
        return True

    def build_ui(self, registry):
        """Clears out existing artifacts and draws the menu on the global menu bar."""
        # Clean up existing instance to prevent duplicate UI objects
        if cmds.menu(self.menu_id, exists=True):
            cmds.deleteUI(self.menu_id, menu=True)

        main_window = "MayaWindow"
        if not cmds.window(main_window, exists=True):
            raise RuntimeError("Maya Main Window container could not be found.")

        # Create root layout wrapper
        cmds.menu(self.menu_id, label=self.label, parent=main_window, tearOff=True)

        # Traverse layout rules recursively
        self._build_recursive(self.menu_id, self.hierarchy, registry)
        log.info(f"Built Tool Menu {self.label}")

    def _build_recursive(self, parent_layout, layout_items, registry):
        """Recurses down the UI hierarchy list to map elements onto maya native widgets."""
        for item in layout_items:
            item_type = item.get("type", "tool")

            if item_type == "separator":
                cmds.menuItem(divider=True, parent=parent_layout)

            elif item_type == "submenu":
                sub_label = item.get("label", "SubMenu")
                sub_menu = cmds.menuItem(
                    label=sub_label, subMenu=True, tearOff=True, parent=parent_layout
                )
                self._build_recursive(sub_menu, item.get("items", []), registry)

            elif item_type == "tool":
                guid = item.get("guid")
                tool = registry.tools.get(guid)

                if not tool:
                    # Gracefully render broken configurations without dropping
                    # layout parsing completely
                    cmds.menuItem(
                        label="Missing Tool (Ref: {0})".format(guid[:8]),
                        enable=False,
                        parent=parent_layout,
                    )
                    continue

                # Amalgamate explicit user toggles from both layout settings
                # and core parameters
                is_enabled = tool.enabled and item.get("enabled", True)

                # Keyword declaration isolates loop mutation side effects
                def execute_callback(*args, execution_payload=tool.script):
                    exec(execution_payload, globals())

                kwargs = {
                    "label": tool.name,
                    "command": execute_callback,
                    "enable": is_enabled,
                    "parent": parent_layout,
                }
                if tool.icon:
                    kwargs["image"] = tool.icon

                cmds.menuItem(**kwargs)


class ToolMenuEditorWindow(SimpleWindow):
    """UI controller for defining, organizing, and saving custom menu layouts."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        parent = parent or get_maya_main_window()
        super().__init__(parent=parent, title="Menu Layout Configuration Editor")

        self.registry = ToolRegistry()

        self.current_layout_path = None
        self._block_ui_updates = False

        self.resize(1000, 700)
        self._build_menu_bar()
        self._build_ui_layout()
        self._load_registry(bmaya.maya.constants.TOOL_REGISTRY_PATH)

        self._connect_signals()
        

    def _build_menu_bar(self) -> None:
        """Constructs the window's main pull-down file interactions."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        self.action_load_registry = file_menu.addAction("Load Master Registry...")
        file_menu.addSeparator()
        self.action_open_layout = file_menu.addAction("Open Menu Layout...")
        self.action_save_layout = file_menu.addAction("Save Menu Layout")
        self.action_save_layout_as = file_menu.addAction("Save Menu Layout As...")
        file_menu.addSeparator()
        self.action_exit = file_menu.addAction("Exit")

    def _build_ui_layout(self) -> None:
        """Generates the main split window view layouts for tools and menu hierarchies."""
        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.mainLayout.addWidget(main_splitter)

        # Left Column Layout (Registry Tools Browser)
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_group = QtWidgets.QGroupBox("Available Registry Tools")
        left_group_layout = QtWidgets.QVBoxLayout(left_group)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Filter registry tools...")
        left_group_layout.addWidget(self.search_input)

        self.tool_list = QtWidgets.QListWidget()
        left_group_layout.addWidget(self.tool_list)

        self.btn_add_to_menu = QtWidgets.QPushButton("Add Selected Tool to Menu ->")
        self.btn_add_to_menu.setMinimumHeight(30)
        left_group_layout.addWidget(self.btn_add_to_menu)
        
        left_layout.addWidget(left_group)

        # Right Column Layout (Tree Hierarchy Workspace)
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        meta_group = QtWidgets.QGroupBox("Menu Configurations")
        meta_layout = QtWidgets.QFormLayout(meta_group)
        self.input_menu_label = QtWidgets.QLineEdit()
        self.input_menu_label.setPlaceholderText("e.g., Custom Tools")
        meta_layout.addRow("Root Menu Label:", self.input_menu_label)
        right_layout.addWidget(meta_group)

        tree_group = QtWidgets.QGroupBox("Menu Item Hierarchy Tree")
        tree_layout = QtWidgets.QVBoxLayout(tree_group)

        # Utilize shared base tree architecture from package base
        self.hierarchy_tree = Tree()
        # Override the hardcoded height limitation defined inside the base module
        self.hierarchy_tree.setMaximumHeight(16777215) 
        self.hierarchy_tree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.hierarchy_tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        tree_layout.addWidget(self.hierarchy_tree)

        # Hierarchy Modification Operators
        hierarchy_control_layout = QtWidgets.QHBoxLayout()
        self.btn_add_submenu = QtWidgets.QPushButton("+ New Submenu")
        self.btn_add_separator = QtWidgets.QPushButton("+ Separator")
        self.btn_delete_item = QtWidgets.QPushButton("- Remove Item")
        
        hierarchy_control_layout.addWidget(self.btn_add_submenu)
        hierarchy_control_layout.addWidget(self.btn_add_separator)
        hierarchy_control_layout.addWidget(self.btn_delete_item)
        tree_layout.addLayout(hierarchy_control_layout)

        right_layout.addWidget(tree_group)

        # Assemble foundational split frame structures
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([350, 650])

    def _connect_signals(self) -> None:
        """Hooks events up to their execution slots."""
        # Menu Actions
        self.action_load_registry.triggered.connect(self._on_load_registry)
        self.action_open_layout.triggered.connect(self._on_open_layout)
        self.action_save_layout.triggered.connect(self._on_save_layout)
        self.action_save_layout_as.triggered.connect(self._on_save_layout_as)
        self.action_exit.triggered.connect(self.close)

        # Interactive Controls
        self.search_input.textChanged.connect(self._filter_registry_items)
        self.btn_add_to_menu.clicked.connect(self._on_add_tool_to_tree)
        self.btn_add_submenu.clicked.connect(self._on_add_submenu_to_tree)
        self.btn_add_separator.clicked.connect(self._on_add_separator_to_tree)
        self.btn_delete_item.clicked.connect(self._on_delete_tree_item)

    def _refresh_registry_list(self) -> None:
        """Updates list items to reflect entries loaded inside memory mappings."""
        self.tool_list.clear()
        for guid, tool in self.registry.tools.items():
            item = QtWidgets.QListWidgetItem(f"{tool.name} ({tool.short_name})")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, guid)
            self.tool_list.addItem(item)
        self._filter_registry_items(self.search_input.text())

    def _filter_registry_items(self, search_text: str) -> None:
        """Hides tool entries contextually according to search strings."""
        search_text = search_text.lower()
        for i in range(self.tool_list.count()):
            item = self.tool_list.item(i)
            item.setHidden(search_text not in item.text().lower())

    def _get_target_parent_node(self) -> tuple[QtCore.QObject, QtGui.QStandardItem | None]:
        """Returns the appropriate contextual nesting attachment points within the tree."""
        selected_items = self.hierarchy_tree.selectedItems()
        if not selected_items:
            return self.hierarchy_tree, None
        
        selected_item = selected_items[0]
        item_type = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        
        # If a submenu container is selected, append directly into it
        if item_type == "submenu":
            return selected_item, None
            
        # If another type is selected, insert next to it under its respective parent
        parent = selected_item.parent()
        if parent:
            return parent, selected_item
        return self.hierarchy_tree, selected_item

    def _create_tree_node(self, node_type: str, text: str, data: str | None = None) -> TreeItem:
        """Instantiates a normalized tracking row conforming to system base tree schemas."""
        node = TreeItem()
        node.setText(0, text)
        node.setData(0, QtCore.Qt.ItemDataRole.UserRole, node_type)
        
        if data:
            node.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, data)
            
        # Restrict structural edits based on type roles
        if node_type in ["separator", "tool"]:
            node.setFlags(node.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            
        return node

    def _on_add_tool_to_tree(self) -> None:
        """Appends selected registry tool configurations into the layout structure."""
        current_list_item = self.tool_list.currentItem()
        if not current_list_item:
            return

        guid = current_list_item.data(QtCore.Qt.ItemDataRole.UserRole)
        tool = self.registry.tools.get(guid)
        if not tool:
            return

        parent_layout, sibling = self._get_target_parent_node()
        node = self._create_tree_node("tool", tool.name, data=guid)

        if parent_layout == self.hierarchy_tree:
            if sibling:
                index = self.hierarchy_tree.indexOfTopLevelItem(sibling)
                self.hierarchy_tree.insertTopLevelItem(index + 1, node)
            else:
                self.hierarchy_tree.addTopLevelItem(node)
        else:
            if sibling:
                index = parent_layout.indexOfChild(sibling)
                parent_layout.insertChild(index + 1, node)
            else:
                parent_layout.addChild(node)
                parent_layout.setExpanded(True)

    def _on_add_submenu_to_tree(self) -> None:
        """Creates an editable container folder for nested structural formatting."""
        parent_layout, sibling = self._get_target_parent_node()
        node = self._create_tree_node("submenu", "New Submenu Container")

        if parent_layout == self.hierarchy_tree:
            if sibling:
                index = self.hierarchy_tree.indexOfTopLevelItem(sibling)
                self.hierarchy_tree.insertTopLevelItem(index + 1, node)
            else:
                self.hierarchy_tree.addTopLevelItem(node)
        else:
            if sibling:
                index = parent_layout.indexOfChild(sibling)
                parent_layout.insertChild(index + 1, node)
            else:
                parent_layout.addChild(node)
                parent_layout.setExpanded(True)

        self.hierarchy_tree.setCurrentItem(node)
        self.hierarchy_tree.editItem(node, 0)

    def _on_add_separator_to_tree(self) -> None:
        """Inserts layout tracking lines inside target menu tiers."""
        parent_layout, sibling = self._get_target_parent_node()
        node = self._create_tree_node("separator", "-----------------------------")

        if parent_layout == self.hierarchy_tree:
            if sibling:
                index = self.hierarchy_tree.indexOfTopLevelItem(sibling)
                self.hierarchy_tree.insertTopLevelItem(index + 1, node)
            else:
                self.hierarchy_tree.addTopLevelItem(node)
        else:
            if sibling:
                index = parent_layout.indexOfChild(sibling)
                parent_layout.insertChild(index + 1, node)
            else:
                parent_layout.addChild(node)
                parent_layout.setExpanded(True)

    def _on_delete_tree_item(self) -> None:
        """Pops selected components or sub-hierarchies out of workspace memory."""
        selected_items = self.hierarchy_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        parent = item.parent()
        
        if parent:
            parent.removeChild(item)
        else:
            index = self.hierarchy_tree.indexOfTopLevelItem(item)
            self.hierarchy_tree.takeTopLevelItem(index)

    def _build_tree_recursively(self, items_list: list, parent_node: QtCore.QObject) -> None:
        """Parses array models structurally down into graphical UI elements."""
        for item in items_list:
            item_type = item.get("type", "tool")

            if item_type == "separator":
                node = self._create_tree_node("separator", "-----------------------------")
            elif item_type == "submenu":
                label = item.get("label", "SubMenu")
                node = self._create_tree_node("submenu", label)
                self._build_tree_recursively(item.get("items", []), node)
            elif item_type == "tool":
                guid = item.get("guid")
                tool = self.registry.tools.get(guid)
                display_name = tool.name if tool else f"Unknown Tool Reference [Ref: {guid[:8]}]"
                node = self._create_tree_node("tool", display_name, data=guid)
            else:
                continue

            if parent_node == self.hierarchy_tree:
                self.hierarchy_tree.addTopLevelItem(node)
            else:
                parent_node.addChild(node)

    def _serialize_tree_node(self, item: TreeItem) -> dict:
        """Converts structural workspace node layouts back down into clean dictionary states."""
        node_type = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        if node_type == "submenu":
            child_items = []
            for i in range(item.childCount()):
                child_items.append(self._serialize_tree_node(item.child(i)))
            return {
                "type": "submenu",
                "label": item.text(0),
                "items": child_items
            }
        elif node_type == "separator":
            return {"type": "separator"}
        elif node_type == "tool":
            guid = item.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
            return {
                "type": "tool",
                "guid": guid,
                "enabled": True
            }
        return {}

    def _on_load_registry(self) -> None:
        """Maps an external master layout registry into system validation rules."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Master Tool Registry Reference", bmaya.maya.constants.TOOL_REGISTRY_PATH, "JSON Files (*.json)"
        )
        if not filepath:
            return

        self._load_registry(filepath)
    
    def _load_registry(self, filepath: str) -> None:
        if self.registry.load_registry(filepath):
            self._refresh_registry_list()
            # Loop and refresh the visual text fields of any pre-existing menu mappings
            self._sync_tree_display_names()
        else:
            QtWidgets.QMessageBox.warning(self, "Load Failure", f"Could not read registry configuration: {filepath}")

    def _sync_tree_display_names(self) -> None:
        """Traverses the hierarchy tree to resolve tool display labels from GUID properties."""
        def _recurse(node):
            for i in range(node.childCount() if hasattr(node, "child") else node.topLevelItemCount()):
                child = node.child(i) if hasattr(node, "child") else node.topLevelItem(i)
                if child.data(0, QtCore.Qt.ItemDataRole.UserRole) == "tool":
                    guid = child.data(0, QtCore.Qt.ItemDataRole.UserRole + 1)
                    tool = self.registry.tools.get(guid)
                    if tool:
                        child.setText(0, tool.name)
                _recurse(child)

        _recurse(self.hierarchy_tree)

    def _on_open_layout(self) -> None:
        """Parses a saved JSON menu layout scheme mapping into workspace nodes."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Menu Layout Mapping", bmaya.maya.constants.TOOLS_PATH, "JSON Files (*.json)"
        )
        if not filepath:
            return

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            self.hierarchy_tree.clear()
            self.input_menu_label.setText(data.get("label", "Tool Menu"))
            
            self._build_tree_recursively(data.get("items", []), self.hierarchy_tree)
            self.current_layout_path = filepath
            log.info(f"Loaded layout design specification sheet from: {filepath}")
        except Exception as err:
            QtWidgets.QMessageBox.critical(self, "Parsing Error", f"Failed structural map evaluation: {err}")

    def _on_save_layout(self) -> None:
        """Serializes current layout parameters down to the existing file path."""
        if not self.current_layout_path:
            self._on_save_layout_as()
            return

        layout_data = {
            "label": self.input_menu_label.text().strip() or "Tool Menu",
            "items": []
        }

        for i in range(self.hierarchy_tree.topLevelItemCount()):
            top_item = self.hierarchy_tree.topLevelItem(i)
            layout_data["items"].append(self._serialize_tree_node(top_item))

        try:
            with open(self.current_layout_path, "w") as f:
                json.dump(layout_data, f, indent=4)
            log.info(f"Menu layout parameters successfully flushed to disk: {self.current_layout_path}")
        except Exception as err:
            QtWidgets.QMessageBox.critical(self, "File Output Failure", f"Could not write data structure to path target: {err}")

    def _on_save_layout_as(self) -> None:
        """Prompts targets explicitly prior to serialization output functions."""
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Menu Layout As Specification", bmaya.maya.constants.TOOLS_PATH, "JSON Files (*.json)"
        )
        if not filepath:
            return

        self.current_layout_path = filepath
        self._on_save_layout()


def show_menu_editor_ui() -> ToolMenuEditorWindow:
    """Helper instantiation execution method entry pipeline standardizer."""
    window = ToolMenuEditorWindow()
    window.show()
    return window