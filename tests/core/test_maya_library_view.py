"""The library browser's window and the tags editor, offscreen in mayapy, over a fake session (RigModules D51,
design/library-browser.md). The session is tested against real rigs in tests/asset/test_maya_library_session.py, so no
plugin is needed here: this checks the wiring.

Run with tests/core/run.bat (the Maya half), or: mayapy -m unittest discover -s tests/core -p "test_maya_*.py"
"""

import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

try:
    import maya.standalone
except ImportError:
    maya = None


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


def make_entry(name, kind="pose", source="user", tags=(), error="", unmatched=(), modified=1_700_000_000.0,
               start=1.0, end=1.0, **meta):
    import bmaya.core.asset.library as library
    file = library.LibraryFile(f"C:/lib/{source}/{name}.json", name, kind, source, source == "user", modified, False)
    info = library.FileInfo(error=error, kind=kind, meta={"tags": list(tags), **meta}, frame_rate=24.0, start_frame=start,
                            end_frame=end, control_count=42, channel_count=318, unmatched_controls=tuple(unmatched))
    return library.LibraryEntry(file, info)


class FakeSession:
    """The LibrarySession surface the window reads and calls. Every command is recorded."""

    def __init__(self, entries=(), kind="pose", masks=(), sources=("approved", "shared", "user")):
        import bmaya.core.asset.library as library
        import bmaya.core.observable
        self.changed = bmaya.core.observable.Event()
        self.rig_root, self.asset_id, self.rig_name, self.reason = "hero:rigRoot", "shooter\\hero", "game", ""
        self.kind, self.query, self.scope = kind, "", None
        self.sources = [library.LibrarySource(key, key.capitalize(), {}, key == "user") for key in sources]
        self.source_enabled = {}
        self.entries, self.selected, self.masks = list(entries), None, list(masks)
        self.calls, self.error, self.taken = [], None, set()
        self.warnings = {}
        self.tag_values = ["hands", "fist"]
        self.suggestion = "pose_001"

    def _record(self, *call):
        if self.error:
            raise RuntimeError(self.error)
        self.calls.append(call)

    # reading
    def details(self, entry):
        if entry.info.error:
            return [entry.info.error]
        return [f"{entry.info.control_count} controls, {entry.info.channel_count} channels, 0 unmatched.",
                *self.warnings.get(entry.name, [])]

    def facets(self):
        return {"tag": self.tag_values, "template": ["Human"], "region": [], "status": ["review"], "category": []}

    def suggest_name(self): return self.suggestion
    def name_taken(self, name): return name in self.taken
    def playback_range(self): return (1, 48)
    def current_frame(self): return 12.0
    def close(self): self.calls.append(("close",))

    # what the window sets
    def refresh(self): self._record("refresh")

    def set_kind(self, kind):
        self._record("set_kind", kind)
        self.kind = kind
        self.changed.emit()

    def set_query(self, text):
        self._record("set_query", text)
        self.query = text
        self.changed.emit()

    def set_source_enabled(self, key, enabled):
        self._record("set_source_enabled", key, enabled)
        self.source_enabled[key] = enabled
        self.changed.emit()

    def set_scope(self, scope):
        self._record("set_scope", scope)
        self.scope = scope
        self.changed.emit()

    def select(self, entry):
        self._record("select", entry.name if entry else None)
        self.selected = entry
        self.changed.emit()

    # commands
    def apply(self, mirror=False, start_frame=None, blend=1.0):
        call = ("apply", self.selected.name if self.selected else None, mirror, start_frame)
        self._record(*call, *(() if blend == 1.0 else (blend,)))
        return ["a", "b", "c"]

    def begin_blend(self, mirror=False):
        self._record("begin_blend", self.selected.name if self.selected else None, mirror)
        return FakeBlend(self)

    def save(self, name, tags=(), description="", replace=False, start_frame=None, end_frame=None):
        self._record("save", name, tags, replace)
        self.changed.emit()   # the real save refreshes the library, and the window reads it again

    def rename(self, entry, name): self._record("rename", entry.name, name)
    def delete(self, entry): self._record("delete", entry.name)
    def copy_to_user(self, entry): self._record("copy_to_user", entry.name)
    def set_meta(self, entry, tags=None, description=None): self._record("set_meta", entry.name, tags, description)
    def save_mask(self, mask): self._record("save_mask", mask.name)
    def delete_mask(self, name): self._record("delete_mask", name)

    def mask_from_selection(self, name):
        import bmaya.core.asset.library as library
        self._record("mask_from_selection", name)
        return library.Mask(name, (library.MaskItem(side="Left"),), "user")


