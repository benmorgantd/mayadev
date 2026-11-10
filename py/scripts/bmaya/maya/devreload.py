"""Dev reload and unload for the RigModules plugin: swaps in a fresh build, or removes it, without restarting Maya.

A loaded .mll is locked, so the build output can't be rebuilt while Maya has it loaded. Reload tears down
everything tied to the plugin (the active rig tracker, the RigModules menu), starts a new scene, unloads the
plugin, loads a copy of the build from a temp folder, and puts the tracker and menu back. The build is
RIGMODULES_PLUGIN from Maya.env, which must be a path to the .mll. Startup loads that path directly, so the file
stays locked until the first reload. Development only: the scene is thrown away.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time

import maya.cmds as cmds

import bmaya.core.log
import bmaya.maya.activerig
import bmaya.maya.constants

PLUGIN_FILE = "RigModules.mll"
MENU_ID = "rigmodules_menu"
_COPY_ROOT = os.path.join(tempfile.gettempdir(), "rigmodules_dev")


def _delete_menu() -> None:
    if cmds.menu(MENU_ID, exists=True):
        cmds.deleteUI(MENU_ID, menu=True)


def _tear_down() -> None:
    """Everything that holds the plugin: callbacks, the menu, nodes, undo entries and cached viewport items."""
    tracker = bmaya.maya.activerig.ActiveRigTracker.current()
    if tracker is not None:
        tracker.stop()
    _delete_menu()

    cmds.select(clear=True)
    cmds.file(new=True, force=True)
    cmds.flushUndo()  # undo entries keep C++ node references alive
    cmds.refresh()  # VP2 caches render items for the control nodes
    if cmds.pluginInfo(PLUGIN_FILE, query=True, loaded=True):
        cmds.unloadPlugin(PLUGIN_FILE)


def _copy_build(build_path: str) -> str:
    """Copies the build to a new folder, so the original is never locked. Folders of earlier reloads are removed
    when Maya has let go of them."""
    shutil.rmtree(_COPY_ROOT, ignore_errors=True)
    folder = os.path.join(_COPY_ROOT, time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(folder, exist_ok=True)
    return shutil.copy2(build_path, os.path.join(folder, PLUGIN_FILE))


def _forget_python_package() -> None:
    """Drops rigmodules from the import cache, so the next import reads the python/ folder again."""
    for name in [m for m in sys.modules if m == "rigmodules" or m.startswith("rigmodules.")]:
        del sys.modules[name]


def _build_menu() -> None:
    from bmaya.core.tool_registry import ToolRegistry
    from bmaya.maya_ui.tool_views.tool_menu import ToolMenu

    registry = ToolRegistry()
    registry.load_registry(bmaya.maya.constants.TOOL_REGISTRY_PATH)
    menu = ToolMenu(MENU_ID)
    menu.load_layout(bmaya.maya.constants.RIGMODULES_MENU_PATH)
    menu.build_ui(registry)


def reload_rigmodules() -> None:
    """Reloads the plugin from RIGMODULES_BUILD. Runs deferred, so a menu item can start it: the menu is deleted
    while the item's own callback would still be on the stack otherwise."""
    build_path = bmaya.maya.constants.RIGMODULES_PLUGIN
    if not os.path.isfile(build_path):
        raise RuntimeError(
            "Set RIGMODULES_PLUGIN in Maya.env to the built RigModules.mll "
            f"(RigModules/cpp/x64/Release/RigModules.mll). It is '{build_path}'."
        )
    cmds.evalDeferred(lambda: _reload(build_path))


def unload_rigmodules() -> None:
    """Unloads the plugin and leaves Maya without it, so the build output is unlocked for a rebuild. The menu is
    rebuilt afterwards, so Reload is still there to bring the plugin back. Deferred for the same reason as the full
    reload."""
    cmds.evalDeferred(_unload)


def reload_menu() -> None:
    """Deletes the RigModules menu and builds it again from the layout and registry files, so edits to them show
    without a restart. The plugin and the scene are untouched. Deferred for the same reason as the full reload."""
    cmds.evalDeferred(_reload_menu)


def _reload_menu() -> None:
    _delete_menu()
    _build_menu()
    bmaya.core.log.info("Reloaded the RigModules menu")


def _unload() -> None:
    _tear_down()
    _forget_python_package()
    _build_menu()
    bmaya.core.log.info("Unloaded RigModules")


def _reload(build_path: str) -> None:
    _tear_down()
    _forget_python_package()
    plugin_path = _copy_build(build_path)
    try:
        cmds.loadPlugin(plugin_path, quiet=True)
    except RuntimeError as e:
        bmaya.core.log.error(f"RigModules was unloaded but the new build did not load: {e}")
        return

    bmaya.maya.activerig.ActiveRigTracker()
    _build_menu()
    bmaya.core.log.info(f"Reloaded RigModules from {build_path}")
