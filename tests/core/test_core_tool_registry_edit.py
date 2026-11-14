"""bmaya.core.tool_registry_edit in plain Python, with no Qt: the Registry Editor's state, its commands and events,
the status line, the checked save and the call picker's lists (RigModules design/mayadev-ui.md, D49).

Run with tests/core/run.bat, or: python -m unittest discover -s tests/core -p "test_core_*.py"
"""

import os
import pathlib
import shutil
import sys
import tempfile
import textwrap
import typing
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "py", "scripts"))

from bmaya.core import tool_registry as tr  # noqa: E402
from bmaya.core import tool_registry_edit as edit  # noqa: E402

FIXTURE_MODULE = "edittoolfixture"
FIXTURE_SOURCE = textwrap.dedent('''
    def second():
        """Second function, written first."""
        return "second"

    def first(count: int, flag: bool = False):
        return (count, flag)

    def _private():
        pass

    def boom():
        raise ValueError("inside the tool")
''')


def tool(tool_id="a.b.c", function="second", kwargs=None):
    return tr.Tool(tool_id, f"Name {tool_id}", f"Short {tool_id}", tr.ToolCall(FIXTURE_MODULE, function, kwargs or {}))


def registry(*tools):
    return tr.Registry({t.id: t for t in (tools or (tool(),))})


class Recorder:
    """Counts each event of a session, in the order they happened."""

    def __init__(self, session):
        self.log = []
        for name in ("tools_changed", "selection_changed", "changed"):
            getattr(session, name).connect(lambda name=name: self.log.append(name))


class EditTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.module_dir = tempfile.mkdtemp(prefix="bmaya_edit_module_")
        with open(os.path.join(cls.module_dir, FIXTURE_MODULE + ".py"), "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_SOURCE)
        sys.path.insert(0, cls.module_dir)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(cls.module_dir)
        sys.modules.pop(FIXTURE_MODULE, None)
        shutil.rmtree(cls.module_dir, True)

    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix="bmaya_edit_")
        self.addCleanup(shutil.rmtree, self.temp, True)

    def path(self, name="registry.json"):
        return os.path.join(self.temp, name)

    def saved(self, *tools, name="registry.json"):
        """A registry file, and a session opened on it."""
        path = self.path(name)
        tr.write_registry(registry(*tools), path)
        return edit.RegistryEditSession.open(path), path


class Picking(EditTest):

    def test_open_reads_the_file_and_starts_clean_with_nothing_picked(self):
        session, path = self.saved(tool("a.b.c"), tool("a.b.d"))
        self.assertEqual((list(session.registry.tools), session.path, session.dirty, session.tool),
                         (["a.b.c", "a.b.d"], path, False, None))

    def test_open_raises_the_reader_errors_for_a_missing_or_broken_file(self):
        with self.assertRaises(FileNotFoundError):
            edit.RegistryEditSession.open(self.path("missing.json"))
        with open(self.path("bad.json"), "w", encoding="utf-8") as handle:
            handle.write('{"version": 2, "tools": [{"id": "Bad Id"}]}')
        with self.assertRaises(tr.ToolDataError):
            edit.RegistryEditSession.open(self.path("bad.json"))

    def test_select_picks_a_tool_emits_and_refuses_an_unknown_id(self):
        session, _ = self.saved(tool("a.b.c"), tool("a.b.d"))
        events = Recorder(session)
        session.select("a.b.d")
        self.assertEqual((session.active_tool_id, session.tool.id, events.log), ("a.b.d", "a.b.d", ["selection_changed"]))
        with self.assertRaises(KeyError):
            session.select("no.such")
        self.assertEqual(session.active_tool_id, "a.b.d")
        session.select(None)
        self.assertIsNone(session.tool)

    def test_search_matches_the_name_short_name_and_id_ignoring_case_in_registry_order(self):
        first, second = tool("a.b.c"), tool("x.y.z")
        second.name, second.short_name = "Flip Pose", "Flip"
        session = edit.RegistryEditSession(registry(first, second))
        self.assertEqual(session.search("flip"), ["x.y.z"])
        self.assertEqual(session.search("A.B"), ["a.b.c"])
        self.assertEqual(session.search(""), ["a.b.c", "x.y.z"])