class FakeBlend:
    """posetools.PoseBlend's surface: records set and end on its session."""

    def __init__(self, session):
        self.session, self.file, self.weight = session, "C:/lib/user/fist.json", 0.0

    def set(self, weight):
        self.weight = weight
        self.session._record("blend_set", weight)

    def end(self, cancel=False):
        self.session._record("blend_end", cancel)


class BrowserTest(unittest.TestCase):

    def browser(self, session, answers=()):
        import bmaya.core.prompts
        import bmaya.maya_ui.librarybrowser
        self.asker = bmaya.core.prompts.ScriptedPrompter(answers)
        browser = bmaya.maya_ui.librarybrowser.LibraryBrowser(session, asker=self.asker)
        self.addCleanup(browser.deleteLater)
        browser.resize(500, 700)
        browser.show()
        return browser

    def names(self, browser):
        return [browser.proxy.data(browser.proxy.index(row, 0)) for row in range(browser.proxy.rowCount())]

    def cell(self, browser, row, column):
        return browser.proxy.data(browser.proxy.index(row, column))

    def entries(self):
        return [
            make_entry("fist", tags=["hands", "fist"], template="Human", author="bm", modified=1_700_000_000.0),
            make_entry("idle", source="approved", tags=["body"], template="Human", modified=1_700_100_000.0),
            make_entry("wave", source="shared", modified=1_699_000_000.0),
        ]

    def select_row(self, browser, row):
        browser.table.selectRow(row)


