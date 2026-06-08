import os
from datetime import datetime
import maya.cmds as cmds
import maya.api.OpenMaya as om

# NOTE there's a py2 om and old om is deprecated

import bmaya.core.log as log

####################
# Immediate setups #
####################


def _initialize_logger():
    log.init_logger()


def _setup_script_editor_streaming():
    # 1. Clean, alphabetical timestamp (e.g., 20260607_123045)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 2. Use os.path.join for clean path expansion

    logs_filepath = os.path.expanduser(
        os.path.join("~", "Documents", "maya", "logs"))

    # Use os.makedirs (safer than mkdir if the parent folders don't exist yet)

    if not os.path.exists(logs_filepath):

        os.makedirs(logs_filepath)

    # Construct the full path

    log_file = os.path.normpath(

        os.path.join(logs_filepath, f"maya_logs_{timestamp}.txt")
    )

    try:
        # Initialize immediately (No executeDeferred) to catch early startup
        # logs

        cmds.scriptEditorInfo(historyFilename=log_file, writeHistory=True)

        log.info(f"Session history is logging to: {log_file}")

    except Exception as e:

        log.error(
            f"[Pipeline Error] Failed to initialize early logging: {e}\n")


###################
# Deferred setups #
###################


def _run_deferred_setup():
    # Setup logger
    log.info("Running deferred setup...")

    # Setup local helper functions

    # Setup tools menu and hotkeys
    tools_registry = _setup_tool_registry()
    _setup_tool_views(tools_registry)

    # Load required plugins
    log.info("Custom startup scripts complete!")


def _setup_tool_registry():
    """Setup the master tool registry that all tool views read from"""

    from bmaya.core.tool_registry import ToolRegistry
    import bmaya.maya.constants as maya_constants

    registry = ToolRegistry()  # TODO: make this a singleton

    # TODO: handle missing file case
    registry.load_registry(maya_constants.TOOL_REGISTRY_PATH)

    return registry


def _setup_tool_views(registry):

    from bmaya.maya.ui.tool_views.tool_menu import ToolMenu
    from bmaya.maya import constants as maya_constants

    main_menu = ToolMenu("test")
    main_menu.load_layout(os.path.join(
        maya_constants.TOOLS_PATH, 'bmaya_menu.json'))

    main_menu.build_ui(registry)


def run_user_setup():
    '''This is the main entry point for user setup. Call any necessary setup functions here.'''
    _initialize_logger()
    _setup_script_editor_streaming()

    # Run all deferred setup

    cmds.evalDeferred(_run_deferred_setup, lowestPriority=True)


# Run the userSetup function on startup
cmds.evalDeferred(run_user_setup)
