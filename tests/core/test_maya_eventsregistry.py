"""bmaya.maya.eventsregistry in mayapy, on real Maya callbacks: a failing callback is logged and never stops another,
a callback is never re-entered, removing or pausing during a dispatch is safe, the closing callbacks run before
anything is removed, and a failed resume leaves the rest resumed. No plugin.

Each test runs on its own registry (the singleton is swapped out and put back), so the session's real callbacks
(the active rig tracker's, if a test elsewhere started one) are never touched.

Run with tests/core/run.bat (the Maya half), or: mayapy -m unittest discover -s tests/core -p "test_maya_*.py"
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

try:
    import maya.standalone
except ImportError:
    maya = None


def setUpModule():
    if maya is None:
        raise unittest.SkipTest("needs mayapy")
    import maya.cmds as cmds
    if not hasattr(cmds, "about"):
        maya.standalone.initialize(name="python")


class RegistryTests(unittest.TestCase):

    def setUp(self):
        import maya.cmds as cmds
        import bmaya.maya.eventsregistry
        self.cmds = cmds
        self.module = bmaya.maya.eventsregistry
        saved = self.module.EventsRegistry._instance
        self.module.EventsRegistry._instance = None
        self.registry = self.module.EventsRegistry()
        self.addCleanup(self.restore, saved)
        cmds.file(new=True, force=True)
        self.node = cmds.createNode("transform", name="registry_test")
        self.other = cmds.createNode("transform", name="registry_other")

    def restore(self, saved):
        self.registry.unregister_all()
        if self.registry._shutdown_id is not None:
            self.module.om.MMessage.removeCallback(self.registry._shutdown_id)
        self.module.EventsRegistry._instance = saved

    def select(self):
        """Changes the selection, which runs the selection callbacks."""
        current = self.cmds.ls(selection=True)
        self.cmds.select(self.other if current == [self.node] else self.node, replace=True)

    # ---- guarded -----------------------------------------------------------------------

    def test_a_failing_callback_is_logged_and_the_next_still_runs(self):
        calls = []

        def broken(*args):
            raise ValueError("boom")

        self.registry.add_selection_changed_callback("broken", broken)
        self.registry.add_selection_changed_callback("working", lambda *args: calls.append("working"))
        with mock.patch("bmaya.core.log.error") as error:
            self.select()
        self.assertEqual(calls, ["working"])
        self.assertEqual(error.call_count, 1)
        message = error.call_args[0][0]
        self.assertIn("Callback broken failed", message)
        self.assertIn("ValueError: boom", message)   # the traceback, not only the message

    def test_a_callback_is_not_re_entered(self):
        calls = []

        def nested(*args):
            calls.append("in")
            guarded()   # what a callback that triggers its own event does

        self.registry.add_selection_changed_callback("nested", nested)
        guarded = self.registry.callbacks["nested"]["guarded"]
        guarded()
        self.assertEqual(calls, ["in"])
        self.assertFalse(self.registry.callbacks["nested"]["running"])
        guarded()   # and it runs again once the first call returned
        self.assertEqual(calls, ["in", "in"])

    def test_a_callback_that_selects_runs_once_per_change(self):
        calls = []

        def selects(*args):
            calls.append("in")
            self.cmds.select(self.other, add=True)

        self.registry.add_selection_changed_callback("selects", selects)
        self.cmds.select(self.node, replace=True)
        self.assertEqual(calls, ["in"])

    # ---- removal during a dispatch -----------------------------------------------------

    def test_a_callback_removed_by_another_mid_dispatch_is_not_called(self):
        # Maya doesn't promise an order within one event (it differs once Qt is up), so each removes both: whichever
        # runs first, the other must not run.
        calls = []

        def remover(name):
            def remove(*args):
                calls.append(name)
                self.registry.unregister("a")
                self.registry.unregister("b")
            return remove

        self.registry.add_selection_changed_callback("a", remover("a"))
        self.registry.add_selection_changed_callback("b", remover("b"))
        self.select()
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.registry.callbacks, {})
        self.assertEqual(self.registry._pending_removals, [])   # taken out of Maya once the dispatch ended
        self.select()
        self.assertEqual(len(calls), 1)

    def test_a_key_replaced_mid_dispatch_calls_only_the_new_function(self):
        calls = []

        def replacer(*args):
            calls.append("old")
            self.registry.add_selection_changed_callback("key", lambda *args: calls.append("new"))

        self.registry.add_selection_changed_callback("key", replacer)
        self.select()
        self.select()
        self.assertEqual(calls[0], "old")
        self.assertNotIn("old", calls[1:])
        self.assertIn("new", calls)
        self.assertEqual(list(self.registry.callbacks), ["key"])

    # ---- pause and resume --------------------------------------------------------------

    def test_pause_and_resume(self):
        calls = []
        self.registry.add_selection_changed_callback("key", lambda *args: calls.append("key"))
        self.assertTrue(self.registry.pause("key"))
        self.assertFalse(self.registry.pause("key"))
        self.select()
        self.assertEqual(calls, [])
        self.assertEqual(self.registry.active_callbacks, [])
        self.assertTrue(self.registry.resume("key"))
        self.select()
        self.assertEqual(calls, ["key"])

    def test_a_failed_resume_stays_paused_and_the_others_resume(self):
        calls = []
        self.registry.add_selection_changed_callback("fails", lambda *args: calls.append("fails"))
        self.registry.add_selection_changed_callback("works", lambda *args: calls.append("works"))

        def refuse(guarded):
            raise RuntimeError("refused")

        self.registry.callbacks["fails"]["register"] = refuse
        pause = self.module.pause_callbacks([self.module.EventType.SELECTION_CHANGED])

        @pause
        def quiet():
            self.select()

        with mock.patch("bmaya.core.log.error") as error:
            quiet()
        self.assertEqual(calls, [])
        self.assertIn("Failed to resume callback fails", error.call_args[0][0])
        self.assertTrue(self.registry.callbacks["fails"]["paused"])
        self.assertEqual(self.registry.active_callbacks, ["works"])
        self.select()
        self.assertEqual(calls, ["works"])

    def test_pause_callbacks_resumes_after_an_error(self):
        calls = []
        self.registry.add_selection_changed_callback("key", lambda *args: calls.append("key"))

        @self.module.pause_callbacks([self.module.EventType.SELECTION_CHANGED])
        def broken():
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            broken()
        self.select()
        self.assertEqual(calls, ["key"])

    def test_paused_node_added_callbacks_skip_the_nodes_made_meanwhile(self):
        made = []
        self.registry.add_node_added_callback("nodes", lambda node, *args: made.append(node), "transform")

        @self.module.pause_callbacks([self.module.EventType.NODE_ADDED])
        def build():
            self.cmds.createNode("transform")

        build()
        self.assertEqual(made, [])
        self.cmds.createNode("transform")
        self.assertEqual(len(made), 1)

    # ---- exiting -----------------------------------------------------------------------

    def test_closing_callbacks_run_in_order_before_anything_is_removed(self):
        seen = []

        def first(*args):
            seen.append(("first", sorted(self.registry.callbacks)))
            raise ValueError("boom")

        self.registry.add_selection_changed_callback("selection", lambda *args: None)
        self.registry.add_maya_closing_callback("first", first)
        self.registry.add_maya_closing_callback("second", lambda *args: seen.append(("second", None)))
        with mock.patch("bmaya.core.log.error"):
            self.registry._on_maya_shutdown()
        self.assertEqual(seen, [("first", ["first", "second", "selection"]), ("second", None)])
        self.assertEqual(self.registry.callbacks, {})
        self.assertIsNone(self.registry._shutdown_id)

    def test_a_closing_callback_may_unregister_others(self):
        calls = []

        def closer(*args):
            calls.append("closer")
            self.registry.unregister("selection")
            self.registry.unregister("later")

        self.registry.add_selection_changed_callback("selection", lambda *args: None)
        self.registry.add_maya_closing_callback("closer", closer)
        self.registry.add_maya_closing_callback("later", lambda *args: calls.append("later"))
        self.registry._on_maya_shutdown()
        self.assertEqual(calls, ["closer"])
        self.assertEqual(self.registry._pending_removals, [])

    def test_a_paused_closing_callback_does_not_run(self):
        calls = []
        self.registry.add_maya_closing_callback("closer", lambda *args: calls.append("closer"))
        self.assertTrue(self.registry.pause("closer"))
        self.registry._on_maya_shutdown()
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
