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
        import bmaya.maya_ui.menus as tool_menu
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
        import bmaya.maya_ui.menus as tool_menu
        with self.no_scene_changes(), mock.patch.object(tool_menu, "build_menus") as build:
            bmaya.maya.devreload._unload()
        build.assert_not_called()


class Forms(MayaUiTest):

    def test_a_form_has_an_editor_per_field_chosen_by_its_hint(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.widgets
        form = bmaya.maya_ui.widgets.DataclassForm(Everything())
        types = {name: type(widget) for name, widget in form.widgets.items()}
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
        form.widgets["flag"].setChecked(True)
        form.widgets["mode"].setCurrentIndex(2)
        self.assertEqual((form.value().flag, form.value().mode), (True, "mesh"))
        form.widgets["data"].setText("[1,")
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
        combo = form.widgets["additive"]
        self.assertEqual(tuple(combo.itemText(i) for i in range(combo.count())),
                         bmaya.core.asset.animproperties.ADDITIVE_TYPES)
        self.assertEqual(form.value(), bmaya.maya.assettools.ClipSettings(additive="local"))


class SignatureFormTest(MayaUiTest):

    def test_a_required_argument_is_always_set(self):
        import bmaya.maya_ui.widgets

        def function(count: int, label: str = "x"):
            return count, label

        form = bmaya.maya_ui.widgets.SignatureForm(function, {})
        rows = {row.name: row for row in form.rows}
        self.assertTrue(rows["count"].is_set)
        self.assertFalse(rows["count"].set_check.isEnabled())
        self.assertFalse(rows["label"].is_set)
        self.assertEqual(form.kwargs(), {"count": 0})

    def test_widgets_follow_the_annotation(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.widgets

        def function(a: bool, b: int, c: float, d: str, e: typing.Literal["x", "y"], f: int | None = None, g=None,
                     h: list = None):
            pass

        form = bmaya.maya_ui.widgets.SignatureForm(function, {"e": "y", "f": 4, "h": [1, 2]})
        widgets = {row.name: type(row.widget) for row in form.rows}
        self.assertEqual(widgets, {
            "a": QtWidgets.QCheckBox, "b": QtWidgets.QSpinBox, "c": QtWidgets.QDoubleSpinBox, "d": QtWidgets.QLineEdit,
            "e": QtWidgets.QComboBox, "f": QtWidgets.QSpinBox, "g": QtWidgets.QLineEdit, "h": QtWidgets.QLineEdit,
        })
        values = form.kwargs()
        self.assertEqual((values["e"], values["f"], values["h"]), ("y", 4, [1, 2]))

    def test_a_saved_kwarg_sets_its_row_and_an_enum_argument_is_saved_as_its_value(self):
        import bmaya.maya_ui.widgets

        def function(colour: Colour = Colour.RED, flag: bool = False):
            pass

        form = bmaya.maya_ui.widgets.SignatureForm(function, {"colour": "blue"})
        rows = {row.name: row for row in form.rows}
        self.assertTrue(rows["colour"].is_set)
        self.assertFalse(rows["flag"].is_set)
        self.assertEqual(form.kwargs(), {"colour": "blue"})   # the value, not Colour.BLUE: the registry is JSON

    def test_json_text_that_is_not_json_is_reported_and_not_saved(self):
        import bmaya.maya_ui.widgets

        def function(items=None):
            pass

        form = bmaya.maya_ui.widgets.SignatureForm(function, {})
        row = form.rows[0]
        row.set_check.setChecked(True)
        row.widget.setText("[1,")
        with self.assertRaisesRegex(ValueError, "argument 'items' is not valid JSON"):
            form.kwargs()

    def test_a_saved_kwarg_the_function_no_longer_has_is_a_stale_row_that_can_be_removed(self):
        import bmaya.maya_ui.widgets

        def function(kept: bool = False):
            pass

        form = bmaya.maya_ui.widgets.SignatureForm(function, {"kept": True, "gone": 1})
        changes = []
        form.changed.connect(lambda: changes.append(1))
        self.assertEqual(form.kwargs(), {"kept": True, "gone": 1})
        self.assertEqual(form.stale, {"gone": 1})
        form.remove_stale("gone")
        self.assertEqual((form.kwargs(), form.stale, len(changes)), ({"kept": True}, {}, 1))

    def test_an_edit_and_a_set_toggle_emit_changed(self):
        import bmaya.maya_ui.widgets

        def function(flag: bool = False):
            pass

        form = bmaya.maya_ui.widgets.SignatureForm(function, {})
        changes = []
        form.changed.connect(lambda: changes.append(1))
        form.rows[0].set_check.setChecked(True)
        form.rows[0].widget.setChecked(True)
        self.assertEqual(len(changes), 2)

    def test_no_function_is_an_empty_form_and_variadic_parameters_get_no_row(self):
        import bmaya.maya_ui.widgets

        def function(*args, **kwargs):
            pass

        self.assertEqual(bmaya.maya_ui.widgets.SignatureForm().kwargs(), {})
        self.assertEqual(bmaya.maya_ui.widgets.SignatureForm(function, {}).rows, [])


class FieldWidgetTest(MayaUiTest):

    def test_show_and_read_value_round_trip_for_every_kind_of_hint(self):
        import bmaya.maya_ui.widgets as widgets
        cases = [(bool, True), (int, -3), (float, 0.25), (str, "walk"), (typing.Literal["a", "b"], "b"),
                 (Colour, Colour.BLUE), (dict, {"a": [1, 2]}), (int | None, 7)]
        for hint, value in cases:
            with self.subTest(hint=hint):
                widget = widgets.field_widget(hint)
                widgets.show_value(widget, hint, value)
                self.assertEqual(widgets.read_value(widget, hint), value)

    def test_an_image_path_field_is_a_line_with_a_browse_button(self):
        import bmaya.core.prompts
        import bmaya.maya_ui.widgets as widgets
        from PySide6 import QtWidgets
        calls = []
        widget = widgets.field_widget(bmaya.core.prompts.ImagePath, lambda: calls.append(1))
        self.assertIsInstance(widget, widgets.PathEdit)
        widgets.show_value(widget, bmaya.core.prompts.ImagePath, bmaya.core.prompts.ImagePath("C:/scans/a.png"))
        self.assertEqual(widget.line.text(), "C:/scans/a.png")
        self.assertEqual(calls, [1])
        value = widgets.read_value(widget, bmaya.core.prompts.ImagePath)
        self.assertEqual((value, type(value)), ("C:/scans/a.png", bmaya.core.prompts.ImagePath))
        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=("C:/scans/b.png", "")) as dialog:
            widget.browse_button.click()
        self.assertEqual(widget.line.text(), "C:/scans/b.png")
        self.assertIn("*.png", dialog.call_args.args[3])
        with mock.patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=("", "")):
            widget.browse_button.click()
        self.assertEqual(widget.line.text(), "C:/scans/b.png", "Cancel changes nothing")

    def test_an_enum_field_shows_a_member_or_its_value(self):
        import bmaya.maya_ui.widgets as widgets
        widget = widgets.field_widget(Colour)
        widgets.show_value(widget, Colour, "blue")
        self.assertIs(widgets.read_value(widget, Colour), Colour.BLUE)

    def test_on_change_is_called_for_each_edit(self):
        import bmaya.maya_ui.widgets as widgets
        calls = []
        for hint in (bool, int, float, str, typing.Literal["a", "b"], Colour, dict):
            widget = widgets.field_widget(hint, lambda: calls.append(hint))
            before = len(calls)
            if hint is bool:
                widget.setChecked(True)
            elif hint in (int, float):
                widget.setValue(5)
            elif hint is str or hint is dict:
                widget.setText("1")
            else:
                widget.setCurrentIndex(1)
            self.assertEqual(len(calls), before + 1, hint)


