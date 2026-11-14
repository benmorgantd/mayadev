"""The registration passes, the dev reload hooks and the Qt side of the prompter, offscreen in mayapy (RigModules
design/mayadev-ui.md, D49). No plugin is needed.

Run with tests/core/run.bat (the Maya half), or: mayapy -m unittest discover -s tests/core -p "test_maya_*.py"
"""

import contextlib
import dataclasses
import enum
import logging
import os
import sys
import typing
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

try:
    import maya.standalone
except ImportError:
    maya = None


class Colour(enum.Enum):
    RED = "red"
    BLUE = "blue"


@dataclasses.dataclass(frozen=True)
class Everything:
    flag: bool = False
    count: int = 0
    scale: float = 1.0
    label: str = ""
    mode: typing.Literal["none", "local", "mesh"] = "none"
    colour: Colour = Colour.RED
    data: dict = dataclasses.field(default_factory=dict)


def setUpModule():
    if maya is None:
        raise unittest.SkipTest("needs mayapy")
    # The QApplication comes first: standalone Maya otherwise starts a QCoreApplication, which can't host widgets
    # (tests/README.md).
    from PySide6 import QtWidgets
    global _APP
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # Initialize only once per process: a second initialize after test_maya_tool_editors crashed Maya 2026 in
    # melRemoveDynamicProc while it sourced its startup MEL.
    import maya.cmds as cmds
    if not hasattr(cmds, "about"):
        maya.standalone.initialize(name="python")


class MayaUiTest(unittest.TestCase):
    pass


class Registration(MayaUiTest):

    def setUp(self):
        import bmaya.core.log
        import bmaya.core.prompts
        import bmaya.maya.devreload
        self.addCleanup(bmaya.core.log.reset_writers)
        self.addCleanup(bmaya.core.prompts.reset_prompter)
        self.addCleanup(bmaya.maya.devreload.reset_hooks)

    def test_maya_register_keeps_stdout_in_batch(self):
        import bmaya.core.log
        import bmaya.maya.startup
        bmaya.maya.startup.register()
        self.assertEqual(bmaya.core.log.LogOutput.writers, {})

    def test_maya_register_logs_through_mgloba_in_a_gui_session(self):
        import maya.api.OpenMaya as om
        import maya.cmds as cmds
        import bmaya.core.log
        import bmaya.maya.startup
        with mock.patch.object(cmds, "about", return_value=False):
            bmaya.maya.startup.register()
            bmaya.maya.startup.register()     # again: replaced, not added to
        self.assertEqual(bmaya.core.log.LogOutput.writers, {
            logging.INFO: om.MGlobal.displayInfo,
            logging.WARNING: om.MGlobal.displayWarning,
            logging.ERROR: om.MGlobal.displayError,
        })

    def test_maya_ui_register_fills_the_prompter_and_the_reload_hooks(self):
        import bmaya.core.prompts
        import bmaya.maya.devreload
        import bmaya.maya_ui.prompter
        import bmaya.maya_ui.startup
        import bmaya.maya_ui.tool_views.tool_menu as tool_menu
        bmaya.maya_ui.startup.register()
        self.assertIsInstance(bmaya.core.prompts.current(), bmaya.maya_ui.prompter.QtPrompter)
        self.assertEqual(bmaya.maya.devreload._hooks,
                         bmaya.maya.devreload.ReloadHooks(tool_menu.delete_plugin_menus, tool_menu.build_menus))

    def no_scene_changes(self):
        """The unload with its Maya calls replaced: these tests check the hooks' order, and a real new scene and
        undo flush after the editor tests crashed Maya's undo manager."""
        import bmaya.maya.devreload
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(bmaya.maya.devreload, "cmds"))
        stack.enter_context(mock.patch.object(bmaya.maya.devreload, "_forget_python_package"))
        return stack

    def test_unload_runs_the_hooks_around_the_plugin(self):
        import bmaya.maya.devreload
        calls = []
        bmaya.maya.devreload.register_hooks(before_unload=lambda: calls.append("before"),
                                            after_load=lambda: calls.append("after"))
        with self.no_scene_changes():
            bmaya.maya.devreload._unload()
        self.assertEqual(calls, ["before", "after"])

    def test_without_hooks_an_unload_builds_no_menu(self):
        import bmaya.maya.devreload
        import bmaya.maya_ui.tool_views.tool_menu as tool_menu
        with self.no_scene_changes(), mock.patch.object(tool_menu, "build_menus") as build:
            bmaya.maya.devreload._unload()
        build.assert_not_called()


