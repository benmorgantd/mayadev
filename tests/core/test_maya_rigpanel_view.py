"""The active rig panel's view, offscreen in mayapy, over a fake session (RigModules D50). The session is tested
against real rigs in tests/asset/test_maya_rigpanel.py, so no plugin is needed here: this checks the wiring.

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


def make_rig(rig_root, namespace, variant="main"):
    import rigmodules.query
    return rigmodules.query.RigInfo(rig_root, f"{namespace}:assetRoot", f"shooter\\{namespace}", variant, namespace, 1, "0.1", "")


class FakeSession:
    """The RigPanelSession surface the view reads and calls. Every command is recorded."""

    def __init__(self, rigs, active=0):
        import bmaya.core.observable
        import bmaya.maya.rigpanel
        self.changed = bmaya.core.observable.Event()
        self.spaces_changed = bmaya.core.observable.Event()
        self.space = None
        self.limb_changed = bmaya.core.observable.Event()
        self.limb = None
        self.watching = []
        self.rigs = rigs
        self.rig = rigs[active] if rigs else None
        self.groups = [
            bmaya.maya.rigpanel.ControlGroup("hero:spine", "FkChain", "Center", ("hero:spine1_ctrl_c", "hero:spine2_ctrl_c")),
            bmaya.maya.rigpanel.ControlGroup("hero:arm_l", "FkChain", "Left", ("hero:arm_ctrl_l",)),
        ] if self.rig else []
        self.calls = []
        self.error = None

    def _record(self, *call):
        if self.error:
            raise RuntimeError(self.error)
        self.calls.append(call)

    def watch_selection(self, watch): self.watching.append(watch)
    def set_space(self, label, key=False): self._record("set_space", label, key)
    def set_ik_fk(self, mode, key=False): self._record("set_ik_fk", mode, key)
    def close(self): self.calls.append(("close",))   # a destroyed panel calls it, even when commands are set to fail
    def refresh(self): self._record("refresh")
    def set_active(self, rig_root): self._record("set_active", rig_root)
    def select_group(self, group, add=False): self._record("select_group", group.module, add)
    def select_all(self): self._record("select_all")
    def select_mirrors(self): self._record("select_mirrors")
    def zero(self): self._record("zero")
    def mirror(self, left_to_right=None): self._record("mirror", left_to_right)
    def flip(self): self._record("flip")
    def key_rig(self): self._record("key_rig")
    def key_modules(self): self._record("key_modules")


class RigPanelView(unittest.TestCase):

    def panel(self, session):
        import bmaya.maya_ui.rigpanel
        panel = bmaya.maya_ui.rigpanel.RigPanel(session)
        self.addCleanup(panel.deleteLater)
        panel.resize(400, 600)
        panel.show()
        return panel

    def labels(self, panel):
        return [button.text() for button in panel.group_buttons]

    def click(self, button, modifiers=None):
        from PySide6 import QtCore, QtTest
        QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton,
                                modifiers or QtCore.Qt.KeyboardModifier.NoModifier)

    def test_there_are_three_labelled_folding_sections_and_no_control_tree(self):
        from PySide6 import QtWidgets
        panel = self.panel(FakeSession([make_rig("hero:rigRoot", "hero")]))
        self.assertEqual([section.header.text() for section in (panel.rig_section, panel.select_section, panel.pose_section)],
                         ["Rig", "Select", "Pose"])
        self.assertEqual(panel.findChildren(QtWidgets.QTreeView), [])   # Maya's Outliner lists controls
        panel.pose_section.header.click()
        self.assertFalse(panel.buttons["zero"].isVisible())
        self.assertTrue(panel.buttons["select_all"].isVisible())   # the other sections stay open
        panel.pose_section.header.click()
        self.assertTrue(panel.buttons["zero"].isVisible())

    def test_there_is_one_button_per_group_labelled_by_module(self):
        panel = self.panel(FakeSession([make_rig("hero:rigRoot", "hero")]))
        self.assertEqual(self.labels(panel), ["spine", "arm_l"])

    def test_the_buttons_have_icons_where_one_fits(self):
        panel = self.panel(FakeSession([make_rig("hero:rigRoot", "hero")]))
        with_icon = {"select_mirrors", "mirror_left_to_right", "mirror_right_to_left", "flip", "key_rig", "key_modules"}
        for name, button in panel.buttons.items():
            self.assertEqual(not button.icon().isNull(), name in with_icon, name)
        self.assertTrue(all(not button.icon().isNull() for button in panel.group_buttons))

    def test_a_module_name_shared_by_two_groups_gets_its_side(self):
        import bmaya.maya.rigpanel
        import bmaya.maya_ui.rigpanel
        group = bmaya.maya.rigpanel.ControlGroup
        labels = bmaya.maya_ui.rigpanel.group_labels([
            group("hero:face", "FkChain", "Left", ("a",)), group("hero:face", "FkChain", "Right", ("b",)),
            group("hero:spine", "FkChain", "Center", ("c",))])
        self.assertEqual(labels, ["face Left", "face Right", "spine"])

    def test_a_group_button_selects_and_ctrl_or_shift_adds(self):
        from PySide6 import QtCore
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        self.click(panel.group_buttons[0])
        self.click(panel.group_buttons[1], QtCore.Qt.KeyboardModifier.ControlModifier)
        self.click(panel.group_buttons[1], QtCore.Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(session.calls, [("select_group", "hero:spine", False), ("select_group", "hero:arm_l", True),
                                         ("select_group", "hero:arm_l", True)])

    def test_each_button_calls_its_session_command(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        for name in ("select_all", "select_mirrors", "zero", "mirror_left_to_right", "mirror_right_to_left", "flip",
                     "key_rig", "key_modules", "refresh"):
            panel.buttons[name].click()
        self.assertEqual(session.calls, [("select_all",), ("select_mirrors",), ("zero",), ("mirror", True),
                                         ("mirror", False), ("flip",), ("key_rig",), ("key_modules",), ("refresh",)])

    def test_a_command_error_is_logged_and_does_not_reach_qt(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        session.error = "Select modules or controls of the active rig."
        panel = self.panel(session)
        with mock.patch("bmaya.core.log.error") as error:
            panel.buttons["key_modules"].click()
        error.assert_called_once_with("Select modules or controls of the active rig.")

    def test_no_rig_shows_the_empty_state_and_only_refresh_works(self):
        panel = self.panel(FakeSession([]))
        self.assertTrue(panel.empty_label.isVisible())
        self.assertEqual([name for name, button in panel.buttons.items() if button.isEnabled()], ["refresh"])
        self.assertEqual(panel.group_buttons, [])

    def test_the_picker_shows_only_with_several_rigs_and_picking_sets_the_active_rig(self):
        one = self.panel(FakeSession([make_rig("hero:rigRoot", "hero")]))
        self.assertFalse(one.rig_combo.isVisible())
        self.assertEqual(one.rig_label.text(), "hero  (main)")

        session = FakeSession([make_rig("hero:rigRoot", "hero"), make_rig("villain:rigRoot", "villain")])
        two = self.panel(session)
        self.assertTrue(two.rig_combo.isVisible())
        self.assertEqual(session.calls, [])   # filling the picker is not the user picking
        two.rig_combo.setCurrentIndex(1)
        self.assertEqual(session.calls, [("set_active", "villain:rigRoot")])

    def space(self, session, current=0):
        import bmaya.maya.rigpanel
        session.space = bmaya.maya.rigpanel.SpaceState("hero:arm_ctrl_l", "hero:arm_ctrl_l_space", ("World", "Chest", "Head"), current)
        session.spaces_changed.emit()

    def test_the_space_section_shows_only_for_a_control_with_a_space_switch(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        self.assertFalse(panel.space_section.isVisible())
        self.space(session, current=1)
        self.assertTrue(panel.space_section.isVisible())
        self.assertEqual(panel.space_section.header.text(), "Space")
        self.assertEqual([button.text() for button in panel.space_buttons], ["World", "Chest", "Head"])
        self.assertEqual([button.isChecked() for button in panel.space_buttons], [False, True, False])
        self.assertEqual(panel.space_label.text(), "arm_ctrl_l")
        session.space = None
        session.spaces_changed.emit()
        self.assertFalse(panel.space_section.isVisible())

    def test_a_space_button_switches_and_the_key_box_keys(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        self.space(session)
        self.click(panel.space_buttons[1])
        panel.space_key.setChecked(True)
        self.click(panel.space_buttons[2])
        self.assertEqual(session.calls, [("set_space", "Chest", False), ("set_space", "Head", True)])

    def test_a_refused_switch_is_logged_and_the_buttons_show_the_current_space(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        self.space(session, current=0)
        session.error = "refused"
        with mock.patch("bmaya.core.log.error") as error:
            self.click(panel.space_buttons[2])
        error.assert_called_once_with("refused")
        self.assertEqual([button.isChecked() for button in panel.space_buttons], [True, False, False])

    def limb(self, session, blend=1.0):
        import bmaya.maya.rigpanel
        session.limb = bmaya.maya.rigpanel.LimbState("hero:arm_l", ("hero:upper_ctrl_l", "hero:settings_ctrl_l"),
                                                     "hero:settings_ctrl_l", blend)
        session.limb_changed.emit()

    def test_the_limb_section_shows_only_for_a_selected_limb_and_its_mode(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        self.assertFalse(panel.limb_section.isVisible())
        self.limb(session, blend=1.0)
        self.assertTrue(panel.limb_section.isVisible())
        self.assertEqual(panel.limb_section.header.text(), "IK/FK")
        self.assertEqual(panel.limb_label.text(), "arm_l: IK")
        self.assertEqual({mode: button.isChecked() for mode, button in panel.limb_buttons.items()}, {"IK": True, "FK": False})
        self.limb(session, blend=0.0)
        self.assertEqual({mode: button.isChecked() for mode, button in panel.limb_buttons.items()}, {"IK": False, "FK": True})
        self.limb(session, blend=0.25)
        self.assertEqual(panel.limb_label.text(), "arm_l: blend 0.25")
        self.assertEqual([button.isChecked() for button in panel.limb_buttons.values()], [False, False])
        session.limb = None
        session.limb_changed.emit()
        self.assertFalse(panel.limb_section.isVisible())

    def test_a_limb_button_switches_and_the_key_box_keys(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        self.limb(session)
        self.click(panel.limb_buttons["FK"])
        panel.limb_key.setChecked(True)
        self.click(panel.limb_buttons["IK"])
        self.assertEqual(session.calls, [("set_ik_fk", "FK", False), ("set_ik_fk", "IK", True)])

    def test_a_refused_limb_switch_is_logged_and_the_buttons_show_the_current_mode(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        self.limb(session, blend=1.0)
        session.error = "refused"
        with mock.patch("bmaya.core.log.error") as error:
            self.click(panel.limb_buttons["FK"])
        error.assert_called_once_with("refused")
        self.assertEqual([button.isChecked() for button in panel.limb_buttons.values()], [True, False])

    def test_the_panel_watches_the_selection_only_while_it_shows(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        panel.hide()
        panel.show()
        self.assertEqual(session.watching, [True, False, True])

    def test_a_destroyed_panel_closes_its_session(self):
        """A docked panel is destroyed with its workspace control, often with no closeEvent."""
        from PySide6 import QtCore, QtWidgets
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        import bmaya.maya_ui.rigpanel
        panel = bmaya.maya_ui.rigpanel.RigPanel(session)
        panel.show()
        panel.deleteLater()
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(session.calls, [("close",)])

    def test_the_panel_reloads_when_the_session_changes(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        session.rig, session.groups = None, []
        session.changed.emit()
        self.assertEqual(self.labels(panel), [])
        self.assertTrue(panel.empty_label.isVisible())
        self.assertEqual(session.calls, [])


class PanelOverARealRig(unittest.TestCase):
    """The window on a real session and rig, which the fake-session tests can't show. Needs RIGMODULES_PLUGIN, so
    it skips in the usual core run. The rig builder is the one in tests/asset/test_maya_rigpanel.py."""

    @classmethod
    def setUpClass(cls):
        plugin = os.environ.get("RIGMODULES_PLUGIN", "")
        if not os.path.isfile(plugin):
            raise unittest.SkipTest("set RIGMODULES_PLUGIN to a RigModules.mll")
        import maya.cmds as cmds
        if not cmds.pluginInfo(plugin, query=True, loaded=True):
            cmds.loadPlugin(plugin)
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "asset"))
        import test_maya_rigpanel
        cls.base = test_maya_rigpanel.RigPanelBase

    def setUp(self):
        self.rigs = self.base("setUp")
        self.rigs.setUp()
        self.addCleanup(self.rigs.tearDown)

    def test_the_panel_shows_the_rigs_controls_and_follows_the_active_rig(self):
        import maya.cmds as cmds
        import bmaya.maya.rigpanel
        import bmaya.maya_ui.rigpanel
        self.rigs.build("shooter\\hero")
        villain = self.rigs.build("shooter\\villain")
        session = bmaya.maya.rigpanel.RigPanelSession()
        panel = bmaya.maya_ui.rigpanel.RigPanel(session)
        self.addCleanup(panel.deleteLater)
        panel.show()
        self.assertEqual(len(panel.group_buttons), len(session.groups))
        self.assertTrue(panel.rig_combo.isVisible())

        panel.rig_combo.setCurrentIndex(panel.rig_combo.findData(villain))   # the user picks the second rig
        self.assertEqual(session.rig.rig_root, villain)
        self.assertTrue(all(control.startswith("villain:") for control in session.groups[0].controls))

        panel.group_buttons[0].click()                                         # a click selects in Maya
        self.assertEqual(cmds.ls(selection=True), list(session.groups[0].controls))


if __name__ == "__main__":
    unittest.main()
