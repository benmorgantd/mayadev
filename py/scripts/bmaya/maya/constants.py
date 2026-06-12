import os
import maya.cmds as cmds

if not os.environ.get("MAYADEV_ROOT"):
    raise EnvironmentError(
        "MAYADEV_ROOT environment variable not set in your Maya.env. "
        "Please set it to the root directory of the mayadev repository."
    )

MAYADEV_ROOT = os.environ["MAYADEV_ROOT"]

RIG_TEMPLATES_DIR = os.environ["RIG_TEMPLATES_DIR"]
RIGGING_PROJECT_DIR = os.environ["RIGGING_PROJECT_DIR"]

TOOLS_PATH = os.path.join(MAYADEV_ROOT, "toolsets")
TOOL_REGISTRY_PATH = os.path.join(TOOLS_PATH, "master_tool_registry.json")

# TODO: update references to these constants
POSTOPS_TEMPLATE = "import maya.cmds as cmds\n\ndef postOps():\n    log.info('Finished with post operations')\npostOps()"
REQUIRED_PLUGINS = ["matrixNodes", "quatNodes"]

IS_BATCH = cmds.about(batch=True)
