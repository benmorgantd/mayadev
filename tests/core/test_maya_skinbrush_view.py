"""The skin brush settings: SkinBrushSession over a fake `cmds`, and the panel offscreen in mayapy (RigModules D65). Maya
creates no contexts without a GUI, so the real context is checked by hand in a GUI Maya.

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


class FakeCommands:
    """The `cmds` surface the session uses. The context holds the settings, as RigModules' skinBrushCtx does, and
    refuses a strength outside (0, 1] as it does. Every edit and tool change is recorded."""

    def __init__(self, batch=False):
        self.batch = batch
        self.context = None
        self.edits = []
        self.tools = []
        self.refuse = False

    def about(self, batch=False):
        return self.batch

    def contextInfo(self, name, exists=False):
        return self.context is not None

    def skinBrushCtx(self, name, query=False, edit=False, **flags):
        if not query and not edit:
            self.context = {"operation": "smooth", "radius": 5.0, "strength": 0.5, "falloff": "surface", "throughMesh": False}
            return name
        if query:
            return self.context[next(iter(flags))]
        if self.refuse:
            raise RuntimeError("Maya refused the setting")
        self.edits.append(flags)
        self.context.update(flags)
        return None

    def setToolTo(self, name):
        self.tools.append(name)


class SessionTest(unittest.TestCase):

    def session(self, **kwargs):
        import bmaya.maya.skinbrush
        self.fake = FakeCommands(**kwargs)
        return bmaya.maya.skinbrush.SkinBrushSession(self.fake)

    def test_there_are_no_settings_until_the_context_exists(self):
        self.assertIsNone(self.session().settings)

    def test_activating_makes_the_context_once_and_sets_the_tool(self):
        session = self.session()
        name = session.activate()
        session.activate()
        self.assertEqual(name, "rigmodulesSkinBrushCtx")
        self.assertEqual(self.fake.tools, [name, name])
        self.assertEqual((session.settings.radius, session.settings.strength, session.settings.operation), (5.0, 0.5, "smooth"))
        self.assertFalse(session.settings.through_mesh)

    def test_apply_writes_only_what_is_given_and_makes_the_context_first(self):
        session = self.session()
        session.apply(strength=0.8)
        session.apply(radius=12.0, falloff="volume", through_mesh=True)
        self.assertEqual(self.fake.edits, [{"strength": 0.8}, {"radius": 12.0, "falloff": "volume", "throughMesh": True}])
        self.assertEqual(session.settings.falloff, "volume")
        self.assertEqual((session.settings.radius, session.settings.strength, session.settings.through_mesh), (12.0, 0.8, True))

    def test_values_that_are_not_valid_are_refused_before_maya_sees_them(self):
        session = self.session()
        for changes in ({"strength": 0.0}, {"strength": 1.5}, {"radius": 0.0}, {"operation": "paint"}, {"falloff": "smooth"}):
            with self.assertRaises(ValueError):
                session.apply(**changes)
        self.assertEqual(self.fake.edits, [])

    def test_a_setting_maya_refuses_raises_and_keeps_the_old_value(self):
        session = self.session()
        session.apply(strength=0.4)
        self.fake.refuse = True
        with self.assertRaises(RuntimeError):
            session.apply(strength=0.9)
        session.refresh()
        self.assertEqual(session.settings.strength, 0.4)

    def test_batch_makes_no_context(self):
        session = self.session(batch=True)
        with self.assertRaisesRegex(RuntimeError, "needs a GUI Maya"):
            session.activate()
        with self.assertRaisesRegex(RuntimeError, "needs a GUI Maya"):
            session.apply(strength=0.9)
        self.assertIsNone(self.fake.context)

    def test_changed_emits_only_when_the_context_changed(self):
        session = self.session()
        session.activate()
        emitted = []
        session.changed.connect(lambda: emitted.append(1))
        session.refresh()
        self.assertEqual(emitted, [])
        self.fake.context["radius"] = 9.0   # a Ctrl + drag resize in the viewport
        session.refresh()
        session.refresh()
        self.assertEqual(emitted, [1])
        self.assertEqual(session.settings.radius, 9.0)

    def test_activate_skin_brush_in_batch_raises(self):
        try:
            import bmaya.maya.assettools
        except ImportError:
            self.skipTest("put RigModules' python folder on the path (RigModules.mod)")
        with self.assertRaisesRegex(RuntimeError, "needs a GUI Maya"):
            bmaya.maya.assettools.activate_skin_brush(strength=0.7)


class PanelTest(unittest.TestCase):

    def setUp(self):
        import bmaya.maya.skinbrush
        import bmaya.maya_ui.skinbrushpanel
        self.fake = FakeCommands()
        self.session = bmaya.maya.skinbrush.SkinBrushSession(self.fake)
        self.session.activate()
        self.module = bmaya.maya_ui.skinbrushpanel
        self.panel = self.module.SkinBrushPanel(self.session)
        self.addCleanup(self.panel.deleteLater)

    def test_it_shows_the_contexts_settings(self):
        self.assertEqual(self.panel.operation_combo.currentText(), "smooth")
        self.assertEqual(self.panel.falloff_combo.currentText(), "surface")
        self.assertEqual(self.panel.radius_box.value(), 5.0)
        self.assertEqual(self.panel.strength_box.value(), 0.5)
        self.assertEqual(self.panel.strength_slider.value(), 50)
        self.assertFalse(self.panel.through_check.isChecked())

    def test_the_radius_slider_is_logarithmic_and_round_trips(self):
        for radius in (0.05, 1.0, 5.0, 250.0):
            position = self.module.radius_to_slider(radius)
            self.assertAlmostEqual(self.module.slider_to_radius(position) / radius, 1.0, delta=0.01)
        self.assertEqual(self.module.radius_to_slider(0.0001), 0)
        self.assertEqual(self.module.radius_to_slider(1.0e6), self.module.RADIUS_SLIDER_STEPS)

    def test_a_widget_change_is_written_to_the_context(self):
        self.panel.strength_slider.setValue(80)
        self.assertEqual(self.fake.edits[-1], {"strength": 0.8})
        self.panel.strength_box.setValue(0.25)
        self.panel.strength_box.editingFinished.emit()
        self.assertEqual(self.fake.edits[-1], {"strength": 0.25})
        self.panel.radius_box.setValue(12.5)
        self.panel.radius_box.editingFinished.emit()
        self.assertEqual(self.fake.edits[-1], {"radius": 12.5})
        self.panel.falloff_combo.setCurrentIndex(1)
        self.panel.falloff_combo.activated.emit(1)
        self.assertEqual(self.fake.edits[-1], {"falloff": "volume"})
        self.panel.through_check.click()
        self.assertEqual(self.fake.edits[-1], {"throughMesh": True})

    def test_showing_the_settings_is_not_writing_them(self):
        edits = len(self.fake.edits)
        self.fake.context["radius"] = 20.0
        self.session.refresh()
        self.assertEqual(self.panel.radius_box.value(), 20.0)
        self.assertEqual(len(self.fake.edits), edits)

    def test_a_refused_setting_goes_to_the_status_line_and_the_widget_goes_back(self):
        self.fake.refuse = True
        with mock.patch("bmaya.core.log.error") as error:
            self.panel.strength_slider.setValue(90)
        self.assertTrue(self.panel.status_label.text())
        error.assert_called_once()
        self.assertEqual(self.panel.strength_slider.value(), 50)

    def test_the_activate_button_makes_the_brush_the_tool(self):
        self.panel.activate_button.click()
        self.assertEqual(self.fake.tools[-1], "rigmodulesSkinBrushCtx")

    def test_the_context_is_polled_only_while_the_panel_shows(self):
        self.assertFalse(self.panel.timer.isActive())
        self.panel.show()
        self.assertTrue(self.panel.timer.isActive())
        self.panel.hide()
        self.assertFalse(self.panel.timer.isActive())

    def test_without_a_context_the_panel_says_so_and_a_change_makes_one(self):
        import bmaya.maya.skinbrush
        fake = FakeCommands()
        session = bmaya.maya.skinbrush.SkinBrushSession(fake)
        panel = self.module.SkinBrushPanel(session)
        self.addCleanup(panel.deleteLater)
        self.assertIn("activate", panel.status_label.text())
        panel.strength_slider.setValue(30)
        self.assertEqual(fake.edits, [{"strength": 0.3}])
        self.assertEqual(panel.status_label.text(), "")

    def test_show_window_docks_beside_the_outliner(self):
        with mock.patch("bmaya.maya.skinbrush.SkinBrushSession", return_value=self.session), \
                mock.patch.object(self.module.host, "show") as show:
            self.module.show_window()
        self.assertEqual(show.call_args.kwargs["beside"], "Outliner")
        self.assertTrue(show.call_args.kwargs["dock"])
        self.assertEqual(show.call_args.kwargs["object_name"], self.module.OBJECT_NAME)
        show.call_args.args[0].deleteLater()


if __name__ == "__main__":
    unittest.main()