class Editing(EditTest):

    def test_a_field_edit_sets_the_value_marks_dirty_and_emits_changed(self):
        session, _ = self.saved()
        session.select("a.b.c")
        events = Recorder(session)
        session.set_field("name", "Renamed")
        session.set_field("enabled", False)
        self.assertEqual((session.tool.name, session.tool.enabled, session.dirty), ("Renamed", False, True))
        self.assertEqual(events.log, ["changed", "changed"])

    def test_setting_the_value_a_field_already_has_changes_nothing(self):
        session, _ = self.saved()
        session.select("a.b.c")
        events = Recorder(session)
        session.set_field("name", session.tool.name)
        self.assertEqual(events.log, [])
        session.set_call(FIXTURE_MODULE, "second")
        session.set_kwargs({})
        self.assertFalse(session.dirty)

    def test_the_icon_is_none_when_cleared_and_the_id_is_not_editable(self):
        session, _ = self.saved()
        session.select("a.b.c")
        session.set_field("icon", "flip.png")
        self.assertEqual(session.tool.icon, "flip.png")
        session.set_field("icon", "  ")
        self.assertIsNone(session.tool.icon)
        with self.assertRaisesRegex(ValueError, "not an editable field"):
            session.set_field("id", "x.y.z")

    def test_an_edit_with_no_tool_picked_is_refused(self):
        session, _ = self.saved()
        with self.assertRaisesRegex(ValueError, "no tool is picked"):
            session.set_field("name", "x")

    def test_a_new_call_starts_with_no_kwargs_because_another_function_has_other_parameters(self):
        session, _ = self.saved(tool(function="first", kwargs={"count": 2}))
        session.select("a.b.c")
        session.set_call(FIXTURE_MODULE, "second")
        self.assertEqual((session.tool.call.function, session.tool.call.kwargs), ("second", {}))
        session.set_kwargs({"flag": True})
        self.assertEqual(session.tool.call.kwargs, {"flag": True})

    def test_the_kwargs_are_copied_so_the_caller_cannot_change_the_tool_by_accident(self):
        session, _ = self.saved()
        session.select("a.b.c")
        kwargs = {"count": 1}
        session.set_kwargs(kwargs)
        kwargs["count"] = 2
        self.assertEqual(session.tool.call.kwargs, {"count": 1})

    def test_the_module_is_stripped(self):
        session, _ = self.saved()
        session.select("a.b.c")
        session.set_call(f"  {FIXTURE_MODULE} ", "second")
        self.assertEqual(session.tool.call.module, FIXTURE_MODULE)
        self.assertFalse(session.dirty)


class Status(EditTest):

    def test_status_is_ok_for_a_runnable_call_and_empty_with_nothing_picked(self):
        session, _ = self.saved()
        self.assertEqual(session.status(), "")
        session.select("a.b.c")
        self.assertEqual((session.status(), session.can_run()), (edit.STATUS_OK, True))

    def test_status_is_the_first_problem_of_the_call(self):
        session, _ = self.saved(tool(function="first", kwargs={"count": 1}))
        session.select("a.b.c")
        session.set_kwargs({})
        self.assertEqual(session.status(), "required argument 'count' is not given")
        session.set_call("no_such_edit_module", "x")
        self.assertIn("cannot import module 'no_such_edit_module'", session.status())
        self.assertFalse(session.can_run())

    def test_an_input_problem_is_the_status_until_the_next_set_call_set_kwargs_or_pick(self):
        session, _ = self.saved(tool("a.b.c"), tool("a.b.d"))
        session.select("a.b.c")
        events = Recorder(session)
        session.report_input_problem("argument 'x' is not valid JSON")
        self.assertEqual((session.status(), session.can_run(), events.log),
                         ("argument 'x' is not valid JSON", False, ["changed"]))
        session.set_field("name", "Other")                       # a field edit leaves it: the form still has bad text
        self.assertEqual(session.status(), "argument 'x' is not valid JSON")
        session.set_kwargs({})
        self.assertEqual(session.status(), edit.STATUS_OK)
        session.report_input_problem("again")
        session.select("a.b.d")
        self.assertEqual(session.status(), edit.STATUS_OK)

    def test_run_calls_the_picked_tool_as_edited_and_lets_its_exception_through(self):
        session, _ = self.saved(tool("a.b.c", "first", {"count": 3}), tool("a.b.d", "boom"))
        with self.assertRaisesRegex(ValueError, "no tool is picked"):
            session.run()
        session.select("a.b.c")
        self.assertEqual(session.run(), (3, False))
        session.select("a.b.d")
        with self.assertRaisesRegex(ValueError, "inside the tool"):
            session.run()


