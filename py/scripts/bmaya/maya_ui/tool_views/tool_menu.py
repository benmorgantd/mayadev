"""Menus built from tool layout files, and the editor for the layouts."""

from __future__ import annotations

import os

import maya.cmds as cmds
from PySide6 import QtWidgets, QtCore
from bmaya.core import log
from bmaya.core import tool_registry
from bmaya.core.tool_registry import Layout, LayoutItem, Registry, Separator, Submenu, ToolItem
import bmaya.maya.constants
from bmaya.maya_ui.qtbase import SimpleWindow, Tree, TreeItem, get_maya_main_window

ROLE_TYPE = QtCore.Qt.ItemDataRole.UserRole
ROLE_TOOL_ID = QtCore.Qt.ItemDataRole.UserRole + 1
SEPARATOR_TEXT = "-----------------------------"


class ToolMenu(object):
    """Builds a cascading menu on Maya's main menu bar from a checked Layout and Registry."""

    def __init__(self, menu_id: str, layout: Layout, registry: Registry) -> None:
        self.menu_id = menu_id
        self.layout = layout
        self.registry = registry

    def build_ui(self) -> None:
        """Deletes the menu if it exists and draws it again."""
        delete_menu(self.menu_id)

        main_window = "MayaWindow"
        if not cmds.window(main_window, exists=True):
            raise RuntimeError("Maya Main Window container could not be found.")

        cmds.menu(self.menu_id, label=self.layout.label, parent=main_window, tearOff=True)
        self._build_items(self.menu_id, self.layout.items)
        log.info(f"Built Tool Menu {self.layout.label}")

    def _build_items(self, parent: str, items: list[LayoutItem]) -> None:
        for item in items:
            if isinstance(item, Separator):
                cmds.menuItem(divider=True, parent=parent)
            elif isinstance(item, Submenu):
                submenu = cmds.menuItem(label=item.label, subMenu=True, tearOff=True, parent=parent)
                self._build_items(submenu, item.items)
            elif isinstance(item, ToolItem):
                self._build_tool(parent, item)

    def _build_tool(self, parent: str, item: ToolItem) -> None:
        tool = self.registry.tools[item.tool]  # a checked layout names only tools in the registry
        # The function is imported on each click, so a module reloaded since the menu was built is read again,
        # and a module that fails to import breaks only its own items.
        kwargs = {
            "label": tool.name,
            "command": lambda *_, tool=tool: tool_registry.run_tool(tool),
            "enable": tool.enabled and item.enabled,
            "parent": parent,
        }
        if tool.icon:
            kwargs["image"] = tool.icon
        cmds.menuItem(**kwargs)


def delete_menu(menu_id: str) -> None:
    if cmds.menu(menu_id, exists=True):
        cmds.deleteUI(menu_id, menu=True)


def delete_plugin_menus() -> None:
    """Deletes the menus that need a plugin. The dev reload runs it before the plugin unloads."""
    for spec in bmaya.maya.constants.MENUS:
        if spec.plugin:
            delete_menu(spec.menu_id)


def reload_menus() -> None:
    """Builds every menu again from the layout and registry files, so edits to them show without a restart. The
    plugin and the scene are untouched. Deferred, because a menu item starts it and its own menu is rebuilt."""
    cmds.evalDeferred(_reload_menus)


def _reload_menus() -> None:
    build_menus()
    log.info("Reloaded the menus")


def _plugin_loaded(plugin: str) -> bool:
    try:
        return bool(cmds.pluginInfo(plugin, query=True, loaded=True))
    except RuntimeError:
        return False


def menu_layout_paths() -> dict[str, str]:
    """Each menu's layout file, by menu id."""
    return {spec.menu_id: os.path.join(bmaya.maya.constants.TOOLS_PATH, spec.layout) for spec in bmaya.maya.constants.MENUS}


def build_menus() -> None:
    """Reads the registry and every layout in bmaya.maya.constants.MENUS, checks them all, then deletes and
    rebuilds every menu. A menu whose plugin isn't loaded is deleted and not rebuilt. Raises FileNotFoundError or
    ToolDataError, with every problem of every file, before touching a menu, so a bad edit leaves the current
    menus in place."""
    paths = menu_layout_paths()
    registry, layouts = tool_registry.load_all(bmaya.maya.constants.TOOL_REGISTRY_PATH, list(paths.values()))
    for spec in bmaya.maya.constants.MENUS:
        if spec.plugin and not _plugin_loaded(spec.plugin):
            delete_menu(spec.menu_id)
            continue
        ToolMenu(spec.menu_id, layouts[paths[spec.menu_id]], registry).build_ui()


