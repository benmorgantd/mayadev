from __future__ import annotations

import dataclasses
import os
import maya.cmds as cmds

if not os.environ.get("MAYADEV_ROOT"):
    raise EnvironmentError(
        "MAYADEV_ROOT environment variable not set in your Maya.env. "
        "Please set it to the root directory of the mayadev repository."
    )

MAYADEV_ROOT = os.environ["MAYADEV_ROOT"]

TOOLS_PATH = os.path.join(MAYADEV_ROOT, "toolsets")
TOOL_REGISTRY_PATH = os.path.join(TOOLS_PATH, "master_tool_registry.json")


@dataclasses.dataclass(frozen=True)
class MenuSpec:
    """A menu on Maya's menu bar: its Maya id, its layout file in TOOLS_PATH, and the plugin it needs, if any."""

    menu_id: str
    layout: str
    plugin: str | None = None


# build_menus builds a menu with a plugin only while that plugin is loaded, because every tool in it calls a
# RigModules command. The dev tools are in the bmaya menu, so they stay reachable after an unload.
MENUS = (
    MenuSpec(menu_id="bmaya_menu", layout="bmaya_menu.json"),
    MenuSpec(menu_id="rigmodules_menu", layout="rigmodules_menu.json", plugin="RigModules"),
)


def menu_layout_paths() -> dict[str, str]:
    """Each menu's layout file, by menu id."""
    return {spec.menu_id: os.path.join(TOOLS_PATH, spec.layout) for spec in MENUS}

# A RigModules.mll path, or the plugin name once RigModules.mod puts it on MAYA_PLUG_IN_PATH.
# Point it at a copy of the build: a loaded plugin locks the file, so the next build would fail.
RIGMODULES_PLUGIN = os.environ.get("RIGMODULES_PLUGIN", "RigModules")

IS_BATCH = cmds.about(batch=True)