class Forms(MayaUiTest):

    def test_a_form_has_an_editor_per_field_chosen_by_its_hint(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.widgets
        form = bmaya.maya_ui.widgets.DataclassForm(Everything())
        types = {name: type(editor.widget) for name, editor in form.editors.items()}
        self.assertEqual(types, {
            "flag": QtWidgets.QCheckBox, "count": QtWidgets.QSpinBox, "scale": QtWidgets.QDoubleSpinBox,
            "label": QtWidgets.QLineEdit, "mode": QtWidgets.QComboBox, "colour": QtWidgets.QComboBox,
            "data": QtWidgets.QLineEdit,
        })

    def test_a_form_round_trips_its_value(self):
        import bmaya.maya_ui.widgets
        value = Everything(flag=True, count=3, scale=0.5, label="walk", mode="mesh", colour=Colour.BLUE, data={"a": 1})
        form = bmaya.maya_ui.widgets.DataclassForm(value)
        self.assertEqual(form.value(), value, "an Enum field reads back its member")

    def test_edits_reach_the_value_and_bad_json_names_the_field(self):
        import bmaya.maya_ui.widgets
        form = bmaya.maya_ui.widgets.DataclassForm(Everything())
        form.editors["flag"].widget.setChecked(True)
        form.editors["mode"].widget.setCurrentIndex(2)
        self.assertEqual((form.value().flag, form.value().mode), (True, "mesh"))
        form.editors["data"].widget.setText("[1,")
        with self.assertRaisesRegex(ValueError, "^data: not valid JSON"):
            form.value()

    def test_a_form_needs_a_dataclass_instance(self):
        import bmaya.maya_ui.widgets
        with self.assertRaises(TypeError):
            bmaya.maya_ui.widgets.DataclassForm(Everything)

    def test_the_clip_settings_form_offers_the_additive_types(self):
        import bmaya.core.asset.animproperties
        import bmaya.maya.assettools
        import bmaya.maya_ui.widgets
        form = bmaya.maya_ui.widgets.DataclassForm(bmaya.maya.assettools.ClipSettings(additive="local"))
        combo = form.editors["additive"].widget
        self.assertEqual(tuple(combo.itemText(i) for i in range(combo.count())),
                         bmaya.core.asset.animproperties.ADDITIVE_TYPES)
        self.assertEqual(form.value(), bmaya.maya.assettools.ClipSettings(additive="local"))


class QtPrompterTest(MayaUiTest):

    def prompter(self):
        import bmaya.maya_ui.prompter
        return bmaya.maya_ui.prompter.QtPrompter()

    def test_ask_text_strips_and_reads_cancel_and_empty_as_none(self):
        from PySide6 import QtWidgets
        for reply, expected in ((("  idle ", True), "idle"), (("", True), None), (("idle", False), None)):
            with mock.patch.object(QtWidgets.QInputDialog, "getText", return_value=reply) as dialog:
                self.assertEqual(self.prompter().ask_text("Save Pose", "Name:", "x"), expected)
            self.assertEqual(dialog.call_args.kwargs["text"], "x")

    def test_ask_file_picks_the_save_or_open_dialog(self):
        from PySide6 import QtWidgets
        with mock.patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=("C:/a.json", "")) as save, \
                mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=("", "")) as open_:
            self.assertEqual(self.prompter().ask_file("Save", "Pose files (*.json)", save=True, folder="C:/p"), "C:/a.json")
            self.assertIsNone(self.prompter().ask_file("Load", "Pose files (*.json)", save=False))
        self.assertEqual(save.call_args.args[1:], ("Save", "C:/p", "Pose files (*.json)"))
        open_.assert_called_once()

    def test_ask_form_returns_the_edited_value_and_none_on_cancel(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.prompter

        def accept_with_flag(dialog):
            dialog.form.editors["flag"].widget.setChecked(True)
            dialog.accept()
            return dialog.result()

        with mock.patch.object(bmaya.maya_ui.prompter.FormDialog, "exec", accept_with_flag):
            self.assertEqual(self.prompter().ask_form("Settings", Everything()), Everything(flag=True))
        with mock.patch.object(bmaya.maya_ui.prompter.FormDialog, "exec",
                               lambda dialog: QtWidgets.QDialog.DialogCode.Rejected):
            self.assertIsNone(self.prompter().ask_form("Settings", Everything()))

    def test_the_form_dialog_stays_open_while_a_value_is_invalid(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.prompter
        dialog = bmaya.maya_ui.prompter.FormDialog("Settings", Everything())
        dialog.form.editors["data"].widget.setText("{")
        dialog.accept()
        self.assertNotEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)
        self.assertIn("data: not valid JSON", dialog.problem.text())


if __name__ == "__main__":
    unittest.main()
