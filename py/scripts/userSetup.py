import os
from datetime import datetime

import maya.cmds as cmds
import maya.api.OpenMaya as om  
# NOTE there's a py2 om and old om is deprecated
import bmaya.core.log as log


def runDeferredSetup():
    print("Starting custom startup!")

    # Setup logger
    log.initLogger()

    # Setup log streaming

    # Setup local helper functions

    # Setup tools menu and hotkeys
    tools_registry = setupToolRegistry()
    setupToolViews(tools_registry)

    # Load required plugins

    log.info("Custom startup scripts complete!")


def setupLogStreaming():
    # 1. Clean, alphabetical timestamp (e.g., 20260607_123045)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 2. Use os.path.join for clean path expansion
    logs_filepath = os.path.expanduser(os.path.join("~", "Documents", "maya", "logs"))

    # Use os.makedirs (safer than mkdir if the parent folders don't exist yet)
    if not os.path.exists(logs_filepath):
        os.makedirs(logs_filepath)

    # Construct the full path
    log_file = os.path.normpath(os.path.join(logs_filepath, f"maya_logs_{timestamp}.txt"))

    try:
        # Initialize immediately (No executeDeferred) to catch early startup logs
        cmds.scriptEditorInfo(historyFilename=log_file, writeHistory=True)
        log.info(f"Session history is logging to: {log_file}")
    except Exception as e:
        log.erorr(f"[Pipeline Error] Failed to initialize early logging: {e}\n")

def setupToolRegistry():
    """Setup the master tool registry that all tool views read from"""
    from bmaya.core.tool_registry import ToolRegistry

    registry = ToolRegistry()  # TODO: make this a singleton
    # TODO: make this path an environment constant
    registry.load_registry(r"C:\Users\bmorgan\Documents\dev\maya\mayadev\toolsets\master_tool_registry.json")

    return registry

def setupToolViews(registry):
    from bmaya.maya.ui.tool_views.tool_menu import ToolMenu
    main_menu = ToolMenu("test")
    main_menu.load_layout(r"C:\Users\bmorgan\Documents\dev\maya\mayadev\toolsets\bmaya_menu.json")
    main_menu.build_ui(registry)

def userSetup():
    setupLogStreaming()
    # Run all deferred setup
    cmds.evalDeferred(runDeferredSetup, lowestPriority=True)

# The start of userSetup has to be deferred but now to lowest priority
cmds.evalDeferred(userSetup)