class Listing(BrowserTest):

    def test_a_row_shows_its_entry_in_the_columns_of_the_details_view(self):
        entry = make_entry("run", kind="animation", tags=["loco", "run"], template="Human", author="bm", start=5, end=30,
                           modified=1_700_000_000.0)
        browser = self.browser(FakeSession([entry], kind="animation"))
        self.assertEqual([self.cell(browser, 0, column) for column in range(7)],
                         ["run", "loco, run", "User", "Human", "bm", "2023-11-14", "5-30"])
        self.assertEqual([browser.proxy.headerData(c, browser.table.horizontalHeader().orientation()) for c in range(7)],
                         ["Name", "Tags", "Source", "Template", "Author", "Date", "Frames"])

    def test_list_shows_name_and_source_and_details_shows_every_column(self):
        browser = self.browser(FakeSession(self.entries()))
        hidden = lambda: [column for column in range(7) if browser.table.isColumnHidden(column)]
        self.assertEqual(hidden(), [1, 3, 4, 5, 6])
        browser.view_buttons["Details"].click()
        self.assertEqual(hidden(), [])
        browser.view_buttons["List"].click()
        self.assertEqual(hidden(), [1, 3, 4, 5, 6])

    def test_the_kind_icon_is_in_the_name_column_only_and_differs_by_kind(self):
        from PySide6 import QtCore
        browser = self.browser(FakeSession([make_entry("a")]))
        decoration = QtCore.Qt.ItemDataRole.DecorationRole
        self.assertFalse(browser.proxy.data(browser.proxy.index(0, 0), decoration).isNull())
        self.assertIsNone(browser.proxy.data(browser.proxy.index(0, 2), decoration))
        pose = browser.proxy.data(browser.proxy.index(0, 0), decoration).pixmap(16, 16).toImage()
        other = self.browser(FakeSession([make_entry("a", kind="animation")], kind="animation"))
        animation = other.proxy.data(other.proxy.index(0, 0), decoration).pixmap(16, 16).toImage()
        self.assertNotEqual(pose, animation)

    def test_a_broken_file_is_red_and_a_file_with_unmatched_controls_is_amber(self):
        from PySide6 import QtCore
        import bmaya.maya_ui.theme as theme
        browser = self.browser(FakeSession([make_entry("a_broken", error="bad json"), make_entry("b_partial", unmatched=[("Left", "arm")]),
                                            make_entry("c_fine")]))
        colour = lambda row: browser.proxy.data(browser.proxy.index(row, 0), QtCore.Qt.ItemDataRole.ForegroundRole)
        self.assertEqual(colour(0).name(), theme.DARK.error)
        self.assertEqual(colour(1).name(), theme.DARK.warning)
        self.assertIsNone(colour(2))
        tip = browser.proxy.data(browser.proxy.index(0, 0), QtCore.Qt.ItemDataRole.ToolTipRole)
        self.assertEqual(tip, "bad json")

    def test_a_header_click_sorts_by_the_columns_key_and_the_selection_stays_on_its_entry(self):
        from PySide6 import QtCore
        browser = self.browser(FakeSession(self.entries()))
        self.assertEqual(self.names(browser), ["fist", "idle", "wave"])
        self.select_row(browser, 0)
        browser.table.sortByColumn(5, QtCore.Qt.SortOrder.DescendingOrder)   # the date
        self.assertEqual(self.names(browser), ["idle", "fist", "wave"])
        self.assertEqual(browser._selected_entry().name, "fist")

    def test_an_entry_list_that_changes_keeps_the_selection_by_path(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.select_row(browser, 1)
        self.assertEqual(session.selected.name, "idle")
        session.calls.clear()
        session.entries = [make_entry("aaa")] + self.entries()   # a reset: new rows, the same file
        session.changed.emit()
        self.assertEqual(browser._selected_entry().name, "idle")
        self.assertEqual(session.calls, [], "showing the session is not the user selecting")

    def test_a_selection_the_session_drops_clears_the_row(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.select_row(browser, 0)
        session.selected = None
        session.entries = session.entries[1:]
        session.changed.emit()
        self.assertIsNone(browser._selected_entry())

    def test_sources_get_a_chip_each_and_a_click_switches_the_source(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.assertEqual(list(browser.source_buttons), ["approved", "shared", "user"])
        self.assertTrue(all(button.isChecked() for button in browser.source_buttons.values()))
        browser.source_buttons["shared"].click()
        self.assertEqual(session.calls, [("set_source_enabled", "shared", False)])
        self.assertFalse(browser.source_buttons["shared"].isChecked())

    def test_no_rig_shows_the_reason_and_disables_the_body(self):
        session = FakeSession()
        session.rig_root, session.asset_id, session.reason = None, None, "There is no active rig."
        browser = self.browser(session)
        self.assertTrue(browser.empty_label.isVisible())
        self.assertEqual(browser.empty_label.text(), "There is no active rig.")
        self.assertFalse(browser.body.isEnabled())
        self.assertTrue(browser.refresh_button.isEnabled())
        session.rig_root, session.asset_id, session.reason = "hero:rigRoot", "shooter\\hero", ""
        session.changed.emit()
        self.assertFalse(browser.empty_label.isVisible())
        self.assertTrue(browser.body.isEnabled())
        self.assertEqual(browser.rig_label.text(), "shooter\\hero  (game)", "the library is the rig's, so the rig is named")

    def test_the_tabs_set_the_kind_and_follow_the_session(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.assertEqual([browser.kind_tabs.tabText(i) for i in range(2)], ["Poses", "Animations"])
        browser.kind_tabs.setCurrentIndex(1)
        self.assertEqual(session.calls, [("set_kind", "animation")])
        session.calls.clear()
        session.kind = "pose"
        session.changed.emit()
        self.assertEqual((browser.kind_tabs.currentIndex(), session.calls), (0, []))

    def test_typing_in_the_search_box_sets_the_query_and_the_session_query_fills_it(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        browser.search_edit.setText("tag:fist")
        self.assertEqual(session.calls, [("set_query", "tag:fist")])
        session.calls.clear()
        session.query = "template:Human"
        session.changed.emit()
        self.assertEqual((browser.search_edit.text(), session.calls), ("template:Human", []))


class Filtering(BrowserTest):

    def facet_actions(self, browser, field):
        browser.fill_filter_menu()
        menu = next(action.menu() for action in browser.filter_menu.actions() if action.text() == field)
        return {action.text(): action for action in menu.actions()}

    def test_the_filter_menu_lists_each_facet_with_the_values_in_use(self):
        browser = self.browser(FakeSession(self.entries()))
        browser.fill_filter_menu()
        self.assertEqual([(a.text(), a.isEnabled()) for a in browser.filter_menu.actions()],
                         [("Tag", True), ("Template", True), ("Region", False), ("Status", True), ("Category", False)])
        self.assertEqual(list(self.facet_actions(browser, "Tag")), ["hands", "fist"])

    def test_a_pick_writes_its_term_in_the_search_box_and_a_second_pick_takes_it_out(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        browser.search_edit.setText("wave")
        self.facet_actions(browser, "Tag")["fist"].trigger()
        self.assertEqual(browser.search_edit.text(), "wave tag:fist")
        self.assertEqual(session.query, "wave tag:fist")
        self.assertTrue(self.facet_actions(browser, "Tag")["fist"].isChecked())
        self.assertFalse(self.facet_actions(browser, "Tag")["hands"].isChecked())
        self.facet_actions(browser, "Tag")["fist"].trigger()
        self.assertEqual(browser.search_edit.text(), "wave")


class Applying(BrowserTest):

    def test_only_a_double_click_or_return_applies_and_a_click_or_arrow_key_only_selects(self):
        from PySide6 import QtCore, QtTest
        session = FakeSession(self.entries())
        browser = self.browser(session)
        center = browser.table.visualRect(browser.proxy.index(1, 0)).center()
        QtTest.QTest.mouseClick(browser.table.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=center)
        QtTest.QTest.keyClick(browser.table, QtCore.Qt.Key.Key_Down)
        self.assertEqual([call[0] for call in session.calls], ["select", "select"])
        self.assertFalse([call for call in session.calls if call[0] == "apply"])

        QtTest.QTest.keyClick(browser.table, QtCore.Qt.Key.Key_Return)
        self.assertEqual(session.calls[-1], ("apply", "wave", False, None))
        QtTest.QTest.mouseDClick(browser.table.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=center)
        self.assertEqual([call[0] for call in session.calls].count("apply"), 2)
        self.assertEqual(browser.status_label.text(), "Applied wave to 3 controls.")

    def test_the_apply_button_applies_with_mirror_and_is_off_without_a_usable_selection(self):
        session = FakeSession(self.entries() + [make_entry("bad", error="broken")])
        browser = self.browser(session)
        self.assertFalse(browser.apply_button.isEnabled())
        self.select_row(browser, 0)   # bad
        self.assertFalse(browser.apply_button.isEnabled(), "a file that can't be read can't be applied")
        self.select_row(browser, 1)
        self.assertTrue(browser.apply_button.isEnabled())
        browser.mirror_box.setChecked(True)
        browser.apply_button.click()
        self.assertEqual(session.calls[-1], ("apply", "fist", True, None))

    def test_start_at_is_for_animations_and_now_fills_the_current_frame(self):
        pose = self.browser(FakeSession(self.entries()))
        self.assertFalse(pose.start_edit.isVisible())
        session = FakeSession([make_entry("run", kind="animation", start=5, end=30)], kind="animation")
        browser = self.browser(session)
        self.assertTrue(all(w.isVisible() for w in (browser.start_label, browser.start_edit, browser.now_button, browser.range_label)))
        self.assertEqual(browser.range_label.text(), "Saves frames 1-48, the playback range.")
        self.select_row(browser, 0)
        browser.apply_button.click()
        self.assertEqual(session.calls[-1], ("apply", "run", False, None), "empty means the animation's own start")
        browser.now_button.click()
        self.assertEqual(browser.start_edit.text(), "12")
        browser.apply_button.click()
        self.assertEqual(session.calls[-1], ("apply", "run", False, 12.0))

    def test_a_session_error_is_logged_and_shown_and_does_not_reach_qt(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.select_row(browser, 0)
        session.error = "Select controls of the active rig, or choose another scope."
        with mock.patch("bmaya.core.log.error") as error:
            browser.apply_button.click()
        error.assert_called_once_with("Select controls of the active rig, or choose another scope.")
        self.assertEqual(browser.status_error_label.text(), "Select controls of the active rig, or choose another scope.")
        self.assertTrue(browser.status_error_label.isVisible() and not browser.status_label.isVisible())
        browser.set_status("Done.")
        self.assertTrue(browser.status_label.isVisible() and not browser.status_error_label.isVisible())

    def test_the_details_show_the_summary_the_origin_and_warnings(self):
        session = FakeSession(self.entries())
        session.warnings["fist"] = ["The rig has no control for Left tail."]
        browser = self.browser(session)
        self.select_row(browser, 0)
        self.assertEqual(browser.summary_label.text(), "42 controls, 318 channels, 0 unmatched.")
        self.assertEqual(browser.warning_label.text(), "The rig has no control for Left tail.")
        self.assertIn("Template Human.", browser.origin_label.text())
        self.assertIn("By bm", browser.origin_label.text())
        self.select_row(browser, 2)
        self.assertEqual(browser.warning_label.text(), "")

    def test_the_details_of_a_broken_file_are_its_error(self):
        browser = self.browser(FakeSession([make_entry("bad", error="Not a pose file.")]))
        self.select_row(browser, 0)
        self.assertEqual((browser.summary_label.text(), browser.warning_label.text(), browser.error_label.text()),
                         ("", "", "Not a pose file."))
        self.assertTrue(browser.error_label.isVisible() and not browser.summary_label.isVisible())

    def test_the_scope_combo_lists_the_scopes_then_the_masks_and_picking_sets_the_scope(self):
        import bmaya.core.asset.library as library
        masks = [library.Mask("Hands", (library.MaskItem(usage="hand"),), "rig"),
                 library.Mask("Upper", (library.MaskItem(side="Left"),), "team"),
                 library.Mask("Mine", (library.MaskItem(side="Right"),), "user")]
        session = FakeSession(self.entries(), masks=masks)
        browser = self.browser(session)
        self.assertEqual([browser.scope_combo.itemText(i) for i in range(browser.scope_combo.count())],
                         ["Auto (selection, else rig)", "Selection", "Whole rig", "Mask: Hands", "Mask: Upper (team)",
                          "Mask: Mine (mine)"])
        browser.scope_combo.setCurrentIndex(4)
        self.assertEqual(session.calls, [("set_scope", "Upper")])
        session.calls.clear()
        session.scope = None
        session.changed.emit()
        self.assertEqual((browser.scope_combo.currentIndex(), session.calls), (0, []))

    def test_save_mask_asks_a_name_saves_the_mask_and_makes_it_the_scope(self):
        session = FakeSession(self.entries())
        browser = self.browser(session, answers=["Left arm"])
        browser.save_mask_action.trigger()
        self.assertEqual(session.calls, [("mask_from_selection", "Left arm"), ("save_mask", "Left arm"), ("set_scope", "Left arm")])
        self.assertEqual(self.asker.asked[0].title, "Save Mask")

    def test_a_cancelled_mask_name_does_nothing_and_only_a_users_own_mask_can_be_deleted(self):
        import bmaya.core.asset.library as library
        masks = [library.Mask("Hands", (library.MaskItem(usage="hand"),), "rig"),
                 library.Mask("Upper", (library.MaskItem(side="Left"),), "team"),
                 library.Mask("Mine", (library.MaskItem(side="Right"),), "user")]
        session = FakeSession(self.entries(), masks=masks)
        browser = self.browser(session, answers=[None, True])
        browser.save_mask_action.trigger()
        self.assertEqual(session.calls, [])
        for name, deletable in (("Hands", False), ("Upper", False), ("Mine", True), (None, False)):
            session.scope = name
            session.changed.emit()
            self.assertEqual(browser.delete_mask_action.isEnabled(), deletable, name)
        session.scope = "Mine"
        session.changed.emit()
        browser.delete_mask_action.trigger()
        self.assertEqual(session.calls, [("delete_mask", "Mine")])
        self.assertEqual([question.kind for question in self.asker.asked], ["ask_text", "confirm"])


class Saving(BrowserTest):

    def test_the_name_is_prefilled_with_a_free_name_and_a_typed_name_is_kept(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.assertEqual(browser.name_edit.text(), "pose_001")
        session.suggestion = "pose_002"
        session.changed.emit()
        self.assertEqual(browser.name_edit.text(), "pose_002", "an untouched suggestion follows the library")
        browser.name_edit.setText("wave_hello")
        session.suggestion = "pose_003"
        session.changed.emit()
        self.assertEqual(browser.name_edit.text(), "wave_hello")

    def test_enter_in_the_name_field_saves_with_the_tags_and_the_next_name_is_offered(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        browser.name_edit.setText("fist_angry")
        browser.tags_edit.setText("hands, fist,  angry ,")
        session.suggestion = "pose_002"
        browser.name_edit.returnPressed.emit()
        self.assertEqual(session.calls, [("save", "fist_angry", ("hands", "fist", "angry"), False)])
        self.assertEqual((browser.name_edit.text(), browser.tags_edit.text()), ("pose_002", ""))
        self.assertEqual(browser.status_label.text(), "Saved fist_angry.")

    def test_the_save_button_and_enter_in_the_tags_field_save_too(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        browser.save_button.click()
        browser.tags_edit.returnPressed.emit()
        self.assertEqual([call[:2] for call in session.calls], [("save", "pose_001"), ("save", "pose_001")])

    def test_a_taken_name_asks_before_it_replaces(self):
        session = FakeSession(self.entries())
        session.taken = {"wave"}
        browser = self.browser(session, answers=[False, True])
        browser.name_edit.setText("wave")
        browser.save_button.click()
        self.assertEqual(session.calls, [], "declined: nothing is saved")
        self.assertEqual(browser.name_edit.text(), "wave")
        browser.save_button.click()
        self.assertEqual(session.calls, [("save", "wave", (), True)])
        self.assertEqual([question.kind for question in self.asker.asked], ["confirm", "confirm"])
        self.assertIn("already have a pose called 'wave'", self.asker.asked[0].message)

    def test_a_refused_name_is_logged_and_shown(self):
        session = FakeSession(self.entries())
        session.error = "'a/b' is not a name."
        browser = self.browser(session)
        browser.name_edit.setText("a/b")
        with mock.patch("bmaya.core.log.error") as error:
            browser.save_button.click()
        error.assert_called_once_with("'a/b' is not a name.")
        self.assertEqual(browser.name_edit.text(), "a/b")

    def test_the_tags_field_offers_the_tags_in_use(self):
        browser = self.browser(FakeSession(self.entries()))
        self.assertEqual(browser.tags_edit._model.stringList(), ["hands", "fist"])


class Menu(BrowserTest):

    def actions(self, browser, entry):
        return {action.text(): action for action in browser.entry_menu(entry).actions()}

    def test_a_users_file_can_be_renamed_edited_and_deleted_but_not_copied_to_the_user(self):
        entry = self.entries()[0]
        actions = self.actions(self.browser(FakeSession([entry])), entry)
        self.assertEqual({text: action.isEnabled() for text, action in actions.items()},
                         {"Apply": True, "Blend": True, "Copy to My Library": False, "Rename...": True,
                          "Edit Tags and Description...": True, "Delete": True})

    def test_an_approved_or_shared_file_can_only_be_applied_and_copied(self):
        for entry in self.entries()[1:]:
            actions = self.actions(self.browser(FakeSession([entry])), entry)
            self.assertEqual({text for text, action in actions.items() if action.isEnabled()},
                             {"Apply", "Blend", "Copy to My Library"})

    def test_a_pose_has_a_blend_submenu_that_adds_or_subtracts_from_the_current_pose(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        entry = self.entries()[0]
        self.select_row(browser, 0)
        actions = self.actions(browser, entry)
        self.assertEqual(list(actions)[:2], ["Apply", "Blend"])
        blend = {action.text(): action for action in actions["Blend"].menu().actions()}
        self.assertEqual(list(blend), ["Add 25%", "Add 50%", "Add 75%", "Subtract 25%", "Subtract 50%", "Subtract 75%"])
        blend["Subtract 25%"].trigger()
        blend["Add 75%"].trigger()
        self.assertEqual([call for call in session.calls if call[0] == "apply"],
                         [("apply", "fist", False, None, -0.25), ("apply", "fist", False, None, 0.75)])

    def test_an_animation_has_no_blend_submenu(self):
        entry = make_entry("walk", kind="animation")
        self.assertNotIn("Blend", self.actions(self.browser(FakeSession([entry], kind="animation")), entry))


    def test_each_item_calls_its_session_command(self):
        session = FakeSession(self.entries())
        browser = self.browser(session, answers=["clench", True])
        user, approved = self.entries()[0], self.entries()[1]
        actions = self.actions(browser, user)
        actions["Rename..."].trigger()
        actions["Delete"].trigger()
        self.actions(browser, approved)["Copy to My Library"].trigger()
        self.assertEqual(session.calls, [("rename", "fist", "clench"), ("delete", "fist"), ("copy_to_user", "idle")])
        self.assertEqual([question.title for question in self.asker.asked], ["Rename", "Delete"])

    def test_a_cancelled_or_unchanged_rename_and_a_declined_delete_do_nothing(self):
        session = FakeSession(self.entries())
        browser = self.browser(session, answers=[None, "fist", False])
        actions = self.actions(browser, self.entries()[0])
        actions["Rename..."].trigger()
        actions["Rename..."].trigger()
        actions["Delete"].trigger()
        self.assertEqual(session.calls, [])

    def test_edit_tags_and_description_sends_what_the_dialog_holds(self):
        from PySide6 import QtWidgets
        import bmaya.maya_ui.librarybrowser as view
        session = FakeSession(self.entries())
        browser = self.browser(session)
        entry = self.entries()[0]

        def accept_with_changes(dialog):
            self.assertEqual((dialog.tags(), dialog.description()), (["hands", "fist"], ""))
            dialog.tags_edit.setText("hands, fist, angry")
            dialog.description_edit.setPlainText("  Clenched  ")
            return QtWidgets.QDialog.DialogCode.Accepted

        with mock.patch.object(view.EditMetaDialog, "exec", accept_with_changes):
            self.actions(browser, entry)["Edit Tags and Description..."].trigger()
        self.assertEqual(session.calls, [("set_meta", "fist", ["hands", "fist", "angry"], "Clenched")])
        session.calls.clear()
        with mock.patch.object(view.EditMetaDialog, "exec", lambda dialog: QtWidgets.QDialog.DialogCode.Rejected):
            self.actions(browser, entry)["Edit Tags and Description..."].trigger()
        self.assertEqual(session.calls, [])

    def test_a_right_click_selects_the_row_under_it(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        position = browser.table.visualRect(browser.proxy.index(2, 0)).center()
        with mock.patch.object(browser, "entry_menu") as menu:
            browser.table.customContextMenuRequested.emit(position)
        self.assertEqual(session.selected.name, "wave")
        menu.assert_called_once_with(session.entries[2])
        menu.return_value.exec.assert_called_once()


class Lifecycle(BrowserTest):

    def test_the_window_reads_the_library_again_each_time_it_opens_but_not_the_first_time(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.assertEqual(session.calls, [])
        browser.hide()
        browser.show()
        self.assertEqual(session.calls, [("refresh",)])

    def test_the_refresh_button_refreshes(self):
        session = FakeSession(self.entries())
        self.browser(session).refresh_button.click()
        self.assertEqual(session.calls, [("refresh",)])

    def test_a_destroyed_window_closes_its_session(self):
        """A docked window is destroyed with its workspace control, often with no closeEvent."""
        from PySide6 import QtCore, QtWidgets
        import bmaya.maya_ui.librarybrowser
        session = FakeSession(self.entries())
        browser = bmaya.maya_ui.librarybrowser.LibraryBrowser(session)
        browser.show()
        browser.deleteLater()
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(session.calls, [("close",)])

    def test_show_window_opens_a_browser_on_a_session_by_its_object_name(self):
        import bmaya.maya.librarybrowser
        import bmaya.maya_ui.host
        import bmaya.maya_ui.librarybrowser
        with mock.patch.object(bmaya.maya.librarybrowser, "LibrarySession", return_value=FakeSession(self.entries())):
            window = bmaya.maya_ui.librarybrowser.show_window()
        self.addCleanup(window.deleteLater)
        self.assertIs(bmaya.maya_ui.host.find(bmaya.maya_ui.librarybrowser.OBJECT_NAME), window)


class TagsEditTest(unittest.TestCase):

    def edit(self, tags_in_use=("hands", "fist", "Hard hit")):
        from bmaya.maya_ui.widgets import TagsEdit
        edit = TagsEdit()
        self.addCleanup(edit.deleteLater)
        edit.set_tags_in_use(list(tags_in_use))
        return edit

    def test_tags_are_trimmed_and_unique_and_in_order(self):
        edit = self.edit()
        edit.setText(" hands ,fist,, hands , angry,")
        self.assertEqual(edit.tags(), ["hands", "fist", "angry"])
        edit.set_tags(["a", "b"])
        self.assertEqual(edit.text(), "a, b")
        edit.setText("")
        self.assertEqual(edit.tags(), [])

    def test_the_word_before_the_cursor_is_the_tag_being_typed(self):
        edit = self.edit()
        edit.setText("hands, fi")
        edit.setCursorPosition(len(edit.text()))
        self.assertEqual(edit.word_before_cursor(), "fi")
        edit.setText("hands, ")
        edit.setCursorPosition(len(edit.text()))
        self.assertEqual(edit.word_before_cursor(), "")
        edit.setText("hands, fist")
        edit.setCursorPosition(3)
        self.assertEqual(edit.word_before_cursor(), "han", "only what is left of the cursor")

    def test_picking_a_completion_replaces_the_word_under_the_cursor_only(self):
        edit = self.edit()
        edit.setText("hands, fi")
        edit.setCursorPosition(len(edit.text()))
        edit.complete_word("fist")
        self.assertEqual((edit.text(), edit.cursorPosition()), ("hands, fist", len("hands, fist")))
        edit.setText("ha, fist")
        edit.setCursorPosition(2)
        edit.complete_word("hands")
        self.assertEqual((edit.text(), edit.tags()), ("hands, fist", ["hands", "fist"]))
        edit.setText("fi")
        edit.setCursorPosition(2)
        edit.complete_word("fist")
        self.assertEqual(edit.text(), "fist", "the first tag gets no leading space")

    def test_typing_offers_the_tags_in_use_that_start_with_the_word(self):
        from PySide6 import QtCore, QtTest
        edit = self.edit()
        edit.show()
        edit.setText("hands, fi")
        edit.setCursorPosition(len(edit.text()))
        edit._offer()
        completer = edit._completer
        self.assertEqual(completer.completionPrefix(), "fi", "the word being typed, not the whole text")
        self.assertEqual([completer.completionModel().index(row, 0).data() for row in range(completer.completionCount())], ["fist"])
        edit.setText("hard")
        edit.setCursorPosition(4)
        edit._offer()
        self.assertEqual([completer.completionModel().index(row, 0).data() for row in range(completer.completionCount())],
                         ["Hard hit"], "case does not matter")
        QtTest.QTest.keyClick(edit, QtCore.Qt.Key.Key_Escape)


if __name__ == "__main__":
    unittest.main()


class Blending(BrowserTest):

    def test_the_slider_is_for_poses_and_needs_a_usable_selection(self):
        browser = self.browser(FakeSession(self.entries() + [make_entry("bad", error="broken")]))
        self.assertTrue(browser.blend_slider.isVisible())
        self.assertFalse(browser.blend_slider.isEnabled())
        self.select_row(browser, 0)   # bad
        self.assertFalse(browser.blend_slider.isEnabled())
        self.select_row(browser, 1)
        self.assertTrue(browser.blend_slider.isEnabled())
        animation = self.browser(FakeSession([make_entry("walk", kind="animation")], kind="animation"))
        self.assertFalse(animation.blend_slider.isVisible())

    def test_a_drag_begins_on_press_sets_each_move_and_ends_and_springs_back_on_release(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.select_row(browser, 0)
        browser.mirror_box.setChecked(True)
        slider = browser.blend_slider
        slider.sliderPressed.emit()
        slider.sliderMoved.emit(50)
        slider.sliderMoved.emit(-100)
        slider.sliderMoved.emit(130)
        self.assertEqual(browser.blend_value_label.text(), "130%")
        slider.sliderReleased.emit()
        self.assertEqual(session.calls[-5:], [("begin_blend", "fist", True), ("blend_set", 0.5), ("blend_set", -1.0),
                                              ("blend_set", 1.3), ("blend_end", False)])
        self.assertEqual((slider.value(), browser.blend_value_label.text()), (0, "0%"))

    def test_escape_cancels_the_drag_and_the_rest_of_it_does_nothing(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.select_row(browser, 0)
        browser.blend_slider.sliderPressed.emit()
        browser.blend_slider.sliderMoved.emit(80)
        browser.blend_slider.cancelled.emit()
        browser.blend_slider.sliderMoved.emit(90)
        browser.blend_slider.sliderReleased.emit()
        self.assertEqual([call for call in session.calls if call[0].startswith("blend")],
                         [("blend_set", 0.8), ("blend_end", True)])
        self.assertEqual(browser.blend_slider.value(), 0)

    def test_a_failed_begin_leaves_no_blend(self):
        session = FakeSession(self.entries())
        browser = self.browser(session)
        self.select_row(browser, 0)
        session.error = "Select a pose to blend."
        browser.blend_slider.sliderPressed.emit()
        session.error = None
        browser.blend_slider.sliderMoved.emit(50)
        browser.blend_slider.sliderReleased.emit()
        self.assertFalse([call for call in session.calls if call[0].startswith("blend")])
        self.assertIn("Select a pose to blend.", browser.status_error_label.text())

    def test_a_middle_drag_on_a_row_selects_it_and_blends_by_distance(self):
        from PySide6 import QtCore, QtTest
        session = FakeSession(self.entries())
        browser = self.browser(session)
        table = browser.table
        center = table.visualRect(browser.proxy.index(2, 0)).center()
        QtTest.QTest.mousePress(table.viewport(), QtCore.Qt.MouseButton.MiddleButton, pos=center)
        self.assertEqual(session.selected.name, "wave")
        table.blend_dragged.emit(100.0)    # half of BLEND_PIXELS
        table.blend_dragged.emit(-1000.0)  # clamped to -100%
        QtTest.QTest.mouseRelease(table.viewport(), QtCore.Qt.MouseButton.MiddleButton, pos=center)
        self.assertEqual([call for call in session.calls if call[0] in ("begin_blend", "blend_set", "blend_end")],
                         [("begin_blend", "wave", False), ("blend_set", 0.5), ("blend_set", -1.0), ("blend_end", False)])
