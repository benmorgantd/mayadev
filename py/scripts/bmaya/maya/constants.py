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
# Built only when RigModules loads, because every tool in it calls a RigModules command.
RIGMODULES_MENU_PATH = os.path.join(TOOLS_PATH, "rigmodules_menu.json")

# A RigModules.mll path, or the plugin name once RigModules.mod puts it on MAYA_PLUG_IN_PATH.
# Point it at a copy of the build: a loaded plugin locks the file, so the next build would fail.
RIGMODULES_PLUGIN = os.environ.get("RIGMODULES_PLUGIN", "RigModules")

IS_BATCH = cmds.about(batch=True)