class AddingAndDeleting(EditTest):

    def test_id_problem_names_a_bad_or_used_id(self):
        session, _ = self.saved()
        self.assertEqual(session.id_problem("a.b.d"), "")
        self.assertIn("lowercase", session.id_problem("Bad Id"))
        self.assertIn("already used", session.id_problem("a.b.c"))

    def test_add_tool_makes_an_empty_call_picks_it_and_marks_dirty(self):
        session, _ = self.saved()
        events = Recorder(session)
        session.add_tool("a.b.d", " New One ")
        new = session.registry.tools["a.b.d"]
        self.assertEqual((new.name, new.short_name, new.call), ("New One", "New One", tr.ToolCall("", "")))
        self.assertEqual((session.active_tool_id, session.dirty), ("a.b.d", True))
        self.assertEqual(events.log, ["tools_changed", "selection_changed"])  # the list is rebuilt before the pick

    def test_add_tool_refuses_a_bad_id_a_used_id_and_an_empty_name_and_changes_nothing(self):
        session, _ = self.saved()
        for tool_id, name in (("Bad Id", "x"), ("a.b.c", "x"), ("a.b.d", "  ")):
            with self.subTest(tool_id, name=name), self.assertRaises(ValueError):
                session.add_tool(tool_id, name)
        self.assertEqual((list(session.registry.tools), session.dirty), (["a.b.c"], False))

    def test_delete_tool_removes_the_picked_tool_picks_none_and_marks_dirty(self):
        session, _ = self.saved(tool("a.b.c"), tool("a.b.d"))
        session.delete_tool()                                    # nothing picked: nothing happens
        self.assertEqual(list(session.registry.tools), ["a.b.c", "a.b.d"])
        session.select("a.b.c")
        events = Recorder(session)
        session.delete_tool()
        self.assertEqual((list(session.registry.tools), session.active_tool_id, session.dirty),
                         (["a.b.d"], None, True))
        self.assertEqual(events.log, ["tools_changed", "selection_changed"])


class Saving(EditTest):

    def test_save_writes_the_registry_and_clears_dirty(self):
        session, path = self.saved()
        session.select("a.b.c")
        session.set_field("name", "Saved Name")
        session.save()
        self.assertFalse(session.dirty)
        self.assertEqual(tr.read_registry(path).tools["a.b.c"].name, "Saved Name")
        self.assertEqual(os.listdir(self.temp), ["registry.json"])  # atomic: no temp file left

    def test_save_as_writes_to_the_new_path_and_keeps_it(self):
        session, _ = self.saved()
        session.select("a.b.c")
        session.set_field("name", "Elsewhere")
        other = self.path("other.json")
        session.save(other)
        self.assertEqual((session.path, session.dirty), (other, False))
        self.assertEqual(tr.read_registry(other).tools["a.b.c"].name, "Elsewhere")

    def test_save_with_no_path_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "no file"):
            edit.RegistryEditSession(registry()).save()

    def test_save_is_refused_with_every_problem_and_writes_nothing(self):
        session, path = self.saved()
        before = pathlib.Path(path).read_bytes()
        session.add_tool("a.b.d", "Unfinished")                  # an empty call
        session.registry.tools["a.b.c"].call.kwargs = {"nope": 1}  # a kwarg that doesn't bind
        with self.assertRaises(tr.ToolDataError) as caught:
            session.save()
        message = str(caught.exception)
        self.assertIn("'module' must be a non-empty string", message)
        self.assertIn("kwarg 'nope' is not a parameter", message)  # structure and calls, in one report
        self.assertEqual(pathlib.Path(path).read_bytes(), before)
        self.assertTrue(session.dirty)

    def test_check_is_none_for_a_good_registry(self):
        session, _ = self.saved()
        self.assertIsNone(session.check())

    def test_saving_the_master_registry_checks_the_layouts_against_it(self):
        master = self.path("master.json")
        layout = self.path("menu.json")
        tr.write_registry(registry(tool("a.b.c"), tool("a.b.d")), master)
        tr.write_layout(tr.Layout("Menu", [tr.ToolItem("a.b.c"), tr.ToolItem("a.b.d")]), layout, ["a.b.c", "a.b.d"])
        session = edit.RegistryEditSession.open(master, master, [layout])
        session.select("a.b.d")
        session.delete_tool()
        with self.assertRaises(tr.ToolDataError) as caught:
            session.save()
        self.assertIn("tool 'a.b.d' is not in the registry", str(caught.exception))
        self.assertIn("menu.json", str(caught.exception))
        self.assertEqual(sorted(tr.read_registry(master).tools), ["a.b.c", "a.b.d"])

    def test_saving_some_other_registry_does_not_check_the_layouts(self):
        master = self.path("master.json")
        layout = self.path("menu.json")
        tr.write_registry(registry(tool("a.b.c")), master)
        tr.write_layout(tr.Layout("Menu", [tr.ToolItem("a.b.c")]), layout, ["a.b.c"])
        session = edit.RegistryEditSession.open(master, master, [layout])
        session.select("a.b.c")
        session.delete_tool()
        session.add_tool("x.y.z", "Other")
        session.set_call(FIXTURE_MODULE, "second")
        session.save(self.path("elsewhere.json"))
        self.assertTrue(os.path.exists(self.path("elsewhere.json")))

    def test_a_missing_layout_file_is_part_of_the_report(self):
        master = self.path("master.json")
        tr.write_registry(registry(), master)
        session = edit.RegistryEditSession.open(master, master, [self.path("gone.json")])
        report = session.check()
        self.assertIn("gone.json", str(report))


