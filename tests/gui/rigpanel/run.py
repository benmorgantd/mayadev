"""Runs check.py, the active rig panel docked in a GUI Maya, and reports its log. A manual check: it opens Maya.

Needs RIGMODULES_PLUGIN (a RigModules.mll, copied here so a build isn't locked) and RIGMODULES_PYTHON (RigModules'
python folder, which holds rigmodules and mayalaunch). Exits 1 on a failed check, an exception, or a Maya that
never finished.
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MAYADEV = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TIMEOUT = 240
TEMPLATE = {
    "rigVersion": 1, "rigTemplateName": "PanelGui", "rigName": "game", "rigAuthor": "tests",
    "rigModules": [
        {"moduleType": "FkChain", "name": "spine", "shapeType": "Box",
         "moduleArgs": {"joints": [["Center", "spine1"], ["Center", "spine2"]]}},
        {"moduleType": "FkChain", "name": "arm_l", "side": "Left", "shapeType": "Circle", "mirror": True,
         "moduleArgs": {"joints": [["Left", "arm"]]}, "parentStructure": {"start": "spine.end"}},
    ],
}


def main() -> int:
    plugin = os.environ.get("RIGMODULES_PLUGIN", "")
    python_folder = os.environ.get("RIGMODULES_PYTHON", "")
    if not os.path.isfile(plugin) or not os.path.isdir(python_folder):
        print("Set RIGMODULES_PLUGIN to a RigModules.mll and RIGMODULES_PYTHON to RigModules' python folder.")
        return 2
    sys.path.insert(0, python_folder)
    import mayalaunch.gui
    import mayalaunch.process

    work = tempfile.mkdtemp(prefix="panel_gui_")
    try:
        template = os.path.join(work, "template.json")
        with open(template, "w", encoding="utf-8") as handle:
            json.dump(TEMPLATE, handle)
        plugin_copy = os.path.join(work, "RigModules.mll")
        shutil.copy(plugin, plugin_copy)
        log = os.path.join(work, "check.log")
        env = mayalaunch.process.child_environment(extra={
            "PANEL_LOG": log,
            "PANEL_PLUGIN": plugin_copy.replace("\\", "/"),
            "PANEL_TEMPLATE": template.replace("\\", "/"),
            "PYTHONPATH": os.pathsep.join([os.path.join(MAYADEV, "py", "scripts"), python_folder]),
        })
        result = mayalaunch.gui.run_gui(os.path.join(HERE, "check.py"), env=env, timeout=TIMEOUT)
        text = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
        print(text or "no log: Maya did not run the script")
        failed = "FAIL" in text or "EXCEPTION" in text or "finished" not in text or not result.ok
        print("FAILED" if failed else "OK", f"(exit {result.exit_code}, timed out {result.timed_out})")
        return 1 if failed else 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
