"""The slots bmaya.core declares, with nothing registered and with test implementations, and the Event and
ProgressManager view-model pieces (RigModules design/mayadev-ui.md, D49). Plain Python.

Run with tests/core/run.bat, or: python -m unittest discover -s tests/core -p "test_core_*.py"
"""

import contextlib
import dataclasses
import gc
import io
import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

import bmaya.core.log  # noqa: E402
import bmaya.core.prompts  # noqa: E402
from bmaya.core.observable import Event  # noqa: E402
from bmaya.core.progressmanager import ProgressManager  # noqa: E402


class LogWriters(unittest.TestCase):

    def setUp(self):
        self.addCleanup(bmaya.core.log.reset_writers)
        bmaya.core.log.init_logger()

    def test_with_nothing_registered_the_log_goes_to_stdout(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bmaya.core.log.info("plain")
            bmaya.core.log.error("broken")
        self.assertIn("[INFO]", out.getvalue())
        self.assertIn(">> plain", out.getvalue())
        self.assertIn("[ERROR]", out.getvalue())

    def test_each_record_goes_to_the_writer_of_its_level(self):
        written = {"info": [], "warning": [], "error": []}
        bmaya.core.log.register_writers({
            logging.INFO: written["info"].append,
            logging.WARNING: written["warning"].append,
            logging.ERROR: written["error"].append,
        })
        bmaya.core.log.info("a")
        bmaya.core.log.warning("b")
        bmaya.core.log.error("c")
        bmaya.core.log.get_logger().critical("d")     # above every level: the highest writer below it
        self.assertEqual([len(written[k]) for k in ("info", "warning", "error")], [1, 1, 2])
        self.assertTrue(written["warning"][0].endswith(">> b"))

    def test_a_level_below_every_writer_goes_to_stdout(self):
        written = []
        bmaya.core.log.register_writers({logging.ERROR: written.append})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bmaya.core.log.info("still printed")
        self.assertEqual(written, [])
        self.assertIn("still printed", out.getvalue())

    def test_registering_replaces_and_reset_restores_stdout(self):
        first, second = [], []
        bmaya.core.log.register_writers({logging.INFO: first.append})
        bmaya.core.log.register_writers({logging.INFO: second.append})
        bmaya.core.log.info("x")
        self.assertEqual((len(first), len(second)), (0, 1))
        bmaya.core.log.reset_writers()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bmaya.core.log.info("y")
        self.assertIn(">> y", out.getvalue())

    def test_the_writer_is_read_when_a_record_is_written(self):
        """A logger made before registration uses the writers registered later."""
        logger = bmaya.core.log.init_logger()
        written = []
        bmaya.core.log.register_writers({logging.INFO: written.append})
        logger.info("late")
        self.assertEqual(len(written), 1)


class Prompts(unittest.TestCase):

    def setUp(self):
        self.addCleanup(bmaya.core.prompts.reset_prompter)

    def test_the_default_raises_naming_the_question(self):
        prompter = bmaya.core.prompts.current()
        with self.assertRaisesRegex(bmaya.core.prompts.PromptError, "'Save Pose: Pose name' needs an answer"):
            prompter.ask_text("Save Pose", "Pose name")
        for ask in (lambda: prompter.choose("T", "m", ["a"]), lambda: prompter.confirm("T", "m"),
                    lambda: prompter.ask_file("T", "*.json", save=True), lambda: prompter.ask_folder("T"),
                    lambda: prompter.ask_form("T", Settings())):
            with self.assertRaises(bmaya.core.prompts.PromptError):
                ask()

    def test_register_and_reset(self):
        scripted = bmaya.core.prompts.ScriptedPrompter()
        bmaya.core.prompts.register_prompter(scripted)
        self.assertIs(bmaya.core.prompts.current(), scripted)
        bmaya.core.prompts.reset_prompter()
        self.assertIsInstance(bmaya.core.prompts.current(), bmaya.core.prompts.NoPrompter)

    def test_scripted_answers_in_order_and_records_the_questions(self):
        prompter = bmaya.core.prompts.ScriptedPrompter(["idle", "B", 0, "C:/a.json", None, Settings(loop=True)])
        self.assertEqual(prompter.ask_text("Save Pose", "Name:", "x"), "idle")
        self.assertEqual(prompter.choose("Variant", "Pick:", ["A", "B"]), "B")
        self.assertIs(prompter.confirm("Replace", "Exists.", accept="Replace"), False)
        self.assertEqual(prompter.ask_file("Load", "Pose files (*.json)", save=False, folder="C:/poses"), "C:/a.json")
        self.assertIsNone(prompter.ask_folder("Weights", "C:/projects"))
        self.assertEqual(prompter.ask_form("Clip", Settings()), Settings(loop=True))
        self.assertEqual([q.kind for q in prompter.asked],
                         ["ask_text", "choose", "confirm", "ask_file", "ask_folder", "ask_form"])
        self.assertEqual(prompter.asked[0].default, "x")
        self.assertEqual(prompter.asked[1].options, ("A", "B"))
        self.assertEqual(prompter.asked[2].options, ("Replace",))
        self.assertEqual(prompter.asked[3].default, "C:/poses")
        self.assertEqual(prompter.asked[5].default, Settings())
        self.assertEqual(prompter.remaining, 0)

    def test_scripted_raises_on_a_question_it_has_no_answer_for(self):
        prompter = bmaya.core.prompts.ScriptedPrompter(["one"])
        prompter.ask_text("First", "")
        with self.assertRaisesRegex(bmaya.core.prompts.PromptError, "No scripted answer for confirm 'Replace"):
            prompter.confirm("Replace", "Exists.")


@dataclasses.dataclass(frozen=True)
class Settings:
    loop: bool = False


class Events(unittest.TestCase):

    def test_listeners_are_called_in_order_with_the_arguments(self):
        event, calls = Event(), []
        event.connect(lambda *a: calls.append(("first", a)))
        event.connect(lambda *a: calls.append(("second", a)))
        event.emit(1, "x")
        self.assertEqual(calls, [("first", (1, "x")), ("second", (1, "x"))])

    def test_connecting_twice_calls_once_and_disconnect_removes(self):
        event, calls = Event(), []
        listener = calls.append
        event.connect(listener)
        event.connect(listener)
        event.emit(1)
        event.disconnect(listener)
        event.emit(2)
        self.assertEqual(calls, [1])

    def test_a_bound_method_is_held_weakly(self):
        class View:
            def __init__(self):
                self.seen = 0

            def refresh(self):
                self.seen += 1

        event, view = Event(), View()
        event.connect(view.refresh)
        event.emit()
        self.assertEqual(view.seen, 1)
        del view
        gc.collect()
        self.assertEqual(event.listeners(), [])
        event.emit()   # nothing left to call, and no error


class Progress(unittest.TestCase):

    def test_every_change_notifies_every_listener(self):
        manager = ProgressManager()
        first, second = [], []
        manager.changed.connect(lambda: first.append((manager.active, manager.current_value, manager.status_text)))
        manager.changed.connect(lambda: second.append(manager.current_value))
        self.addCleanup(lambda: setattr(manager, "changed", Event()))
        manager.start("Building", max_value=10)
        manager.update(4, "Halfway")
        manager.increment(20)        # clamped to max_value
        manager.end()
        self.assertEqual(first, [(True, 0, "Building"), (True, 4, "Halfway"), (True, 10, "Halfway"), (False, 0, "Halfway")])
        self.assertEqual(second, [0, 4, 10, 0])

    def test_the_context_manager_ends_the_task_when_it_raises(self):
        manager = ProgressManager()
        manager.start("Work")
        with self.assertRaises(ValueError), contextlib.redirect_stdout(io.StringIO()):
            with manager:
                raise ValueError("boom")
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main()