class Loading(EditTest):

    def test_load_replaces_the_registry_clears_dirty_and_picks_none(self):
        session, _ = self.saved(tool("a.b.c"))
        session.select("a.b.c")
        session.set_field("name", "Edited")
        other = self.path("other.json")
        tr.write_registry(registry(tool("x.y.z")), other)
        events = Recorder(session)
        session.load(other)
        self.assertEqual((list(session.registry.tools), session.path, session.dirty, session.active_tool_id),
                         (["x.y.z"], other, False, None))
        self.assertEqual(events.log, ["tools_changed", "selection_changed"])

    def test_a_file_that_fails_its_check_is_refused_and_the_registry_stays(self):
        session, path = self.saved(tool("a.b.c"))
        session.select("a.b.c")
        with open(self.path("bad.json"), "w", encoding="utf-8") as handle:
            handle.write('{"version": 2, "tools": [{"id": "Bad Id"}]}')
        events = Recorder(session)
        with self.assertRaises(tr.ToolDataError):
            session.load(self.path("bad.json"))
        self.assertEqual((list(session.registry.tools), session.path, session.active_tool_id, events.log),
                         (["a.b.c"], path, "a.b.c", []))


class CallPicker(EditTest):

    def test_list_modules_finds_modules_without_importing_leaf_modules(self):
        sys.modules.pop("bmaya.core.tool_registry_edit_probe", None)
        names = edit.list_modules()
        self.assertIn("bmaya.core.observable", names)
        self.assertIn("bmaya.core", names)
        self.assertNotIn("bmaya.core.__init__", names)
        self.assertEqual(names, sorted(set(names)))

    def test_list_functions_are_the_public_functions_defined_in_the_module_in_written_order(self):
        import importlib
        module = importlib.import_module(FIXTURE_MODULE)
        self.assertEqual(edit.list_functions(module), ["second", "first", "boom"])  # not _private, not imports

    def test_function_names_keep_a_saved_function_that_the_module_no_longer_has(self):
        session, _ = self.saved()
        self.assertEqual(session.function_names(FIXTURE_MODULE), ["second", "first", "boom"])
        self.assertEqual(session.function_names(FIXTURE_MODULE, "gone")[-1], "gone")
        self.assertEqual(session.function_names(FIXTURE_MODULE, "first").count("first"), 1)
        self.assertEqual(session.function_names("no_such_edit_module", "kept"), ["kept"])

    def test_import_module_gives_the_reason_when_it_cannot(self):
        self.assertEqual(edit.import_module(""), (None, "no module"))
        module, reason = edit.import_module("no_such_edit_module")
        self.assertIsNone(module)
        self.assertIn("cannot import module 'no_such_edit_module'", reason)

    def test_the_picked_function_and_the_first_line_of_its_docstring(self):
        session, _ = self.saved(tool("a.b.c", "second"), tool("a.b.d", "gone"))
        self.assertIsNone(session.function())
        session.select("a.b.c")
        self.assertEqual((session.function().__name__, session.doc()), ("second", "Second function, written first."))
        session.select("a.b.d")
        self.assertEqual((session.function(), session.doc()), (None, ""))

    def test_module_names_are_found_once(self):
        session, _ = self.saved()
        self.assertIs(session.module_names(), session.module_names())


class Hints(unittest.TestCase):

    def test_unwrap_optional_takes_none_out_of_a_union_of_one_type_only(self):
        self.assertIs(tr.unwrap_optional(int | None), int)
        self.assertIs(tr.unwrap_optional(typing.Optional[str]), str)
        self.assertEqual(tr.unwrap_optional(int | str | None), int | str | None)
        self.assertIs(tr.unwrap_optional(bool), bool)
        self.assertIsNone(tr.unwrap_optional(None))


if __name__ == "__main__":
    unittest.main()