class CollapsibleSectionTest(MayaUiTest):

    def section(self, **kwargs):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.widgets
        section = bmaya.maya_ui.widgets.CollapsibleSection("Pose", **kwargs)
        section.content_layout.addWidget(QtWidgets.QLabel("inside"))
        self.addCleanup(section.deleteLater)
        section.show()
        return section

    def test_it_starts_open_with_a_down_chevron_and_its_title(self):
        section = self.section()
        self.assertEqual(section.header.text(), "Pose")
        self.assertTrue(section.is_expanded)
        self.assertTrue(section.body.isVisible())
        self.assertEqual(self.chevron(section), "chevron_down")

    def test_pressing_the_title_folds_and_opens_it_and_turns_the_chevron(self):
        section = self.section()
        seen = []
        section.toggled.connect(seen.append)
        section.header.click()
        self.assertFalse(section.is_expanded)
        self.assertFalse(section.body.isVisible())
        self.assertEqual(self.chevron(section), "chevron_right")
        section.header.click()
        self.assertTrue(section.body.isVisible())
        self.assertEqual(self.chevron(section), "chevron_down")
        self.assertEqual(seen, [False, True])

    @staticmethod
    def chevron(section):
        """The name of the theme icon the title bar shows, by comparing its image with each chevron's."""
        import bmaya.maya_ui.theme
        shown = section.header.icon().pixmap(16, 16).toImage()
        for name in ("chevron_down", "chevron_right"):
            if bmaya.maya_ui.theme.icon(name).pixmap(16, 16).toImage() == shown:
                return name
        return None

    def test_it_can_start_folded_and_be_set_from_code(self):
        section = self.section(expanded=False)
        self.assertFalse(section.body.isVisible())
        section.set_expanded(True)
        self.assertTrue(section.body.isVisible())


