"""Dev reload and unload for the RigModules plugin: swaps in a fresh build, or removes it, without restarting Maya.

A loaded .mll is locked, so the build output can't be rebuilt while Maya has it loaded. Reload tears down
everything tied to the plugin (the active rig tracker, the menus that need it), starts a new scene, unloads the
plugin, loads a copy of the build from a temp folder, and puts the tracker and menu back. The build is
RIGMODULES_PLUGIN from Maya.env, which must be a path to the .mll. Startup loads that path directly, so the file
stays locked until the first reload. Development only: the scene is thrown away.

The menus are UI, so this module doesn't build them. A GUI session registers hooks (register_hooks, called from
bmaya.maya_ui.startup) that run before the plugin unloads and after it loads. Without them (mayapy) nothing runs.
"""

from __future__ import annotations

import dataclasses
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable

import maya.cmds as cmds

import bmaya.core.log
import bmaya.maya.activerig
import bmaya.maya.constants

PLUGIN_FILE = "RigModules.mll"
_COPY_ROOT = os.path.join(tempfile.gettempdir(), "rigmodules_dev")


def _do_nothing() -> None:
    pass


@dataclasses.dataclass(frozen=True)
class ReloadHooks:
    """What a reload runs around the plugin: before_unload while the plugin is still loaded, after_load once the
    new build is in (or, after an unload, once the plugin is gone)."""

    before_unload: Callable[[], None] = _do_nothing
    after_load: Callable[[], None] = _do_nothing


_hooks = ReloadHooks()


def register_hooks(before_unload: Callable[[], None], after_load: Callable[[], None]) -> None:
    """Fills the reload hooks slot. Replaces the hooks registered before. Called only from a layer's
    startup.register()."""
    global _hooks
    _hooks = ReloadHooks(before_unload, after_load)


def reset_hooks() -> None:
    """Puts the default back: no hooks."""
    global _hooks
    _hooks = ReloadHooks()


def _tear_down() -> None:
    """Everything that holds the plugin: callbacks, the menu, nodes, undo entries and cached viewport items."""
    tracker = bmaya.maya.activerig.ActiveRigTracker.current()
    if tracker is not None:
        tracker.stop()
    _hooks.before_unload()

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
    """Unloads the plugin and leaves Maya without it, so the build output is unlocked for a rebuild. The RigModules
    menu goes with the plugin, and Reload, in the bmaya menu, brings it back. Deferred for the same reason as the
    full reload."""
    cmds.evalDeferred(_unload)


def _unload() -> None:
    _tear_down()
    _forget_python_package()
    _hooks.after_load()
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
    _hooks.after_load()
    bmaya.core.log.info(f"Reloaded RigModules from {build_path}")
