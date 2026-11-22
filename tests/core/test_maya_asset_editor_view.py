"""The Asset Editor's window offscreen in mayapy, over a fake session (RigModules D61). The session and the file rows are
tested against real rigs in tests/asset/test_maya_asset_editor.py, so no plugin is needed here: this checks the wiring.

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

HERO = "shooter\\main\\characters\\hero"
VILLAIN = "shooter\\main\\characters\\villain"


def setUpModule():
    if maya is None:
        raise unittest.SkipTest("needs mayapy")
    from PySide6 import QtWidgets
    global _APP
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    import maya.cmds as cmds
    if not hasattr(cmds, "about"):
        maya.standalone.initialize(name="python")
    try:
        import rigmodules.query  # noqa: F401
    except ImportError:
        raise unittest.SkipTest("put RigModules' python folder on the path (RigModules.mod)")


def row(key, label, owner_kind, owner, exists=True, saves=True, loads=True, save_blocked="", load_blocked=""):
    import bmaya.maya.assetfiles
    return bmaya.maya.assetfiles.FileRow(
        key=key, label=label, owner_kind=owner_kind, owner=owner, path=f"C:/projects/{key}", exists=exists,
        modified=1_700_000_000.0 if exists else None, versions=2 if exists else 0, saves=saves, loads=loads,
        save_blocked=save_blocked, load_blocked=load_blocked)


class FakeFiles:

    def __init__(self):
        self.rows = [row("skeleton", "Skeleton", "skeleton", "default"),
                     row("model", "Model", "look", "default", exists=False, save_blocked="There are no meshes.",
                         load_blocked="The model is not saved yet."),
                     row("template", "Template", "rig", "game", saves=False, loads=False)]
        self.message = ""
        self.calls = []
        self.error = None

    def _record(self, *call):
        if self.error:
            raise RuntimeError(self.error)
        self.calls.append(call)

    def save(self, key, prompter=None):
        self._record("save", key)
        return f"C:/projects/{key}"

    def load(self, key):
        self._record("load", key)

    def restore(self, key, prompter=None):
        self._record("restore", key)
        return f"C:/projects/{key}"

    def load_by_name(self, key):
        self._record("load_by_name", key)

    def import_textures(self, key, prompter=None):
        self._record("import_textures", key)
        return f"C:/projects/{key}"

    def open_folder(self, key):
        self._record("open_folder", key)
        return f"C:/projects/{key}"

    def build_rig(self, ignore_skeleton_hash=False):
        self._record("build_rig", ignore_skeleton_hash)
        return "hero_game:rigRootModule1"

    def refresh(self):
        self.calls.append(("refresh",))


class FakeMarkup:
    """The MarkupModel surface the Markup tab reads and calls. Every command is recorded."""

    def __init__(self):
        import bmaya.core.observable
        from bmaya.core.fieldset import FieldState
        self.changed = bmaya.core.observable.Event()
        self.summary = "3 joint(s): 2 marked, 1 not"
        self.joints = ["|a", "|b", "|c"]
        self.marked = {"|a": {}, "|b": {}}
        self.unmarked = ["|c"]
        self.fields = {"usage": FieldState(None, True, 2), "side": FieldState("Left", False, 2),
                       "export": FieldState(None, True, 2), "skin": FieldState(True, False, 2)}
        self.usages = ["arm", "spine"]
        self.warnings = []
        self.controls = []
        self.active = []
        self.calls = []
        self.error = None

    def _record(self, *call):
        if self.error:
            raise RuntimeError(self.error)
        self.calls.append(call)

    def set_active(self, active): self.active.append(active)
    def set_field(self, name, value): self._record("set_field", name, value)
    def add_markup(self, usage, side="Center", export=True, skin=True, numbered=False):
        self._record("add_markup", usage, side, export, skin, numbered)
    def remove(self): self._record("remove")
    def mirror_joints(self): self._record("mirror_joints")
    def add_twist_joints(self, prompter=None): self._record("add_twist_joints")


class FakeShapes:
    """The ShapeModel surface the Shapes tab reads and calls. Every command is recorded."""

    def __init__(self):
        import bmaya.core.observable
        from bmaya.core.fieldset import FieldState
        self.changed = bmaya.core.observable.Event()
        self.summary = "2 rig control(s)"
        self.controls = ["|a", "|b"]
        self.enum_names = ["Box", "Sphere", "Circle"]
        self.fields = {"shapeType": FieldState("Sphere", False, 2), "filled": FieldState(None, True, 2),
                       "wireframeAlpha": FieldState(0.5, False, 2), "scale": FieldState(2.0, False, 2),
                       "scaleX": FieldState(2.0, False, 2), "scaleY": FieldState(2.0, False, 2),
                       "scaleZ": FieldState(2.0, False, 2), "translateX": FieldState(None, True, 2),
                       "translateY": FieldState(0.0, False, 2), "translateZ": FieldState(0.0, False, 2),
                       "rotateX": FieldState(0.0, False, 2), "rotateY": FieldState(0.0, False, 2),
                       "rotateZ": FieldState(90.0, False, 2)}
        self.active = []
        self.calls = []
        self.error = None

    def _record(self, *call):
        if self.error:
            raise RuntimeError(self.error)
        self.calls.append(call)

    def set_active(self, active): self.active.append(active)
    def set_field(self, name, value, mode="set"): self._record("set_field", name, value, mode)
    def mirror(self, left_to_right, fallback_rig_root=None): self._record("mirror", left_to_right, fallback_rig_root)


class FakeNaming:
    """The NamingModel surface the Naming tab reads and calls. Every command is recorded."""

    def __init__(self):
        import bmaya.core.observable
        self.changed = bmaya.core.observable.Event()
        self.summary = "3 node(s): finger_00_L_JNT and 2 more"
        self.nodes = ["|a", "|b", "|c"]
        self.base, self.side, self.start_index = "finger", "Left", 4
        self.active = []
        self.calls = []
        self.error = None

    def _record(self, *call):
        if self.error:
            raise RuntimeError(self.error)
        self.calls.append(call)
        return ["x"] * len(self.nodes)

    def set_active(self, active): self.active.append(active)
    def rename(self, base, side, start_index): return self._record("rename", base, side, start_index)
    def mirror(self): return self._record("mirror")


class FakeSession:
    """The AssetEditorSession surface the window reads and calls. Every command is recorded."""

    def __init__(self, root, asset_id=HERO):
        import bmaya.core.asset.context
        import bmaya.core.observable
        self.changed = bmaya.core.observable.Event()
        self.selection_changed = bmaya.core.observable.Event()
        self.context = bmaya.core.asset.context.AssetContext(root)
        self.context.set_asset(asset_id)
        self.asset_ids = [HERO, VILLAIN]
        self.files = FakeFiles()
        self.markup = FakeMarkup()
        self.shapes = FakeShapes()
        self.naming = FakeNaming()
        self.mismatch = ""
        self.rig = object()
        self.watching = []
        self.calls = []
        self.error = None

    def _record(self, *call):
        if self.error:
            raise RuntimeError(self.error)
        self.calls.append(call)

    def close(self): self.calls.append(("close",))
    def watch_selection(self, watch): self.watching.append(watch)
    def rig_mismatch(self): return self.mismatch
    def active_rig(self): return self.rig
    def refresh(self): self._record("refresh")
    def set_asset(self, asset_id): self._record("set_asset", asset_id)
    def use_active_rig(self): self._record("use_active_rig")
    def create_project(self, prompter=None): self._record("create_project")
    def create_asset(self, prompter=None): self._record("create_asset")
    def create_rig(self, prompter=None): self._record("create_rig")
    def create_look(self, prompter=None): self._record("create_look")


class EditorView(unittest.TestCase):

    def setUp(self):
        import bmaya.core.asset
        temp = tempfile.mkdtemp(prefix="bmaya_asset_editor_view_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.root = os.path.join(temp, "projects")
        patcher = mock.patch.dict(os.environ, {"RIGGING_PROJECT_DIR": self.root})
        patcher.start()
        self.addCleanup(patcher.stop)
        bmaya.core.asset.Project.create(os.path.join(self.root, "shooter", "main"))
        hero = bmaya.core.asset.Asset.create(HERO, "Character")
        hero.add_rig("game", bmaya.core.asset.SkeletonRef("default"))
        hero.add_rig("face", bmaya.core.asset.SkeletonRef("default"))
        hero.add_look("default", [bmaya.core.asset.SkeletonRef("default")])
        patcher = mock.patch("PySide6.QtWidgets.QMessageBox.critical", side_effect=AssertionError("unexpected dialog"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def window(self, session=None):
        import bmaya.maya_ui.asseteditor
        session = session or FakeSession(self.root)
        window = bmaya.maya_ui.asseteditor.AssetEditor(session)
        self.addCleanup(window.deleteLater)
        return window

    # ---- the header ----

    def test_the_header_shows_the_asset_and_its_owners(self):
        window = self.window()
        self.assertEqual(window.picker.currentText(), HERO)
        self.assertEqual([window.picker.itemText(i) for i in range(window.picker.count())], [HERO, VILLAIN])
        self.assertEqual([window.rig_combo.itemText(i) for i in range(window.rig_combo.count())], ["face", "game"])
        self.assertEqual((window.rig_combo.currentText(), window.look_combo.currentText()), ("face", "default"))

    def test_an_asset_with_no_skeleton_says_none_saved_and_disables_the_combo(self):
        window = self.window()
        self.assertEqual((window.skeleton_combo.isEnabled(), window.skeleton_combo.currentText()), (False, "none saved"))

    def test_picking_an_asset_in_the_list_sets_it(self):
        window = self.window()
        window.picker.activated.emit(1)
        self.assertEqual(window.session.calls, [("set_asset", VILLAIN)])

    def test_returning_a_typed_id_sets_it_and_programmatic_changes_do_not(self):
        window = self.window()
        window.picker.set_current(VILLAIN)
        window.picker.set_ids([HERO], HERO)
        self.assertEqual(window.session.calls, [])
        window.picker.setEditText("shooter\\main\\props\\crate")
        window.picker.lineEdit().returnPressed.emit()
        self.assertEqual(window.session.calls, [("set_asset", "shooter\\main\\props\\crate")])

    def test_picking_a_rig_sets_it_in_the_context(self):
        window = self.window()
        window.rig_combo.activated.emit(1)
        self.assertEqual(window.session.context.rig, "game")

    def test_use_active_rig_is_disabled_with_no_active_rig(self):
        session = FakeSession(self.root)
        session.rig = None
        window = self.window(session)
        self.assertFalse(window.use_rig_button.isEnabled())
        window.use_rig_button.click()
        self.assertEqual(session.calls, [])

    def test_use_active_rig_calls_the_session(self):
        window = self.window()
        window.use_rig_button.click()
        self.assertEqual(window.session.calls, [("use_active_rig",)])

    def test_the_refresh_button_reads_again(self):
        window = self.window()
        window.refresh_button.click()
        self.assertEqual(window.session.calls, [("refresh",)])

    def test_the_new_menu_has_four_actions_and_each_calls_the_session(self):
        window = self.window()
        self.assertEqual([action.text() for action in window.new_menu.actions()],
                         ["Project...", "Asset...", "Rig...", "Look..."])
        for key in ("project", "asset", "rig", "look"):
            window.new_actions[key].trigger()
        self.assertEqual([call[0] for call in window.session.calls],
                         ["create_project", "create_asset", "create_rig", "create_look"])

    # ---- the mismatch strip ----

    def test_the_mismatch_strip_shows_only_with_text_and_switch_uses_the_active_rig(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.show()
        self.assertFalse(window.mismatch_bar.isVisible())
        session.mismatch = "The active rig 'game' belongs to villain."
        session.changed.emit()
        self.assertTrue(window.mismatch_bar.isVisible())
        self.assertIn("villain", window.mismatch_label.text())
        window.switch_button.click()
        self.assertEqual(session.calls, [("use_active_rig",)])

    # ---- the Files tab ----

    def test_the_files_table_has_a_row_per_file_with_its_status(self):
        window = self.window()
        model = window.files_table.row_model
        self.assertEqual(model.rowCount(), 3)
        text = lambda r, c: model.data(model.index(r, c))
        self.assertEqual([text(0, c) for c in (0, 1, 3)], ["Skeleton", "default", "2"])
        self.assertRegex(text(0, 2), r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")   # local time, so the zone varies
        self.assertEqual([text(1, c) for c in range(4)], ["Model", "default", "Not saved", ""])

    def test_a_folder_row_has_an_open_folder_menu_item_and_counts_its_files(self):
        import dataclasses
        window = self.window()
        textures = dataclasses.replace(row("textures", "Textures", "look", "default"), opens_folder=True, file_count=3,
                                       note="2 meshes mapped", versions=0)
        missing = dataclasses.replace(textures, key="more", file_count=None, exists=False, note="",
                                      open_blocked="The asset has no look.")
        window.files_table.set_rows([textures, missing])
        model = window.files_table.row_model
        self.assertEqual([model.data(model.index(r, 2)) for r in (0, 1)], ["3 files, 2 meshes mapped", "No folder"])
        self.assertIn(("textures", "save"), window.files_table.buttons)
        menu = window.files_table.row_menu("textures")
        self.assertEqual([action.text() for action in menu.actions()], ["Open Folder"])
        menu.actions()[0].trigger()
        self.assertEqual(window.session.files.calls[-1], ("open_folder", "textures"))
        blocked = window.files_table.row_menu("more").actions()[0]
        self.assertFalse(blocked.isEnabled())
        self.assertEqual(blocked.toolTip(), "The asset has no look.")

    def test_the_import_textures_menu_item_asks_the_files_model_and_says_where_it_went(self):
        import dataclasses
        window = self.window()
        textures = dataclasses.replace(row("textures", "Textures", "look", "default"), opens_folder=True, imports_images=True,
                                       versions=0)
        blocked = dataclasses.replace(textures, key="more", save_blocked="The rig is not in the scene.")
        window.files_table.set_rows([textures, blocked])
        menu = window.files_table.row_menu("textures")
        self.assertEqual([action.text() for action in menu.actions()], ["Import Textures...", "Open Folder"])
        menu.actions()[0].trigger()
        self.assertEqual(window.session.files.calls[-1], ("import_textures", "textures"))
        self.assertIn("Imported textures into C:/projects/textures", window.status_label.text())
        off = window.files_table.row_menu("more").actions()[0]
        self.assertFalse(off.isEnabled())
        self.assertEqual(off.toolTip(), "The rig is not in the scene.")

    def test_a_file_without_save_or_load_has_no_buttons(self):
        window = self.window()
        self.assertNotIn(("template", "save"), window.files_table.buttons)
        self.assertNotIn(("template", "load"), window.files_table.buttons)
        self.assertIn(("skeleton", "save"), window.files_table.buttons)

    def test_save_load_and_open_folder_buttons_show_an_icon_and_no_text(self):
        window = self.window()
        buttons = list(window.files_table.buttons.values()) + [window.save_shapes_button, window.load_shapes_button]
        for button in buttons:
            self.assertEqual(button.text(), "")
            self.assertFalse(button.icon().isNull())

    def test_a_blocked_button_is_disabled_and_its_tool_tip_is_the_reason(self):
        window = self.window()
        buttons = window.files_table.buttons
        self.assertFalse(buttons[("model", "save")].isEnabled())
        self.assertEqual(buttons[("model", "save")].toolTip(), "There are no meshes.")
        self.assertFalse(buttons[("model", "load")].isEnabled())
        self.assertTrue(buttons[("skeleton", "save")].isEnabled())
        self.assertIn("local version", buttons[("skeleton", "save")].toolTip())

    def test_save_and_load_buttons_call_the_files_model(self):
        window = self.window()
        window.files_table.buttons[("skeleton", "save")].click()
        window.files_table.buttons[("skeleton", "load")].click()
        self.assertEqual(window.session.files.calls, [("save", "skeleton"), ("load", "skeleton")])
        self.assertEqual(window.status_label.text(), "")

    def test_a_save_says_where_it_went(self):
        window = self.window()
        window.files_table.buttons[("skeleton", "save")].click()
        self.assertIn("C:/projects/skeleton", window.status_label.text())

    def test_the_row_menu_restores_through_the_files_model(self):
        window = self.window()
        menu = window.files_table.row_menu("skeleton")
        self.assertEqual([action.text() for action in menu.actions()], ["Restore Version..."])
        menu.actions()[0].trigger()
        self.assertEqual(window.session.files.calls[-1], ("restore", "skeleton"))
        self.assertIn("Restored C:/projects/skeleton", window.status_label.text())

    def test_a_row_without_versions_or_load_by_name_has_no_menu(self):
        window = self.window()
        self.assertIsNone(window.files_table.row_menu("model"))
        self.assertIsNone(window.files_table.row_menu("nothing"))

    def test_load_by_name_is_on_the_row_menu_and_off_when_load_is_blocked(self):
        import dataclasses
        window = self.window()
        weights = dataclasses.replace(row("weights", "Skin weights", "look", "default"), versions=0, loads_by_name=True)
        blocked = dataclasses.replace(weights, key="other", load_blocked="The rig is not in the scene.")
        window.files_table.set_rows([weights, blocked])
        menu = window.files_table.row_menu("weights")
        self.assertEqual([action.text() for action in menu.actions()], ["Load by Name"])
        menu.actions()[0].trigger()
        self.assertEqual(window.session.files.calls[-1], ("load_by_name", "weights"))
        action = window.files_table.row_menu("other").actions()[0]
        self.assertEqual((action.isEnabled(), action.toolTip()), (False, "The rig is not in the scene."))

    def test_build_rig_calls_the_files_model_and_is_disabled_with_no_rig(self):
        window = self.window()
        window.build_button.click()
        self.assertIn(("build_rig", False), window.session.files.calls)
        window.ignore_hash_check.setChecked(True)
        window.build_button.click()
        self.assertEqual(window.session.files.calls[-1], ("build_rig", True))
        window.session.context.set_asset(VILLAIN)
        window.session.changed.emit()
        self.assertFalse(window.build_button.isEnabled())

    def test_the_rows_follow_the_session_changing(self):
        session = FakeSession(self.root)
        window = self.window(session)
        session.files.rows = session.files.rows[:1]
        session.changed.emit()
        self.assertEqual(window.files_table.row_model.rowCount(), 1)

    def test_a_message_shows_only_when_there_is_one(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.show()
        self.assertFalse(window.files_message.isVisible())
        session.files.rows, session.files.message = [], "Pick an asset."
        session.changed.emit()
        self.assertEqual((window.files_message.isVisible(), window.files_message.text()), (True, "Pick an asset."))

    # ---- errors ----

    def test_a_command_error_goes_to_the_status_line_and_never_raises(self):
        session = FakeSession(self.root)
        window = self.window(session)
        session.files.error = "There are no joints in the scene."
        window.files_table.buttons[("skeleton", "save")].click()
        self.assertEqual(window.status_label.text(), "There are no joints in the scene.")

    def test_an_invalid_typed_id_is_reported_not_raised(self):
        import bmaya.core.asset
        session = FakeSession(self.root)
        session.set_asset = mock.Mock(side_effect=bmaya.core.asset.AssetIdError("bad id"))
        window = self.window(session)
        window.picker.setEditText("Bad Id")
        window.picker.lineEdit().returnPressed.emit()
        self.assertEqual(window.status_label.text(), "bad id")

    # ---- the Markup tab ----

    def show_markup(self, window):
        window.show()
        window.tabs.setCurrentWidget(window.markup_tab)

    def test_the_markup_model_reads_only_while_its_tab_shows(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.show()
        self.assertEqual(session.markup.active, [False])
        window.tabs.setCurrentWidget(window.markup_tab)
        window.tabs.setCurrentIndex(0)
        window.tabs.setCurrentWidget(window.markup_tab)
        window.hide()
        self.assertEqual(session.markup.active, [False, True, False, True, False])
        self.assertEqual(session.shapes.active, [False, False, False, False, False])

    def test_the_form_shows_each_fields_value_and_mixed(self):
        from PySide6 import QtCore
        window = self.window()
        form = window.markup_form
        self.assertEqual(form.editors["side"].currentText(), "Left")
        self.assertEqual(form.editors["usage"].currentText(), "")
        self.assertEqual(form.editors["usage"].lineEdit().placeholderText(), "Mixed")
        self.assertEqual(form.editors["export"].checkState(), QtCore.Qt.CheckState.PartiallyChecked)
        self.assertEqual(form.editors["skin"].checkState(), QtCore.Qt.CheckState.Checked)

    def test_the_summary_and_the_suggestions_show(self):
        window = self.window()
        self.assertEqual(window.markup_summary.text(), "3 joint(s): 2 marked, 1 not")
        combo = window.markup_form.editors["usage"]
        self.assertEqual([combo.itemText(i) for i in range(combo.count())], ["arm", "spine"])

    def test_editing_a_field_sets_it_on_the_model_and_showing_it_does_not(self):
        session = FakeSession(self.root)
        window = self.window(session)
        session.markup.changed.emit()
        self.assertEqual(session.markup.calls, [])
        side = window.markup_form.editors["side"]
        side.setCurrentIndex(side.findText("Right"))
        side.activated.emit(side.currentIndex())
        window.markup_form.editors["export"].click()
        usage = window.markup_form.editors["usage"]
        usage.setEditText("hand")
        usage.lineEdit().editingFinished.emit()
        self.assertEqual(session.markup.calls, [("set_field", "side", "Right"), ("set_field", "export", True),
                                                ("set_field", "usage", "hand")])

    def test_a_mixed_choice_row_is_not_an_edit_and_goes_when_a_value_is_shown(self):
        from bmaya.core.fieldset import FieldState
        session = FakeSession(self.root)
        window = self.window(session)
        side = window.markup_form.editors["side"]
        window.markup_form.set_state("side", FieldState(None, True, 2))
        self.assertEqual((side.currentText(), side.count()), ("Mixed", 4))
        side.activated.emit(0)
        self.assertEqual(session.markup.calls, [])
        window.markup_form.set_state("side", FieldState("Right", False, 2))
        self.assertEqual((side.currentText(), side.count()), ("Right", 3))

    def test_the_form_and_remove_are_off_with_no_marked_joint(self):
        session = FakeSession(self.root)
        session.markup.marked = {}
        window = self.window(session)
        session.markup.changed.emit()
        self.assertFalse(window.markup_form.isEnabled())
        self.assertFalse(window.remove_markup_button.isEnabled())

    def test_the_buttons_call_the_model(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.remove_markup_button.click()
        window.mirror_joints_button.click()
        window.twist_button.click()
        self.assertEqual([call[0] for call in session.markup.calls], ["remove", "mirror_joints", "add_twist_joints"])

    def test_the_add_box_shows_only_with_unmarked_joints_and_counts_them(self):
        session = FakeSession(self.root)
        window = self.window(session)
        self.show_markup(window)
        self.assertTrue(window.add_box.isVisibleTo(window))
        self.assertEqual(window.add_markup_button.text(), "Add Markup to 1 Joint(s)")
        session.markup.unmarked = []
        session.markup.changed.emit()
        self.assertFalse(window.add_box.isVisibleTo(window))

    def test_add_markup_sends_the_forms_values_and_the_number_box(self):
        session = FakeSession(self.root)
        session.markup.unmarked = ["|c", "|d"]
        window = self.window(session)
        session.markup.changed.emit()
        self.assertTrue(window.number_check.isEnabled())
        window.add_form.editors["usage"].setEditText("spine")
        window.add_form.editors["side"].setCurrentIndex(window.add_form.editors["side"].findText("Left"))
        window.add_form.editors["skin"].click()
        self.assertTrue(window.number_check.isChecked(), "numbering is on by default")
        window.add_markup_button.click()
        self.assertEqual(session.markup.calls, [("add_markup", "spine", "Left", True, False, True)])

    def test_the_number_box_is_off_for_one_joint(self):
        window = self.window()
        self.assertFalse(window.number_check.isEnabled())
        self.assertFalse(window.number_check.isChecked())

    def test_editing_the_add_form_changes_nothing(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.add_form.editors["usage"].setEditText("spine")
        window.add_form.editors["usage"].lineEdit().editingFinished.emit()
        window.add_form.editors["export"].click()
        self.assertEqual(session.markup.calls, [])   # only Add Markup writes

    def test_warnings_show_only_when_there_are_some(self):
        session = FakeSession(self.root)
        window = self.window(session)
        self.show_markup(window)
        self.assertFalse(window.markup_warnings.isVisible())
        session.markup.warnings = ["2 joints share side Center and usage 'arm': a, b"]
        session.markup.changed.emit()
        self.assertTrue(window.markup_warnings.isVisible())
        self.assertIn("share side Center", window.markup_warnings.text())

    def test_selected_controls_are_listed_and_cannot_be_edited(self):
        window.number_check.setChecked(False)
        session.markup.changed.emit()
        self.assertFalse(window.number_check.isChecked(), "a choice is kept while several joints stay selected")
        session.markup.unmarked = ["|c"]
        session.markup.changed.emit()
        session.markup.unmarked = ["|c", "|d"]
        session.markup.changed.emit()
        self.assertTrue(window.number_check.isChecked(), "ticked again when several joints are selected")
        import rigmodules.query
        from PySide6 import QtWidgets
        session = FakeSession(self.root)
        session.markup.controls = [rigmodules.query.RigControl("hero:arm_00_L_CTRL", "hero:arm_00_L_MOD", "FkChain",
                                                               "Left", "arm", "hero:arm_00_R_CTRL")]
        window = self.window(session)
        self.show_markup(window)
        session.markup.changed.emit()
        model = window.controls_model
        self.assertEqual([model.data(model.index(0, c)) for c in range(5)],
                         ["hero:arm_00_L_CTRL", "hero:arm_00_L_MOD", "Left", "arm", "hero:arm_00_R_CTRL"])
        self.assertEqual(window.controls_table.editTriggers(), QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.assertTrue(window.controls_table.isVisibleTo(window))

    def test_the_controls_table_is_hidden_with_no_controls(self):
        window = self.window()
        self.assertFalse(window.controls_table.isVisibleTo(window))

    def test_a_markup_error_goes_to_the_status_line(self):
        session = FakeSession(self.root)
        window = self.window(session)
        session.markup.error = "That would give 2 joints side Left and usage 'arm'."
        window.markup_form.editors["skin"].click()
        self.assertEqual(window.status_label.text(), "That would give 2 joints side Left and usage 'arm'.")

    # ---- the Shapes tab ----

    def show_shapes(self, window):
        window.show()
        window.tabs.setCurrentWidget(window.shapes_tab)

    def test_the_tabs_are_files_markup_shapes_and_naming(self):
        window = self.window()
        self.assertEqual([window.tabs.tabText(i) for i in range(window.tabs.count())],
                         ["Files", "Markup", "Shapes", "Naming"])

    # ---- the Naming tab ----

    def test_the_naming_tab_shows_the_models_root_side_and_start_number(self):
        window = self.window()
        self.assertEqual(window.naming_base_edit.text(), "finger")
        self.assertEqual([window.naming_side_combo.itemText(i) for i in range(3)], ["Left", "Right", "Center"])
        self.assertEqual(window.naming_side_combo.currentText(), "Left")
        self.assertEqual(window.naming_start_spin.value(), 4)
        self.assertIn("3 node(s)", window.naming_summary.text())

    def test_the_start_number_defaults_to_zero_and_the_side_is_a_combo(self):
        session = FakeSession(self.root)
        session.naming.base, session.naming.side, session.naming.start_index = "", "Center", 0
        window = self.window(session)
        self.assertEqual((window.naming_start_spin.value(), window.naming_side_combo.currentText()), (0, "Center"))

    def test_rename_sends_the_root_side_and_start_number(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.naming_base_edit.setText("toe")
        window.naming_side_combo.setCurrentIndex(window.naming_side_combo.findData("Right"))
        window.naming_start_spin.setValue(2)
        window.rename_button.click()
        self.assertEqual(session.naming.calls, [("rename", "toe", "Right", 2)])
        self.assertEqual(window.status_label.text(), "Renamed 3 node(s)")

    def test_mirror_names_calls_the_model(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.naming_mirror_button.click()
        self.assertEqual(session.naming.calls, [("mirror",)])

    def test_naming_buttons_are_off_with_no_selection(self):
        session = FakeSession(self.root)
        session.naming.nodes = []
        window = self.window(session)
        session.naming.changed.emit()
        self.assertFalse(window.rename_button.isEnabled())
        self.assertFalse(window.naming_mirror_button.isEnabled())

    def test_a_naming_error_goes_to_the_status_line(self):
        session = FakeSession(self.root)
        window = self.window(session)
        session.naming.error = "arm_00_R_JNT is taken."
        window.rename_button.click()
        self.assertEqual(window.status_label.text(), "arm_00_R_JNT is taken.")

    def test_only_the_showing_naming_tab_reads_the_scene(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.show()
        window.tabs.setCurrentWidget(window.naming_tab)
        window.hide()
        self.assertEqual(session.naming.active, [False, True, False])

    def test_only_the_showing_tab_reads_the_scene(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.show()
        window.tabs.setCurrentWidget(window.shapes_tab)
        window.tabs.setCurrentWidget(window.markup_tab)
        window.hide()
        self.assertEqual(session.shapes.active, [False, True, False, False])
        self.assertEqual(session.markup.active, [False, False, True, False])

    def test_the_shape_choices_come_from_the_model_and_the_fields_show_their_states(self):
        from PySide6 import QtCore
        window = self.window()
        shape = window.appearance_form.editors["shapeType"]
        self.assertEqual([shape.itemText(i) for i in range(shape.count())], ["Box", "Sphere", "Circle"])
        self.assertEqual(shape.currentText(), "Sphere")
        self.assertEqual(window.appearance_form.editors["filled"].checkState(), QtCore.Qt.CheckState.PartiallyChecked)
        self.assertEqual(window.appearance_form.editors["wireframeAlpha"].text(), "0.5")
        self.assertEqual(window.transform_form.editors["scale"].text(), "2")
        self.assertEqual(window.transform_form.editors["translateX"].text(), "")
        self.assertEqual(window.transform_form.editors["translateX"].placeholderText(), "Mixed")
        self.assertEqual(window.transform_form.editors["rotateZ"].text(), "90")
        self.assertEqual(window.shapes_summary.text(), "2 rig control(s)")

    def test_an_edit_goes_to_the_model_with_the_mode(self):
        session = FakeSession(self.root)
        window = self.window(session)
        edit = window.transform_form.editors["translateY"]
        edit.setText("1.5")
        edit.setModified(True)
        edit.editingFinished.emit()
        window.shape_mode_combo.setCurrentIndex(window.shape_mode_combo.findData("adjust"))
        scale = window.transform_form.editors["scale"]
        scale.setText("1.2")
        scale.setModified(True)
        scale.editingFinished.emit()
        window.appearance_form.editors["filled"].click()
        self.assertEqual(session.shapes.calls, [("set_field", "translateY", 1.5, "set"),
                                                ("set_field", "scale", 1.2, "adjust"),
                                                ("set_field", "filled", True, "adjust")])

    def test_picking_a_shape_sends_its_name(self):
        session = FakeSession(self.root)
        window = self.window(session)
        shape = window.appearance_form.editors["shapeType"]
        shape.setCurrentIndex(shape.findText("Circle"))
        shape.activated.emit(shape.currentIndex())
        self.assertEqual(session.shapes.calls, [("set_field", "shapeType", "Circle", "set")])

    def test_showing_the_model_again_edits_nothing(self):
        session = FakeSession(self.root)
        window = self.window(session)
        session.shapes.changed.emit()
        session.changed.emit()
        self.assertEqual(session.shapes.calls, [])

    def test_the_forms_are_off_with_no_controls_selected(self):
        session = FakeSession(self.root)
        session.shapes.controls = []
        window = self.window(session)
        session.shapes.changed.emit()
        self.assertFalse(window.appearance_form.isEnabled())
        self.assertFalse(window.transform_form.isEnabled())

    def test_the_mirror_buttons_mirror_the_selected_controls_rigs_or_the_chosen_rig(self):
        session = FakeSession(self.root)
        session.files.rig_root = "hero:rigRootModule1"
        window = self.window(session)
        window.mirror_buttons["left_to_right"].click()
        window.mirror_buttons["right_to_left"].click()
        self.assertEqual(session.shapes.calls, [("mirror", True, "hero:rigRootModule1"),
                                                ("mirror", False, "hero:rigRootModule1")])

    def test_save_and_load_shapes_use_the_files_model_and_say_why_when_blocked(self):
        session = FakeSession(self.root)
        session.files.rows.append(row("shapes", "Control shapes", "rig", "game", load_blocked="Not saved yet."))
        window = self.window(session)
        session.changed.emit()
        window.save_shapes_button.click()
        self.assertTrue(window.save_shapes_button.isEnabled())
        self.assertFalse(window.load_shapes_button.isEnabled())
        self.assertEqual(window.load_shapes_button.toolTip(), "Not saved yet.")
        self.assertEqual(session.files.calls, [("save", "shapes")])

    def test_save_shapes_is_off_with_no_shapes_row(self):
        window = self.window()
        self.assertFalse(window.save_shapes_button.isEnabled())
        self.assertEqual(window.save_shapes_button.toolTip(), "No asset.")

    def test_a_shape_error_goes_to_the_status_line(self):
        session = FakeSession(self.root)
        window = self.window(session)
        session.shapes.error = "A scale of 0 flattens the shape. Use a small number."
        window.appearance_form.editors["filled"].click()
        self.assertEqual(window.status_label.text(), "A scale of 0 flattens the shape. Use a small number.")

    # ---- the window's life ----

    def test_the_session_watches_the_selection_only_while_shown(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.show()
        window.hide()
        self.assertEqual(session.watching, [True, False])

    def test_showing_reads_the_files_again(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.show()
        self.assertIn(("refresh",), session.files.calls)

    def test_closing_the_window_closes_the_session(self):
        session = FakeSession(self.root)
        window = self.window(session)
        window.show()
        window.close()
        self.assertIn(("close",), session.calls)

    def test_a_destroyed_window_closes_the_session_even_without_a_close_event(self):
        from PySide6 import QtCore, QtWidgets
        import bmaya.maya_ui.asseteditor
        session = FakeSession(self.root)
        window = bmaya.maya_ui.asseteditor.AssetEditor(session)
        window.show()
        window.deleteLater()
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertIn(("close",), session.calls)

    def test_show_window_makes_a_real_session_and_cleans_it_up(self):
        plugin = os.environ.get("RIGMODULES_PLUGIN", "")
        if not os.path.isfile(plugin):
            self.skipTest("set RIGMODULES_PLUGIN to a RigModules.mll")
        import maya.cmds as cmds
        if not cmds.pluginInfo(plugin, query=True, loaded=True):
            cmds.loadPlugin(plugin)
        import bmaya.core.asset.context
        import bmaya.maya.activerig
        import bmaya.maya.asseteditor
        import bmaya.maya.eventsregistry
        import bmaya.maya_ui.asseteditor
        self.addCleanup(lambda: bmaya.maya.activerig.ActiveRigTracker.current() and
                        bmaya.maya.activerig.ActiveRigTracker.current().stop())
        window = bmaya.maya_ui.asseteditor.show_window()
        self.addCleanup(window.deleteLater)
        self.assertIsNotNone(bmaya.core.asset.context.AssetContext.current())
        window.close()
        self.assertIsNone(bmaya.core.asset.context.AssetContext.current())
        callbacks = bmaya.maya.eventsregistry.EventsRegistry().callbacks
        self.assertEqual([key for key in callbacks if key.startswith(bmaya.maya.asseteditor.CALLBACK_PREFIX)], [])


class MixedForm(unittest.TestCase):
    """MixedFieldForm with every kind of field, on its own."""

    SPECS = None

    def form(self):
        from bmaya.core.fieldset import FieldSpec
        import bmaya.maya_ui.assetwidgets
        specs = (FieldSpec("kind", "Kind", "choice", ("A", "B")), FieldSpec("name", "Name", "text", ("x", "y")),
                 FieldSpec("on", "On", "bool"), FieldSpec("size", "Size", "float"))
        form = bmaya.maya_ui.assetwidgets.MixedFieldForm(specs)
        self.addCleanup(form.deleteLater)
        edits = []
        form.field_edited.connect(lambda name, value: edits.append((name, value)))
        return form, edits

    def test_a_float_field_emits_the_number_typed_and_not_for_an_untouched_field(self):
        form, edits = self.form()
        form.editors["size"].editingFinished.emit()
        self.assertEqual(edits, [])
        form.editors["size"].setText("2.5")
        form.editors["size"].setModified(True)
        form.editors["size"].editingFinished.emit()
        self.assertEqual(edits, [("size", 2.5)])

    def test_a_float_field_shows_a_value_or_mixed(self):
        from bmaya.core.fieldset import FieldState
        form, edits = self.form()
        form.set_state("size", FieldState(0.5, False, 2))
        self.assertEqual(form.editors["size"].text(), "0.5")
        form.set_state("size", FieldState(None, True, 2))
        self.assertEqual((form.editors["size"].text(), form.editors["size"].placeholderText()), ("", "Mixed"))
        self.assertEqual(edits, [])

    def test_values_reads_what_is_shown_with_none_for_blank_and_mixed(self):
        from bmaya.core.fieldset import FieldState
        form, _edits = self.form()
        form.set_states({"kind": FieldState("B", False, 1), "name": FieldState(None, True, 2),
                         "on": FieldState(None, True, 2), "size": FieldState(3.0, False, 1)})
        self.assertEqual(form.values(), {"kind": "B", "name": None, "on": None, "size": 3.0})

    def test_a_state_never_set_is_blank(self):
        form, _edits = self.form()
        form.set_states({})
        self.assertEqual(form.values(), {"kind": None, "name": None, "on": False, "size": None})

    def test_clicking_a_mixed_box_makes_it_a_plain_value(self):
        from bmaya.core.fieldset import FieldState
        form, edits = self.form()
        form.set_state("on", FieldState(None, True, 2))
        form.editors["on"].click()
        self.assertEqual(edits, [("on", True)])
        form.editors["on"].click()
        self.assertEqual(edits[-1], ("on", False))

    def test_the_suggestions_of_a_text_field_can_be_replaced_without_losing_the_text(self):
        form, _edits = self.form()
        form.editors["name"].setEditText("typed")
        form.set_options("name", ["p", "q", "r"])
        combo = form.editors["name"]
        self.assertEqual(([combo.itemText(i) for i in range(combo.count())], combo.currentText()),
                         (["p", "q", "r"], "typed"))

    def test_the_text_field_does_not_emit_an_unchanged_value_or_a_blank_one(self):
        from bmaya.core.fieldset import FieldState
        form, edits = self.form()
        form.set_state("name", FieldState("x", False, 1))
        form.editors["name"].lineEdit().editingFinished.emit()
        form.editors["name"].setEditText("  ")
        form.editors["name"].lineEdit().editingFinished.emit()
        self.assertEqual(edits, [])


if __name__ == "__main__":
    unittest.main()
