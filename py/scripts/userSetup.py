import os
from datetime import datetime

import maya.cmds as cmds
import maya.api.OpenMaya as om  
# NOTE there's a py2 om and old om is deprecated
import bmaya.core.log as log


def runDeferredSetup():
    print("Starting custom startup!")

    # Setup logger
    log.init_logger()

    # Setup log streaming

    # Setup local helper functions

    # Setup tools menu and hotkeys

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

def userSetup():
    setupLogStreaming()
    # Run all deferred setup
    cmds.evalDeferred(runDeferredSetup, lowestPriority=True)

# The start of userSetup has to be deferred but now to lowest priority
cmds.evalDeferred(userSetup)