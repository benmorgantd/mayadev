"""The layer rules of bmaya, read from the source with ast (RigModules design/mayadev-ui.md, D49). Plain Python.

core > maya > maya_ui: a layer imports only layers to its left. Qt and Maya's UI commands stay in maya_ui. A slot
in a lower layer is filled only by a layer's startup.register(). Run with tests/core/run.bat, or:
python -m unittest discover -s tests/core -p "test_core_*.py"
"""

import ast
import os
import pathlib
import unittest

BMAYA = pathlib.Path(__file__).resolve().parents[2] / "py" / "scripts" / "bmaya"

# Python 2 files that don't parse under Python 3 (docs/status.md). A new file that doesn't parse fails the test.
KNOWN_PYTHON2 = {
    "maya/rigging/weights/skin/averageVertexSkinWeightCmd.py",
    "maya/rigging/weights/skin/bm_softCluster.py",
    "maya/rigging/weights/skin/cvshapeinverter.py",
}

QT_MODULES = ("PySide6", "shiboken6", "PySide2", "shiboken2")
# maya.cmds commands that open a dialog or build a window. Qt dialogs replace them everywhere (D49), and the Maya
# menus (cmds.menu, cmds.menuItem) and docking (cmds.workspaceControl) stay in maya_ui.
CMDS_DIALOGS = {"promptDialog", "confirmDialog", "layoutDialog", "fileDialog", "fileDialog2", "progressWindow"}
CMDS_UI = CMDS_DIALOGS | {
    "window", "showWindow", "button", "text", "textField", "scrollField", "checkBox", "optionMenu", "columnLayout",
    "rowLayout", "formLayout", "menu", "menuItem", "workspaceControl", "headsUpMessage", "inViewMessage",
}
SLOT_REGISTRATIONS = {"register_writers", "register_prompter", "register_hooks"}
STARTUP_FILES = {"maya/startup.py", "maya_ui/startup.py"}


def _sources():
    """(path relative to bmaya, parsed tree) for every .py file, and the files that don't parse."""
    trees, broken = {}, set()
    for path in sorted(BMAYA.rglob("*.py")):
        relative = path.relative_to(BMAYA).as_posix()
        try:
            trees[relative] = ast.parse(path.read_text(encoding="utf-8"), relative)
        except SyntaxError:
            broken.add(relative)
    return trees, broken


TREES, BROKEN = _sources()


def _module_name(relative):
    parts = ["bmaya", *relative[:-3].split("/")]
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imports(relative, tree):
    """Every module a file imports, anywhere in it, with relative imports resolved."""
    package = _module_name(relative).rsplit(".", 0 if relative.endswith("__init__.py") else 1)[0]
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[:len(base) - node.level + 1]
                module = ".".join(base + ([node.module] if node.module else []))
            else:
                module = node.module
            names.append(module)
            names += [f"{module}.{alias.name}" for alias in node.names]
    return names


def _starts_with(name, prefixes):
    return any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)


def _layer_files(layer):
    return {relative: tree for relative, tree in TREES.items() if relative.startswith(layer + "/")}


def _cmds_calls(tree):
    """The maya.cmds functions a file calls as cmds.<name>(...)."""
    return {node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "cmds"}


class Layers(unittest.TestCase):

    def test_every_file_parses_except_the_known_python2_files(self):
        self.assertEqual(BROKEN, KNOWN_PYTHON2)

    def assert_imports_none(self, layer, forbidden):
        found = []
        for relative, tree in _layer_files(layer).items():
            found += [f"{relative}: {name}" for name in _imports(relative, tree) if _starts_with(name, forbidden)]
        self.assertEqual(found, [], f"{layer} imports what it must not")

    def test_core_is_plain_python(self):
        self.assert_imports_none("core", ("maya", "rigmodules", "bmaya.maya", "bmaya.maya_ui") + QT_MODULES)

    def test_maya_imports_no_ui(self):
        self.assert_imports_none("maya", ("bmaya.maya_ui",) + QT_MODULES)

    def test_no_maya_ui_commands_outside_maya_ui(self):
        found = [f"{relative}: cmds.{name}" for relative, tree in TREES.items() if not relative.startswith("maya_ui/")
                 for name in sorted(_cmds_calls(tree) & CMDS_UI)]
        self.assertEqual(found, [])

    def test_no_maya_dialogs_anywhere(self):
        found = [f"{relative}: cmds.{name}" for relative, tree in TREES.items()
                 for name in sorted(_cmds_calls(tree) & CMDS_DIALOGS)]
        self.assertEqual(found, [])

    def test_slots_are_filled_only_by_a_startup_register(self):
        found = []
        for relative, tree in TREES.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                    if name in SLOT_REGISTRATIONS and relative not in STARTUP_FILES:
                        found.append(f"{relative}:{node.lineno}: {name}")
        self.assertEqual(found, [])

    def test_the_layer_helpers_see_what_they_check(self):
        """A guard on the checks above: they would pass on nothing if the walk found no files."""
        self.assertIn("bmaya.core.log", _imports("maya/startup.py", TREES["maya/startup.py"]))
        self.assertIn("bmaya.core.log", _imports("core/progressmanager.py", TREES["core/progressmanager.py"]))
        self.assertIn("menu", _cmds_calls(TREES["maya_ui/tool_views/tool_menu.py"]))
        self.assertGreater(len(_layer_files("core")), 10)
        self.assertTrue(os.path.isdir(BMAYA))


if __name__ == "__main__":
    unittest.main()
