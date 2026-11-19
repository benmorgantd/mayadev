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

    def build_rig(self):
        self._record("build_rig")
        return "hero_game:rigRootModule1"

    def refresh(self):
        self.calls.append(("refresh",))


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

    def test_a_file_without_save_or_load_has_no_buttons(self):
        window = self.window()
        self.assertNotIn(("template", "save"), window.files_table.buttons)
        self.assertNotIn(("template", "load"), window.files_table.buttons)
        self.assertIn(("skeleton", "save"), window.files_table.buttons)

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

    def test_build_rig_calls_the_files_model_and_is_disabled_with_no_rig(self):
        window = self.window()
        window.build_button.click()
        self.assertIn(("build_rig",), window.session.files.calls)
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


if __name__ == "__main__":
    unittest.main()