class ThemeTest(MayaUiTest):

    def test_the_sheet_has_no_unfilled_name_and_names_only_icons_that_exist(self):
        import re
        import pathlib
        import bmaya.maya_ui.theme as theme
        sheet = theme.stylesheet()
        self.assertNotIn("$", sheet)
        paths = re.findall(r"url\(([^)]+)\)", sheet)
        self.assertTrue(paths)
        for path in paths:
            self.assertTrue(pathlib.Path(path).is_file(), path)
            self.assertTrue(pathlib.Path(path.replace(".png", "@2x.png")).is_file(), path)

    def test_every_icon_draws_something(self):
        import bmaya.maya_ui.theme as theme
        for name in ("chevron_down", "chevron_right", "chevron_up", "check", "dot", "plus", "minus", "mirror",
                     "rotate", "scale", "translate", "key", "pose", "module",
                     "save", "load", "folder"):
            image = theme.icon(name).pixmap(16, 16).toImage()
            opaque = [image.pixelColor(x, y).alpha() for x in range(16) for y in range(16)]
            self.assertTrue(any(opaque), name)
            self.assertFalse(all(opaque), name)

    def test_a_changed_palette_gets_its_own_icon_folder(self):
        import dataclasses
        import bmaya.maya_ui.theme as theme
        other = dataclasses.replace(theme.DARK, accent="#ff0000")
        self.assertNotEqual(theme.icon_folder(other), theme.icon_folder())

    def test_apply_styles_the_widget_it_is_given_and_not_the_application(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.theme as theme
        widget = QtWidgets.QWidget()
        self.addCleanup(widget.deleteLater)
        before = QtWidgets.QApplication.instance().styleSheet()
        theme.apply(widget)
        self.assertEqual(widget.styleSheet(), theme.stylesheet())
        self.assertEqual(QtWidgets.QApplication.instance().styleSheet(), before)

    def test_the_windows_and_the_host_apply_it(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.host
        import bmaya.maya_ui.qtbase
        import bmaya.maya_ui.theme as theme
        sheet = theme.stylesheet()
        window = bmaya.maya_ui.qtbase.SimpleWindow()
        dialog = bmaya.maya_ui.qtbase.Dialog()
        shown = bmaya.maya_ui.host.show(QtWidgets.QWidget(), object_name="themetest_host")
        for widget in (window, dialog, shown):
            self.addCleanup(widget.deleteLater)
            self.assertEqual(widget.styleSheet(), sheet)


class HostTest(MayaUiTest):

    def tearDown(self):
        from PySide6 import QtWidgets
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if widget.objectName().startswith("hosttest"):
                widget.deleteLater()

    def test_there_is_no_main_window_in_mayapy(self):
        import bmaya.maya_ui.host
        self.assertIsNone(bmaya.maya_ui.host.parent_window())

    def test_show_opens_the_widget_by_its_object_name(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.host
        widget = QtWidgets.QWidget()
        shown = bmaya.maya_ui.host.show(widget, object_name="hosttest_one")
        self.assertIs(shown, widget)
        self.assertTrue(widget.isVisible())
        self.assertIs(bmaya.maya_ui.host.find("hosttest_one"), widget)
        self.assertIsNone(bmaya.maya_ui.host.find("hosttest_other"))

    def test_showing_again_closes_the_old_window_so_there_is_one(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.host
        first = bmaya.maya_ui.host.show(QtWidgets.QWidget(), object_name="hosttest_two")
        second = bmaya.maya_ui.host.show(QtWidgets.QWidget(), object_name="hosttest_two")
        self.assertIsNot(first, second)
        self.assertFalse(first.isVisible())
        self.assertIs(bmaya.maya_ui.host.find("hosttest_two"), second)

    def test_an_open_window_that_refuses_to_close_is_kept_and_the_new_one_is_dropped(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.host

        class Stubborn(QtWidgets.QWidget):
            def closeEvent(self, event):
                event.ignore()

        old = bmaya.maya_ui.host.show(Stubborn(), object_name="hosttest_three")
        new = QtWidgets.QWidget()
        self.assertIs(bmaya.maya_ui.host.show(new, object_name="hosttest_three"), old)
        self.assertTrue(old.isVisible())
        self.assertFalse(new.isVisible())

    def test_dock_outside_a_gui_maya_shows_a_plain_window(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.host
        widget = bmaya.maya_ui.host.show(QtWidgets.QWidget(), object_name="hosttest_dock", dock=True)
        self.assertTrue(widget.isVisible())

    def test_defer_runs_the_function_from_the_event_loop_outside_maya(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.host
        calls = []
        with mock.patch.dict(sys.modules, {"maya.utils": None}):   # an import of it raises ImportError, as in plain Python
            bmaya.maya_ui.host.defer(lambda: calls.append(1))
        self.assertEqual(calls, [])
        QtWidgets.QApplication.processEvents()
        self.assertEqual(calls, [1])


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
            dialog.form.widgets["flag"].setChecked(True)
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
        dialog.form.widgets["data"].setText("{")
        dialog.accept()
        self.assertNotEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)
        self.assertIn("data: not valid JSON", dialog.problem.text())


if __name__ == "__main__":
    unittest.main()
