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

    def refresh(self): self._record("refresh")
    def set_active(self, rig_root): self._record("set_active", rig_root)
    def select_group(self, group, add=False): self._record("select_group", group.module, add)
    def select_controls(self, controls, add=False): self._record("select_controls", list(controls), add)
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

    def top_rows(self, panel):
        proxy = panel.proxy
        return [proxy.index(row, 0).data() for row in range(proxy.rowCount())]

    def click(self, panel, index, ctrl=False):
        from PySide6 import QtCore, QtTest
        modifiers = QtCore.Qt.KeyboardModifier.ControlModifier if ctrl else QtCore.Qt.KeyboardModifier.NoModifier
        QtTest.QTest.mouseClick(panel.tree.viewport(), QtCore.Qt.MouseButton.LeftButton, modifiers,
                                panel.tree.visualRect(index).center())

    def test_the_tree_has_a_row_per_group_with_its_controls_under_it(self):
        panel = self.panel(FakeSession([make_rig("hero:rigRoot", "hero")]))
        self.assertEqual(self.top_rows(panel), ["spine  Center  (FkChain)", "arm_l  Left  (FkChain)"])
        spine = panel.proxy.index(0, 0)
        self.assertEqual([panel.proxy.index(row, 0, spine).data() for row in range(panel.proxy.rowCount(spine))],
                         ["spine1_ctrl_c", "spine2_ctrl_c"])

    def test_the_filter_keeps_a_group_with_a_matching_control(self):
        panel = self.panel(FakeSession([make_rig("hero:rigRoot", "hero")]))
        panel.filter.setText("ARM")
        self.assertEqual(self.top_rows(panel), ["arm_l  Left  (FkChain)"])
        panel.filter.setText("")
        self.assertEqual(len(self.top_rows(panel)), 2)

    def test_a_click_selects_a_group_or_one_control_and_ctrl_adds(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        spine = panel.proxy.index(0, 0)
        self.click(panel, spine)
        self.click(panel, panel.proxy.index(1, 0, spine), ctrl=True)
        self.assertEqual(session.calls, [("select_group", "hero:spine", False),
                                         ("select_controls", ["hero:spine2_ctrl_c"], True)])

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
        self.assertFalse(panel.tree.isEnabled())

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

    def test_the_panel_reloads_when_the_session_changes(self):
        session = FakeSession([make_rig("hero:rigRoot", "hero")])
        panel = self.panel(session)
        session.rig, session.groups = None, []
        session.changed.emit()
        self.assertEqual(self.top_rows(panel), [])
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
        self.assertEqual(panel.proxy.rowCount(), len(session.groups))
        self.assertTrue(panel.rig_combo.isVisible())

        panel.rig_combo.setCurrentIndex(panel.rig_combo.findData(villain))   # the user picks the second rig
        self.assertEqual(session.rig.rig_root, villain)
        first = panel.proxy.index(0, 0)
        group = first.data(bmaya.maya_ui.rigpanel.ITEM_ROLE)
        self.assertTrue(all(control.startswith("villain:") for control in group.controls))

        panel.tree.clicked.emit(first)                                         # a click selects in Maya
        self.assertEqual(cmds.ls(selection=True), list(session.groups[0].controls))


if __name__ == "__main__":
    unittest.main()