class ToolMenuEditorWindow(SimpleWindow):
    """UI controller for defining, organizing, and saving custom menu layouts."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        parent = parent or get_maya_main_window()
        super().__init__(parent=parent, title="Menu Layout Configuration Editor")

        self.registry = Registry()
        self.current_layout_path = None

        self.resize(1000, 700)
        self._build_menu_bar()
        self._build_ui_layout()
        self._connect_signals()
        self._load_registry(bmaya.maya.constants.TOOL_REGISTRY_PATH)

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

        tree_group = QtWidgets.QGroupBox("Menu Item Hierarchy Tree (a ticked tool is enabled)")
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
        for tool_id, tool in self.registry.tools.items():
            item = QtWidgets.QListWidgetItem(f"{tool.name} ({tool.short_name})")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, tool_id)
            item.setToolTip(tool_id)
            self.tool_list.addItem(item)
        self._filter_registry_items(self.search_input.text())

    def _filter_registry_items(self, search_text: str) -> None:
        """Hides tool entries contextually according to search strings."""
        search_text = search_text.lower()
        for i in range(self.tool_list.count()):
            item = self.tool_list.item(i)
            item.setHidden(search_text not in item.text().lower())

    # --- tree rows -------------------------------------------------------------------------------------------

    def _create_tree_node(self, node_type: str, text: str, tool_id: str | None = None, enabled: bool = True) -> TreeItem:
        """One tree row. A tool row is checkable: the check box is the item's `enabled`, and its tooltip is the id."""
        node = TreeItem()
        node.setText(0, text)
        node.setData(0, ROLE_TYPE, node_type)

        if node_type == "tool":
            node.setData(0, ROLE_TOOL_ID, tool_id)
            node.setToolTip(0, tool_id)
            node.setCheckState(0, QtCore.Qt.CheckState.Checked if enabled else QtCore.Qt.CheckState.Unchecked)
        if node_type in ("separator", "tool"):
            node.setFlags(node.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        return node

    def _tool_node(self, tool_id: str, enabled: bool = True) -> TreeItem:
        tool = self.registry.tools.get(tool_id)
        text = tool.name if tool else f"Unknown tool [{tool_id}]"
        return self._create_tree_node("tool", text, tool_id, enabled)

    def _insert_node(self, node: TreeItem) -> None:
        """Adds a row inside the selected submenu, else after the selected row, else at the end."""
        selected = self.hierarchy_tree.selectedItems()
        selected_item = selected[0] if selected else None

        if selected_item is not None and selected_item.data(0, ROLE_TYPE) == "submenu":
            selected_item.addChild(node)
            selected_item.setExpanded(True)
            return
        parent = selected_item.parent() if selected_item is not None else None
        if parent is not None:
            parent.insertChild(parent.indexOfChild(selected_item) + 1, node)
        elif selected_item is not None:
            self.hierarchy_tree.insertTopLevelItem(self.hierarchy_tree.indexOfTopLevelItem(selected_item) + 1, node)
        else:
            self.hierarchy_tree.addTopLevelItem(node)

    def _on_add_tool_to_tree(self) -> None:
        """Appends selected registry tool configurations into the layout structure."""
        current = self.tool_list.currentItem()
        if current is None:
            return
        self._insert_node(self._tool_node(current.data(QtCore.Qt.ItemDataRole.UserRole)))

    def _on_add_submenu_to_tree(self) -> None:
        """Creates an editable container folder for nested structural formatting."""
        node = self._create_tree_node("submenu", "New Submenu Container")
        self._insert_node(node)
        self.hierarchy_tree.setCurrentItem(node)
        self.hierarchy_tree.editItem(node, 0)

    def _on_add_separator_to_tree(self) -> None:
        """Inserts layout tracking lines inside target menu tiers."""
        self._insert_node(self._create_tree_node("separator", SEPARATOR_TEXT))

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
            self.hierarchy_tree.takeTopLevelItem(self.hierarchy_tree.indexOfTopLevelItem(item))

    # --- tree and Layout -------------------------------------------------------------------------------------

    def set_layout(self, layout: Layout) -> None:
        """Replaces the tree with a Layout."""
        self.hierarchy_tree.clear()
        self.input_menu_label.setText(layout.label)
        self._add_items(layout.items, self.hierarchy_tree.invisibleRootItem())

    def _add_items(self, items: list[LayoutItem], parent: QtWidgets.QTreeWidgetItem) -> None:
        for item in items:
            if isinstance(item, Separator):
                node = self._create_tree_node("separator", SEPARATOR_TEXT)
            elif isinstance(item, Submenu):
                node = self._create_tree_node("submenu", item.label)
                self._add_items(item.items, node)
            else:
                node = self._tool_node(item.tool, item.enabled)
            parent.addChild(node)

    def get_layout(self) -> Layout:
        """The tree as a Layout."""
        root = self.hierarchy_tree.invisibleRootItem()
        label = self.input_menu_label.text().strip() or "Tool Menu"
        return Layout(label, self._read_items(root))

    def _read_items(self, parent: QtWidgets.QTreeWidgetItem) -> list[LayoutItem]:
        items: list[LayoutItem] = []
        for i in range(parent.childCount()):
            node = parent.child(i)
            node_type = node.data(0, ROLE_TYPE)
            if node_type == "submenu":
                items.append(Submenu(node.text(0), self._read_items(node)))
            elif node_type == "separator":
                items.append(Separator())
            else:
                enabled = node.checkState(0) == QtCore.Qt.CheckState.Checked
                items.append(ToolItem(node.data(0, ROLE_TOOL_ID), enabled))
        return items

    # --- files -----------------------------------------------------------------------------------------------

    def _on_load_registry(self) -> None:
        """Maps an external master layout registry into system validation rules."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Master Tool Registry Reference", bmaya.maya.constants.TOOL_REGISTRY_PATH, "JSON Files (*.json)"
        )
        if filepath:
            self._load_registry(filepath)

    def _load_registry(self, filepath: str) -> None:
        """Replaces the registry. A file that fails its check is refused, and the loaded registry stays."""
        try:
            registry = tool_registry.read_registry(filepath)
        except (FileNotFoundError, tool_registry.ToolDataError) as err:
            QtWidgets.QMessageBox.warning(self, "Load Failure", str(err))
            return
        self.registry = registry
        self._refresh_registry_list()
        self._sync_tree_display_names()

    def _sync_tree_display_names(self) -> None:
        """Refreshes the tool rows' labels from the registry."""
        def _recurse(parent):
            for i in range(parent.childCount()):
                node = parent.child(i)
                if node.data(0, ROLE_TYPE) == "tool":
                    node.setText(0, self._tool_node(node.data(0, ROLE_TOOL_ID)).text(0))
                _recurse(node)

        _recurse(self.hierarchy_tree.invisibleRootItem())

    def _on_open_layout(self) -> None:
        """Reads a layout file into the tree. A file that fails its check is refused with every problem."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Menu Layout Mapping", bmaya.maya.constants.TOOLS_PATH, "JSON Files (*.json)"
        )
        if not filepath:
            return

        try:
            layout = tool_registry.read_layout(filepath, self.registry.tools)
        except (FileNotFoundError, tool_registry.ToolDataError) as err:
            QtWidgets.QMessageBox.critical(self, "Layout Error", str(err))
            return
        self.set_layout(layout)
        self.current_layout_path = filepath
        log.info(f"Loaded layout design specification sheet from: {filepath}")

    def _on_save_layout(self) -> None:
        """Checks the layout against the registry, then writes it to the existing file path."""
        if not self.current_layout_path:
            self._on_save_layout_as()
            return

        try:
            tool_registry.write_layout(self.get_layout(), self.current_layout_path, self.registry.tools)
        except (OSError, tool_registry.ToolDataError) as err:
            QtWidgets.QMessageBox.critical(self, "File Output Failure", str(err))
            return
        log.info(f"Menu layout parameters successfully flushed to disk: {self.current_layout_path}")

    def _on_save_layout_as(self) -> None:
        """Prompts targets explicitly prior to serialization output functions."""
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Menu Layout As Specification", bmaya.maya.constants.TOOLS_PATH, "JSON Files (*.json)"
        )
        if not filepath:
            return

        self.current_layout_path = filepath
        self._on_save_layout()


def show_window() -> ToolMenuEditorWindow:
    """Opens the Menu Editor."""
    window = ToolMenuEditorWindow()
    window.show()
    return window
