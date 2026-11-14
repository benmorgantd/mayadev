"""The Tool Registry Editor and the Tool Menu Editor, offscreen in mayapy: the tree to Layout round trip, the
call picker and argument form, the status line and the checked save. No plugin is needed.

Run with tests/core/run.bat (the Maya half), or: mayapy -m unittest discover -s tests/core -p "test_maya_*.py"
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

try:
    import maya.standalone
except ImportError:
    maya = None

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "toolsets")


class EditorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if maya is None:
            raise unittest.SkipTest("needs mayapy")
        # The QApplication comes first: standalone Maya otherwise starts a QCoreApplication, which can't host
        # widgets, and creating one then aborts the process.
        from PySide6 import QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        maya.standalone.initialize(name="python")

    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix="bmaya_editors_")
        self.addCleanup(shutil.rmtree, self.temp, True)
        # An editor must never show a dialog in a test: any message box is a failure.
        from PySide6 import QtWidgets
        for name in ("warning", "critical", "question", "information"):
            patcher = mock.patch.object(QtWidgets.QMessageBox, name, side_effect=AssertionError(f"unexpected QMessageBox.{name}"))
            patcher.start()
            self.addCleanup(patcher.stop)


class MenuEditor(EditorTest):

    def editor(self):
        import bmaya.maya_ui.tool_views.tool_menu as tool_menu
        with mock.patch.object(tool_menu, "get_maya_main_window", return_value=None):
            return tool_menu.ToolMenuEditorWindow(parent=None)

    def test_a_layout_round_trips_through_the_tree(self):
        from bmaya.core import tool_registry as tr
        window = self.editor()
        layout = tr.Layout("Round Trip", [
            tr.ToolItem("bmaya.joints.zero_transforms", enabled=False),
            tr.Submenu("S", [tr.ToolItem("bmaya.joints.orient_to_world"), tr.Separator(), tr.Submenu("T", [])]),
            tr.Separator(),
        ])
        window.set_layout(layout)
        self.assertEqual(window.get_layout(), layout)

    def test_a_tool_row_is_checkable_and_the_check_is_enabled(self):
        from PySide6 import QtCore
        from bmaya.core import tool_registry as tr
        window = self.editor()
        window.set_layout(tr.Layout("L", [tr.ToolItem("bmaya.joints.zero_transforms")]))
        row = window.hierarchy_tree.topLevelItem(0)
        self.assertTrue(row.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        self.assertEqual(row.toolTip(0), "bmaya.joints.zero_transforms")
        row.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
        self.assertFalse(window.get_layout().items[0].enabled)

    def test_every_repo_layout_loads_and_saves_unchanged_through_the_editor(self):
        from bmaya.core import tool_registry as tr
        window = self.editor()
        for name in ("bmaya_menu.json", "rigmodules_menu.json"):
            with self.subTest(name):
                layout = tr.read_layout(os.path.join(TOOLS, name), window.registry.tools)
                window.set_layout(layout)
                self.assertEqual(window.get_layout(), layout)

    def test_insert_goes_inside_a_selected_submenu_after_a_selected_tool_else_at_the_end(self):
        from bmaya.core import tool_registry as tr
        window = self.editor()
        window.set_layout(tr.Layout("L", [
            tr.Submenu("S", [tr.ToolItem("bmaya.joints.zero_transforms")]),
            tr.ToolItem("bmaya.joints.orient_to_world"),
        ]))
        tree = window.hierarchy_tree

        tree.setCurrentItem(tree.topLevelItem(0))                       # the submenu: inside, at the end
        window._insert_node(window._tool_node("bmaya.joints.orient_to_mesh"))
        self.assertEqual([i.tool for i in window.get_layout().items[0].items],
                         ["bmaya.joints.zero_transforms", "bmaya.joints.orient_to_mesh"])

        tree.setCurrentItem(tree.topLevelItem(0).child(0))              # a tool in a submenu: after it
        window._insert_node(window._create_tree_node("separator", "-"))
        self.assertIsInstance(window.get_layout().items[0].items[1], tr.Separator)

        tree.setCurrentItem(tree.topLevelItem(1))                       # a top-level tool: after it
        window._insert_node(window._create_tree_node("separator", "-"))
        self.assertIsInstance(window.get_layout().items[2], tr.Separator)

        tree.clearSelection()                                           # nothing selected: the end
        tree.setCurrentItem(None)
        window._insert_node(window._create_tree_node("separator", "-"))
        self.assertEqual(len(window.get_layout().items), 4)

    def test_save_refuses_a_layout_with_a_tool_missing_from_the_registry_and_writes_nothing(self):
        from bmaya.core import tool_registry as tr
        window = self.editor()
        window.set_layout(tr.Layout("L", [tr.ToolItem("no.such.tool")]))
        window.current_layout_path = os.path.join(self.temp, "l.json")
        from PySide6 import QtWidgets
        with mock.patch.object(QtWidgets.QMessageBox, "critical") as critical:
            window._on_save_layout()
        critical.assert_called_once()
        self.assertIn("tool 'no.such.tool' is not in the registry", critical.call_args[0][2])
        self.assertEqual(os.listdir(self.temp), [])

    def test_save_writes_the_tree_and_open_reads_it_back(self):
        from bmaya.core import tool_registry as tr
        window = self.editor()
        layout = tr.Layout("Saved", [tr.ToolItem("bmaya.joints.zero_transforms", enabled=False), tr.Separator()])
        window.set_layout(layout)
        window.current_layout_path = os.path.join(self.temp, "l.json")
        window._on_save_layout()
        self.assertEqual(tr.read_layout(window.current_layout_path, window.registry.tools), layout)

    def test_a_layout_that_fails_its_check_is_refused_on_open_and_the_tree_is_kept(self):
        from PySide6 import QtWidgets
        from bmaya.core import tool_registry as tr
        window = self.editor()
        window.set_layout(tr.Layout("Keep", [tr.Separator()]))
        bad = os.path.join(self.temp, "bad.json")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write('{"version": 2, "label": "x", "items": [{"type": "tool", "tool": "no.such"}, {"type": "bogus"}]}')
        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=(bad, "")), \
                mock.patch.object(QtWidgets.QMessageBox, "critical") as critical:
            window._on_open_layout()
        message = critical.call_args[0][2]
        self.assertIn("no.such", message)
        self.assertIn("bogus", message)  # every problem, not the first
        self.assertEqual(window.get_layout().label, "Keep")


class RegistryEditor(EditorTest):

    def editor(self, path=None):
        import bmaya.maya_ui.tool_registry_editor as editor
        with mock.patch.object(editor, "get_maya_main_window", return_value=None):
            window = editor.ToolManagerWindow(parent=None)
        if path:
            window._load_registry(path)
        return window

    def select(self, window, tool_id):
        from PySide6 import QtCore
        for i in range(window.tool_list.count()):
            item = window.tool_list.item(i)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == tool_id:
                window.tool_list.setCurrentItem(item)
                return
        self.fail(tool_id)

    def test_every_repo_tool_shows_status_ok_and_can_run(self):
        window = self.editor()
        for tool_id in list(window.registry.tools):
            with self.subTest(tool_id):
                self.select(window, tool_id)
                self.assertEqual(window.label_status.text(), "OK", window.label_status.text())
                self.assertTrue(window.btn_execute.isEnabled())

    def test_the_function_drop_down_is_as_wide_as_its_longest_function_name(self):
        window = self.editor()
        combo = window.combo_function
        self.select(window, "rigmodules.pose.flip")        # bmaya.maya.posetools
        posetools_width = combo.minimumWidth()
        longest = max(combo.itemText(i) for i in range(combo.count()))
        self.assertGreaterEqual(posetools_width, combo.fontMetrics().horizontalAdvance(longest))

        self.select(window, "bmaya.dev.reload_menu")       # bmaya.maya.devreload: shorter names
        self.assertLess(combo.minimumWidth(), posetools_width)  # it shrinks again, not only grows

    def test_the_call_picker_shows_the_saved_call_and_kwargs(self):
        window = self.editor()
        self.select(window, "rigmodules.pose.mirror_left_to_right")
        self.assertEqual(window.input_id.text(), "rigmodules.pose.mirror_left_to_right")
        self.assertTrue(window.input_id.isReadOnly())
        self.assertEqual(window.input_module.text(), "bmaya.maya.posetools")
        self.assertEqual(window.combo_function.currentText(), "mirror_pose_ui")
        self.assertIn("Mirrors the pose", window.label_doc.text())
        self.assertEqual(window.argument_form.kwargs(), {"left_to_right": True})
        functions = [window.combo_function.itemText(i) for i in range(window.combo_function.count())]
        self.assertIn("flip_pose_ui", functions)
        self.assertNotIn("get_scope_x", functions)

    def test_an_unset_argument_is_not_saved_and_a_set_one_is(self):
        window = self.editor()
        self.select(window, "rigmodules.pose.mirror")
        self.assertEqual(window.argument_form.kwargs(), {})
        row = window.argument_form._rows[0]
        self.assertEqual(row.name, "left_to_right")
        self.assertFalse(row.is_set)
        self.assertFalse(row.widget.isEnabled())   # greyed: the default shows, and it isn't saved

        row.set_check.setChecked(True)
        row.widget.setChecked(False)
        self.assertEqual(window.registry.tools["rigmodules.pose.mirror"].call.kwargs, {"left_to_right": False})
        self.assertTrue(window.dirty)

        row.set_check.setChecked(False)
        self.assertEqual(window.registry.tools["rigmodules.pose.mirror"].call.kwargs, {})

    def test_a_required_argument_is_always_set(self):
        import bmaya.maya_ui.tool_registry_editor as editor
        form = editor.ArgumentForm()

        def function(count: int, label: str = "x"):
            return count, label

        form.set_function(function, {})
        rows = {row.name: row for row in form._rows}
        self.assertTrue(rows["count"].is_set)
        self.assertFalse(rows["count"].set_check.isEnabled())
        self.assertFalse(rows["label"].is_set)
        self.assertEqual(form.kwargs(), {"count": 0})

    def test_widgets_follow_the_annotation(self):
        from typing import Literal
        from PySide6 import QtWidgets
        import bmaya.maya_ui.tool_registry_editor as editor
        form = editor.ArgumentForm()

        def function(a: bool, b: int, c: float, d: str, e: Literal["x", "y"], f: int | None = None, g=None, h: list = None):
            pass

        form.set_function(function, {"e": "y", "f": 4, "h": [1, 2]})
        widgets = {row.name: type(row.widget) for row in form._rows}
        self.assertEqual(widgets, {
            "a": QtWidgets.QCheckBox, "b": QtWidgets.QSpinBox, "c": QtWidgets.QDoubleSpinBox, "d": QtWidgets.QLineEdit,
            "e": QtWidgets.QComboBox, "f": QtWidgets.QSpinBox, "g": QtWidgets.QLineEdit, "h": QtWidgets.QLineEdit,
        })
        values = form.kwargs()
        self.assertEqual((values["e"], values["f"], values["h"]), ("y", 4, [1, 2]))

    def test_json_text_that_is_not_json_is_reported_and_not_saved(self):
        window = self.editor()
        import bmaya.maya_ui.tool_registry_editor as editor
        self.select(window, "rigmodules.pose.mirror")
        form = window.argument_form

        def function(items=None):
            pass

        form.set_function(function, {})
        row = form._rows[0]
        row.set_check.setChecked(True)
        row.widget.setText("[1,")
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            form.kwargs()

    def test_a_saved_kwarg_the_function_no_longer_has_is_a_stale_row_that_can_be_removed(self):
        import bmaya.maya_ui.tool_registry_editor as editor
        form = editor.ArgumentForm()

        def function(kept: bool = False):
            pass

        form.set_function(function, {"kept": True, "gone": 1})
        self.assertEqual(form.kwargs(), {"kept": True, "gone": 1})
        self.assertEqual(form._stale, {"gone": 1})
        form._remove_stale("gone", form._layout.itemAt(3).widget(), form._layout.itemAt(4).widget())
        self.assertEqual(form.kwargs(), {"kept": True})

    def test_the_status_shows_the_first_call_problem_and_run_waits_for_ok(self):
        window = self.editor()
        self.select(window, "rigmodules.pose.flip")
        window.input_module.setText("bmaya.maya.no_such_module")
        window.input_module.editingFinished.emit()
        self.assertIn("cannot import module 'bmaya.maya.no_such_module'", window.label_status.text())
        self.assertFalse(window.btn_execute.isEnabled())

    def test_run_calls_the_tool_as_edited(self):
        import bmaya.core.tool_registry as tr
        window = self.editor()
        self.select(window, "rigmodules.pose.flip")
        with mock.patch.object(tr, "run_tool") as run:
            window._on_execute_payload()
        run.assert_called_once_with(window.registry.tools["rigmodules.pose.flip"])

    def test_new_tool_asks_for_a_checked_id_and_starts_with_an_empty_call(self):
        import bmaya.maya_ui.tool_registry_editor as editor
        from PySide6 import QtWidgets
        dialog = editor.NewToolDialog(["a.b.c"])
        ok = dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        for text, valid in (("", False), ("Bad Id", False), ("a.b.c", False), ("a.b.d", False)):
            dialog.input_id.setText(text)
            self.assertEqual(ok.isEnabled(), valid, text)
        self.assertIn("lowercase", self.problem_for(dialog, "Bad Id"))
        self.assertIn("already used", self.problem_for(dialog, "a.b.c"))
        dialog.input_id.setText("a.b.d")
        dialog.input_name.setText("New One")
        self.assertTrue(ok.isEnabled())
        self.assertEqual(dialog.values(), ("a.b.d", "New One"))

        window = self.editor()
        with mock.patch.object(editor.NewToolDialog, "exec", return_value=QtWidgets.QDialog.DialogCode.Accepted), \
                mock.patch.object(editor.NewToolDialog, "values", return_value=("a.b.d", "New One")):
            window._on_add_new_tool()
        tool = window.registry.tools["a.b.d"]
        self.assertEqual((tool.name, tool.short_name, tool.call.module, tool.call.function), ("New One", "New One", "", ""))

    @staticmethod
    def problem_for(dialog, text):
        dialog.input_id.setText(text)
        return dialog.problem.text()

    def test_save_refuses_an_unfinished_tool_with_the_full_report_and_writes_nothing(self):
        import bmaya.core.tool_registry as tr
        from PySide6 import QtWidgets
        path = os.path.join(self.temp, "r.json")
        shutil.copy(os.path.join(TOOLS, "master_tool_registry.json"), path)
        window = self.editor(path)
        window.registry.tools["a.b.d"] = tr.Tool("a.b.d", "New", "New", tr.ToolCall("", ""))
        with open(path, "rb") as handle:
            before = handle.read()
        with mock.patch.object(QtWidgets.QMessageBox, "critical") as critical:
            window._on_save_registry()
        critical.assert_called_once()
        self.assertIn("'module' must be a non-empty string", critical.call_args[0][2])
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), before)

    def test_save_reports_a_kwarg_that_does_not_bind_even_though_the_structure_is_valid(self):
        from PySide6 import QtWidgets
        path = os.path.join(self.temp, "r.json")
        shutil.copy(os.path.join(TOOLS, "master_tool_registry.json"), path)
        window = self.editor(path)
        window.registry.tools["rigmodules.pose.flip"].call.kwargs = {"nope": 1}
        with mock.patch.object(QtWidgets.QMessageBox, "critical") as critical:
            window._on_save_registry()
        self.assertIn("kwarg 'nope' is not a parameter", critical.call_args[0][2])

    def test_save_of_the_master_registry_refuses_to_delete_a_tool_a_layout_uses(self):
        import bmaya.maya.constants
        from PySide6 import QtWidgets
        window = self.editor()
        window.registry.tools.pop("bmaya.joints.zero_transforms")
        window.current_filepath = bmaya.maya.constants.TOOL_REGISTRY_PATH
        with mock.patch.object(QtWidgets.QMessageBox, "critical") as critical, \
                mock.patch("bmaya.core.tool_registry.write_registry") as write:
            window._on_save_registry()
        write.assert_not_called()
        message = critical.call_args[0][2]
        self.assertIn("bmaya_menu.json", message)
        self.assertIn("tool 'bmaya.joints.zero_transforms' is not in the registry", message)

    def test_save_writes_a_valid_registry_and_clears_the_unsaved_flag(self):
        import bmaya.core.tool_registry as tr
        path = os.path.join(self.temp, "r.json")
        shutil.copy(os.path.join(TOOLS, "master_tool_registry.json"), path)
        window = self.editor(path)
        self.select(window, "rigmodules.pose.flip")
        window.input_name.setText("Flip It")
        self.assertTrue(window.dirty)
        window._on_save_registry()
        self.assertFalse(window.dirty)
        self.assertEqual(tr.read_registry(path).tools["rigmodules.pose.flip"].name, "Flip It")
        self.assertEqual(os.listdir(self.temp), ["r.json"])

    def test_opening_a_registry_replaces_the_loaded_one_and_asks_first_when_there_are_unsaved_edits(self):
        import bmaya.core.tool_registry as tr
        from PySide6 import QtWidgets
        other = os.path.join(self.temp, "other.json")
        tr.write_registry(tr.Registry({"x.y.z": tr.Tool("x.y.z", "Only", "Only", tr.ToolCall("os.path", "join"))}), other)
        window = self.editor()
        self.assertGreater(len(window.registry.tools), 1)

        window._load_registry(other)
        self.assertEqual(list(window.registry.tools), ["x.y.z"])   # replaced, not merged with the 47 tools

        window.dirty = True
        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=(other, "")), \
                mock.patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.StandardButton.Cancel) as ask, \
                mock.patch.object(window, "_load_registry") as load:
            window._on_open_registry()
        ask.assert_called_once()
        load.assert_not_called()

    def test_a_registry_that_fails_its_check_is_refused_and_the_loaded_one_stays(self):
        from PySide6 import QtWidgets
        window = self.editor()
        count = len(window.registry.tools)
        bad = os.path.join(self.temp, "bad.json")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write('{"version": 2, "tools": [{"id": "Bad Id"}]}')
        with mock.patch.object(QtWidgets.QMessageBox, "warning") as warning:
            window._load_registry(bad)
        warning.assert_called_once()
        self.assertEqual(len(window.registry.tools), count)

    def test_list_modules_finds_modules_without_importing_leaf_modules(self):
        import bmaya.maya_ui.tool_registry_editor as editor
        sys.modules.pop("bmaya.maya.posetools", None)
        names = editor.list_modules()
        self.assertIn("bmaya.maya.posetools", names)
        self.assertNotIn("bmaya.maya.posetools", sys.modules)


class BuildMenus(EditorTest):
    """build_menus with the menu drawing replaced: Maya standalone has no MayaWindow."""

    def setUp(self):
        super().setUp()
        import bmaya.maya.constants
        import bmaya.maya_ui.tool_views.tool_menu as tool_menu
        self.tool_menu = tool_menu
        shutil.copytree(TOOLS, os.path.join(self.temp, "toolsets"))
        patcher = mock.patch.object(bmaya.maya.constants, "TOOLS_PATH", os.path.join(self.temp, "toolsets"))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(bmaya.maya.constants, "TOOL_REGISTRY_PATH", os.path.join(self.temp, "toolsets", "master_tool_registry.json"))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.built, self.deleted = [], []
        for target, record in (("delete_menu", self.deleted.append),):
            patcher = mock.patch.object(tool_menu, target, side_effect=record)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(tool_menu.ToolMenu, "build_ui", autospec=True, side_effect=lambda menu: self.built.append(menu.menu_id))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_builds_every_menu_when_the_plugin_is_loaded(self):
        with mock.patch.object(self.tool_menu, "_plugin_loaded", return_value=True):
            self.tool_menu.build_menus()
        self.assertEqual(self.built, ["bmaya_menu", "rigmodules_menu"])

    def test_a_menu_that_needs_a_plugin_is_deleted_and_not_built_without_it(self):
        with mock.patch.object(self.tool_menu, "_plugin_loaded", return_value=False):
            self.tool_menu.build_menus()
        self.assertEqual(self.built, ["bmaya_menu"])
        self.assertEqual(self.deleted, ["rigmodules_menu"])

    def test_a_broken_layout_raises_before_any_menu_is_touched_and_even_without_the_plugin(self):
        from bmaya.core import tool_registry as tr
        layout = os.path.join(self.temp, "toolsets", "rigmodules_menu.json")
        with open(layout, "w", encoding="utf-8") as handle:
            handle.write('{"version": 2, "label": "x", "items": [{"type": "bogus"}]}')
        registry = os.path.join(self.temp, "toolsets", "master_tool_registry.json")
        with open(registry, encoding="utf-8") as handle:
            text = handle.read()
        with open(registry, "w", encoding="utf-8") as handle:
            handle.write(text.replace('"enabled": true', '"enabeld": true', 1))
        with mock.patch.object(self.tool_menu, "_plugin_loaded", return_value=False):
            with self.assertRaises(tr.ToolDataError) as caught:
                self.tool_menu.build_menus()
        self.assertEqual((self.built, self.deleted), ([], []))
        self.assertEqual(len(caught.exception.reports), 2)   # the registry and the RigModules layout, in one report

    def test_a_missing_registry_raises_file_not_found(self):
        os.remove(os.path.join(self.temp, "toolsets", "master_tool_registry.json"))
        with self.assertRaises(FileNotFoundError):
            self.tool_menu.build_menus()
        self.assertEqual((self.built, self.deleted), ([], []))


def tearDownModule():
    if maya is not None:
        maya.standalone.uninitialize()


if __name__ == "__main__":
    unittest.main()
