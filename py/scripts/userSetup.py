import os
from datetime import datetime
import maya.cmds as cmds
import bmaya.core.log as log

_IS_BATCH = cmds.about(batch=True)
# only needed here for visual consistency in print statements before the logger has been set up.
_print_prefix = '' if _IS_BATCH else '# '

if _IS_BATCH:
    # NOTE: for mayabatch processes we won't be able to get log streaming in this way. There is an arg.
    print(f"{_print_prefix}[bmaya][startup] This Maya instance is a batch process")


def _run_deferred_setup():
    print(f"{_print_prefix}[bmaya][startup] Starting custom startup")

    # Setup logger
    log.init_logger()

    # Setup log streaming

    # Setup local helper functions

    # Setup tools menu and hotkeys
    tools_registry = _setup_tool_registry()
    if not _IS_BATCH:
        _setup_tool_views(tools_registry)

    # Load required plugins

    log.info("Custom startup scripts complete!")


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


def _setup_tool_registry():
    """Setup the master tool registry that all tool views read from"""
    from bmaya.core.tool_registry import ToolRegistry
    from bmaya.maya import constants

    registry = ToolRegistry()  # TODO: make this a singleton
    registry.load_registry(constants.TOOL_REGISTRY_PATH)

    return registry


def _setup_tool_views(registry):
    from bmaya.maya.ui.tool_views.tool_menu import ToolMenu
    from bmaya.maya import constants

    main_menu = ToolMenu("test")
    main_menu.load_layout(os.path.join(constants.TOOLS_PATH, 'bmaya_menu.json'))
    main_menu.build_ui(registry)


def user_setup():
    if not _IS_BATCH:
        _setup_log_streaming()
    # Run all deferred setup
    cmds.evalDeferred(_run_deferred_setup, lowestPriority=True)


# The start of userSetup has to be deferred but now to lowest priority
cmds.evalDeferred(user_setup)
