"""Runs check.py, the library browser docked in a GUI Maya, and reports its log. A manual check: it opens Maya.

Needs RIGMODULES_PLUGIN (a RigModules.mll, copied here so a build isn't locked) and RIGMODULES_PYTHON (RigModules'
python folder, which holds rigmodules and mayalaunch). The projects root, the local versions folder and the template
are made in a temporary folder. Exits 1 on a failed check, an exception, or a Maya that never finished.
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
    "rigVersion": 1, "rigTemplateName": "LibraryGui", "rigName": "game", "rigAuthor": "tests",
    "rigModules": [
        {"moduleType": "FkChain", "name": "spine_00_M_MOD", "shapeType": "Box",
         "moduleArgs": {"joints": [["Center", "spine1"], ["Center", "spine2"]]}},
        {"moduleType": "FkChain", "name": "arm_00_L_MOD", "side": "Left", "shapeType": "Circle", "mirror": True,
         "moduleArgs": {"joints": [["Left", "arm"]]}, "parentStructure": {"start": "spine_00_M_MOD.end"}},
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

    work = tempfile.mkdtemp(prefix="library_gui_")
    try:
        template = os.path.join(work, "template.json")
        with open(template, "w", encoding="utf-8") as handle:
            json.dump(TEMPLATE, handle)
        plugin_copy = os.path.join(work, "RigModules.mll")
        shutil.copy(plugin, plugin_copy)
        log = os.path.join(work, "check.log")
        env = mayalaunch.process.child_environment(extra={
            "LIBRARY_LOG": log,
            "LIBRARY_PLUGIN": plugin_copy.replace("\\", "/"),
            "LIBRARY_TEMPLATE": template.replace("\\", "/"),
            "RIGGING_PROJECT_DIR": os.path.join(work, "projects"),
            "BMAYA_VERSIONS_DIR": os.path.join(work, "local_versions"),
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
