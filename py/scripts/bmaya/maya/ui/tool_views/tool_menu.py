import os
import json
import maya.cmds as cmds
from bmaya.core import log


class ToolMenu(object):
    """Generates an editable, cascading Maya native window menu from a layout file."""

    def __init__(self, menu_id=None):
        self.menu_id = menu_id or "{0}Menu".format(label.replace(" ", ""))
        self.hierarchy = []

    def load_layout(self, filepath):
        """Loads the view structural configuration file."""
        if not os.path.exists(filepath):
            return False

        with open(filepath, 'r') as f:
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
            raise RuntimeError(
                "Maya Main Window container could not be found.")

        # Create root layout wrapper
        cmds.menu(
            self.menu_id,
            label=self.label,
            parent=main_window,
            tearOff=True)

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
                    label=sub_label,
                    subMenu=True,
                    tearOff=True,
                    parent=parent_layout
                )
                self._build_recursive(
                    sub_menu, item.get(
                        "items", []), registry)

            elif item_type == "tool":
                guid = item.get("guid")
                tool = registry.tools.get(guid)

                if not tool:
                    # Gracefully render broken configurations without dropping
                    # layout parsing completely
                    cmds.menuItem(
                        label="Missing Tool (Ref: {0})".format(guid[:8]),
                        enable=False,
                        parent=parent_layout
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
                    "parent": parent_layout
                }
                if tool.icon:
                    kwargs["image"] = tool.icon

                cmds.menuItem(**kwargs)
