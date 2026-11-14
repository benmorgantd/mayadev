import os
from datetime import datetime
import maya.cmds as cmds
import bmaya.core.log as log
from bmaya.core import progressmanager

_IS_BATCH = cmds.about(batch=True)
# only needed here for visual consistency in print statements before the logger has been set up.
_print_prefix = "" if _IS_BATCH else "# "

if _IS_BATCH:
    # NOTE: for mayabatch processes we won't be able to get log streaming in this way. There is an arg.
    print(f"{_print_prefix}[bmaya][startup] This Maya instance is a batch process")

if not _IS_BATCH:
    # ui-related imports
    from bmaya.maya_ui.qtbase import ProgressWindow


def _run_deferred_setup():
    print(f"{_print_prefix}[bmaya][startup] Starting custom startup")

    # Setup logger
    log.init_logger()

    # Start progress window
    pmanager.start("Running Deferred Startup")

    if not _IS_BATCH:
        ProgressWindow().show()

    pmanager.update(10, "Set up log streaming")

    # Setup local helper functions

    # Load required plugins before the menus, which skip the RigModules menu without it
    rigmodules_loaded = _load_rigmodules()

    # Only setup the menus if we're not in batch mode
    if not _IS_BATCH:
        _setup_tool_menus()

    # The RigModules menu tools act on the active rig, so they need the tracker's selection callbacks
    if rigmodules_loaded and not _IS_BATCH:
        _start_active_rig_tracker()

    log.info("Custom startup scripts complete!")

    pmanager.end()


def _setup_log_streaming():
    # 1. Clean, alphabetical timestamp (e.g., 20260607_123045)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 2. Use os.path.join for clean path expansion
    logs_filepath = os.path.expanduser(os.path.join("~", "Documents", "maya", "logs"))

    # Use os.makedirs (safer than mkdir if the parent folders don't exist yet)
    if not os.path.exists(logs_filepath):
        os.makedirs(logs_filepath)

    # Construct the full path
    log_file = os.path.normpath(
        os.path.join(logs_filepath, f"maya_logs_{timestamp}.txt")
    )

    try:
        # Initialize immediately (No executeDeferred) to catch early startup logs
        cmds.scriptEditorInfo(historyFilename=log_file, writeHistory=True)
        log.info(f"Session history is logging to: {log_file}")
    except Exception as e:
        log.error(f"[Pipeline Error] Failed to initialize early logging: {e}\n")


def _start_active_rig_tracker():
    """Follows the rig the RigModules menu tools act on, through selection and file new and open callbacks."""
    import bmaya.maya.activerig

    pmanager.update(70, "Tracking the active rig")
    bmaya.maya.activerig.ActiveRigTracker()


def _load_rigmodules():
    """Loads the RigModules plugin. Returns False, with a warning, when it can't be loaded."""
    from bmaya.maya import constants

    pmanager.update(20, "Loading RigModules")

    try:
        cmds.loadPlugin(constants.RIGMODULES_PLUGIN, quiet=True)
    except RuntimeError as e:
        log.warning(f"RigModules not loaded from '{constants.RIGMODULES_PLUGIN}', so its menu is skipped: {e}")
        return False
    return True


def _setup_tool_menus():
    """Builds every menu from the tool registry and layout files. A broken file is logged and the menus are skipped,
    so the plugin and the active rig tracker still start."""
    from bmaya.core.tool_registry import ToolDataError
    from bmaya.maya_ui.tool_views.tool_menu import build_menus

    pmanager.update(50, "Building tool menus")

    try:
        build_menus()
    except (FileNotFoundError, ToolDataError) as e:
        log.error(f"The tool menus were not built:\n{e}")


def user_setup():
    if not _IS_BATCH:
        _setup_log_streaming()

    # Run all deferred setup
    cmds.evalDeferred(_run_deferred_setup, lowestPriority=True)


# Convenience imports
from importlib import reload

pmanager = progressmanager.ProgressManager()

with pmanager:
    # The start of userSetup has to be deferred but now to lowest priority
    cmds.evalDeferred(user_setup)
