"""bmaya.core.tool_registry in plain Python: read and write, the check pass, versions, atomic writes, calls and
running a tool.

Run with tests/core/run.bat, or: python -m unittest discover -s tests/core -p "test_core_*.py"
"""

import json
import os
import shutil
import sys
import tempfile
import textwrap
import traceback
import unittest
from unittest import mock

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "py", "scripts"))

from bmaya.core import tool_registry as tr  # noqa: E402

TOOLS = os.path.join(ROOT, "toolsets")
FIXTURE_MODULE = "toolfixture_module"
FIXTURE_SOURCE = textwrap.dedent('''
    from typing import Literal

    def plain():
        return "plain"

    def with_args(count: int, scale: float = 1.0, flag: bool = False, mode: Literal["a", "b"] = "a",
                  label: str | None = None):
        return (count, scale, flag, mode, label)

    def boom():
        raise ValueError("inside the tool")

    not_callable = 3
''')


def good_tool(tool_id="a.b.c", name="Name", **call):
    call = {"module": FIXTURE_MODULE, "function": "plain", "kwargs": {}, **call}
    return {"id": tool_id, "name": name, "short_name": name, "call": call, "icon": None, "enabled": True}


def good_registry(*tools):
    return {"version": 2, "tools": list(tools) or [good_tool()]}


def good_layout(*items):
    return {"version": 2, "label": "Menu", "items": list(items) or [{"type": "tool", "tool": "a.b.c", "enabled": True}]}


class TempDirTest(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix="bmaya_tool_registry_")
        self.addCleanup(shutil.rmtree, self.temp, True)

    def path(self, name):
        return os.path.join(self.temp, name)

    def read_text(self, name):
        with open(self.path(name), encoding="utf-8") as handle:
            return handle.read()

    def write(self, name, data):
        with open(self.path(name), "w", encoding="utf-8") as handle:
            handle.write(data if isinstance(data, str) else json.dumps(data))
        return self.path(name)


class RepoFiles(TempDirTest):

    def read(self, name):
        with open(os.path.join(TOOLS, name), encoding="utf-8", newline="") as handle:
            return handle.read().replace("\r\n", "\n")

    def test_repo_files_round_trip(self):
        registry = tr.read_registry(os.path.join(TOOLS, "master_tool_registry.json"))
        tr.write_registry(registry, self.path("registry.json"))
        with open(self.path("registry.json"), encoding="utf-8", newline="") as handle:
            self.assertEqual(handle.read().replace("\r\n", "\n"), self.read("master_tool_registry.json"))

        for name in ("bmaya_menu.json", "rigmodules_menu.json"):
            with self.subTest(name):
                layout = tr.read_layout(os.path.join(TOOLS, name), registry.tools)
                tr.write_layout(layout, self.path(name), registry.tools)
                with open(self.path(name), encoding="utf-8", newline="") as handle:
                    self.assertEqual(handle.read().replace("\r\n", "\n"), self.read(name))

    def test_load_all_reads_the_registry_and_every_layout(self):
        paths = [os.path.join(TOOLS, "bmaya_menu.json"), os.path.join(TOOLS, "rigmodules_menu.json")]
        registry, layouts = tr.load_all(os.path.join(TOOLS, "master_tool_registry.json"), paths)
        self.assertEqual(set(layouts), set(paths))
        used = [i.tool for layout in layouts.values() for i in layout.tool_items()]
        self.assertEqual(sorted(used), sorted(registry.tools))  # every tool is in exactly one menu

    def test_the_repo_menus_have_the_layout_the_docs_describe(self):
        registry = tr.read_registry(os.path.join(TOOLS, "master_tool_registry.json"))
        rig = tr.read_layout(os.path.join(TOOLS, "rigmodules_menu.json"), registry.tools)
        self.assertEqual([i.label for i in rig.items], ["panels", "asset", "mesh", "joints", "weights", "shapes", "control", "pose", "clip"])
        self.assertEqual(len(list(rig.tool_items())), 40)
        bmaya = tr.read_layout(os.path.join(TOOLS, "bmaya_menu.json"), registry.tools)
        dev = [i for i in bmaya.items if isinstance(i, tr.Submenu) and i.label == "dev"][0]
        self.assertEqual([i.tool for i in dev.items], ["bmaya.dev.reload_rigmodules", "bmaya.dev.unload_rigmodules", "bmaya.dev.reload_menu"])

    def test_repo_ids_follow_the_format_and_every_call_is_json(self):
        registry = tr.read_registry(os.path.join(TOOLS, "master_tool_registry.json"))
        for tool in registry.tools.values():
            self.assertRegex(tool.id, tr.ID_PATTERN)
            self.assertEqual(tr.check_registry(tr.registry_to_dict(registry)), [])


class RoundTrip(TempDirTest):

    def test_enabled_false_and_non_ascii_survive(self):
        data = good_registry(good_tool(name="Café →"))
        data["tools"][0]["enabled"] = False
        path = self.write("r.json", data)
        registry = tr.read_registry(path)
        self.assertFalse(registry.tools["a.b.c"].enabled)
        tr.write_registry(registry, path)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("Café →", text)  # readable in a diff, not an escape
        self.assertEqual(tr.read_registry(path).tools["a.b.c"].name, "Café →")

        layout = good_layout({"type": "tool", "tool": "a.b.c", "enabled": False})
        lpath = self.write("l.json", layout)
        self.assertFalse(tr.read_layout(lpath, ["a.b.c"]).items[0].enabled)
        tr.write_layout(tr.read_layout(lpath, ["a.b.c"]), lpath, ["a.b.c"])
        self.assertFalse(tr.read_layout(lpath, ["a.b.c"]).items[0].enabled)

    def test_reading_returns_a_new_registry_each_time(self):
        path = self.write("r.json", good_registry())
        first, second = tr.read_registry(path), tr.read_registry(path)
        self.assertIsNot(first, second)
        self.assertEqual(list(second.tools), ["a.b.c"])

    def test_tool_items_walks_depth_first(self):
        layout = tr.Layout("m", [
            tr.ToolItem("a"),
            tr.Submenu("s", [tr.ToolItem("b"), tr.Separator(), tr.Submenu("t", [tr.ToolItem("c")])]),
            tr.ToolItem("d"),
        ])
        self.assertEqual([i.tool for i in layout.tool_items()], ["a", "b", "c", "d"])


class Files(TempDirTest):

    def test_a_missing_file_raises_and_names_the_path(self):
        with self.assertRaisesRegex(FileNotFoundError, "missing.json"):
            tr.read_registry(self.path("missing.json"))
        with self.assertRaisesRegex(FileNotFoundError, "missing.json"):
            tr.read_layout(self.path("missing.json"), [])

    def test_a_file_that_is_not_json_is_one_issue(self):
        path = self.write("bad.json", "{ not json")
        with self.assertRaises(tr.ToolDataError) as caught:
            tr.read_registry(path)
        self.assertEqual(len(caught.exception.issues), 1)
        self.assertIn("not valid JSON", str(caught.exception))
        self.assertIn(path, str(caught.exception))

    def test_a_newer_version_raises(self):
        path = self.write("r.json", {"version": 3, "tools": []})
        with self.assertRaisesRegex(tr.ToolDataError, "newer mayadev"):
            tr.read_registry(path)

    def test_a_file_without_version_is_version_one_and_no_longer_read(self):
        path = self.write("r.json", {"tools": []})
        with self.assertRaisesRegex(tr.ToolDataError, "version 1 is no longer read"):
            tr.read_registry(path)
        lpath = self.write("l.json", {"label": "x", "items": []})
        with self.assertRaisesRegex(tr.ToolDataError, "version 1 is no longer read"):
            tr.read_layout(lpath, [])

    def test_an_invalid_registry_is_never_written(self):
        registry = tr.read_registry(self.write("r.json", good_registry()))
        before = self.read_text("r.json")
        registry.tools["a.b.c"].name = ""
        with self.assertRaises(tr.ToolDataError):
            tr.write_registry(registry, self.path("r.json"))
        self.assertEqual(self.read_text("r.json"), before)
        self.assertEqual(os.listdir(self.temp), ["r.json"])

    def test_a_write_that_fails_partway_leaves_the_original_and_no_temp_file(self):
        registry = tr.read_registry(self.write("r.json", good_registry()))
        before = self.read_text("r.json")
        registry.tools["a.b.c"].name = "Changed"
        with mock.patch.object(os, "fsync", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                tr.write_registry(registry, self.path("r.json"))
        self.assertEqual(self.read_text("r.json"), before)
        self.assertEqual(os.listdir(self.temp), ["r.json"])

    def test_a_write_replaces_the_file_and_leaves_no_temp_file(self):
        registry = tr.read_registry(self.write("r.json", good_registry()))
        registry.tools["a.b.c"].name = "Changed"
        tr.write_registry(registry, self.path("r.json"))
        self.assertEqual(tr.read_registry(self.path("r.json")).tools["a.b.c"].name, "Changed")
        self.assertEqual(os.listdir(self.temp), ["r.json"])

    def test_load_all_reports_every_broken_file_together(self):
        registry = self.write("r.json", good_registry(good_tool(), good_tool("x.y.z", "Other") | {"enabeld": True}))
        layout_a = self.write("a.json", good_layout({"type": "bogus"}))
        layout_b = self.write("b.json", good_layout({"type": "separator"}))
        with self.assertRaises(tr.ToolDataError) as caught:
            tr.load_all(registry, [layout_a, layout_b])
        message = str(caught.exception)
        self.assertIn("unknown key 'enabeld'", message)
        self.assertIn("unknown item type 'bogus'", message)
        self.assertEqual(len(caught.exception.reports), 2)  # the registry and layout a; layout b is fine

    def test_load_all_checks_layout_references_against_a_good_registry(self):
        registry = self.write("r.json", good_registry())
        layout = self.write("l.json", good_layout({"type": "tool", "tool": "no.such.tool"}))
        with self.assertRaisesRegex(tr.ToolDataError, "tool 'no.such.tool' is not in the registry"):
            tr.load_all(registry, [layout])

    def test_load_all_with_a_broken_registry_still_checks_layout_structure(self):
        registry = self.write("r.json", {"version": 2, "tools": "nope"})
        layout = self.write("l.json", good_layout({"type": "bogus"}))
        with self.assertRaises(tr.ToolDataError) as caught:
            tr.load_all(registry, [layout])
        self.assertIn("unknown item type 'bogus'", str(caught.exception))
        self.assertIn("tools: must be a list", str(caught.exception))


class RegistryChecks(unittest.TestCase):

    def test_a_good_registry_has_no_issues(self):
        self.assertEqual(tr.check_registry(good_registry()), [])

    def test_one_bad_file_reports_every_issue(self):
        tools = [
            good_tool("a.b.one", "One") | {"enabeld": True},      # unknown key
            good_tool("a.b.two", "Two"),
            good_tool("a.b.two", "Three"),                        # duplicate id
            good_tool("a.b.four", "TWO"),                         # duplicate name, compared casefolded
            good_tool("Bad Id", "Five"),                          # bad id format
            {k: v for k, v in good_tool("a.b.six", "Six").items() if k != "short_name"},  # missing key
        ]
        issues = tr.check_registry(good_registry(*tools))
        self.assertEqual(len(issues), 5, [f"{i.where}: {i.message}" for i in issues])
        text = "\n".join(f"{i.where}: {i.message}" for i in issues)
        for expected in ("unknown key 'enabeld'", "id 'a.b.two' is already used by tools[1]",
                         "name 'TWO' is already used by tools[1]", "dot-separated lowercase", "missing key 'short_name'"):
            self.assertIn(expected, text)
        self.assertIn("tools[0] (a.b.one)", text)

    def test_value_types(self):
        cases = {
            "name must be non-empty": good_tool(name="  "),
            "icon must be a string or null": good_tool() | {"icon": 3},
            "enabled must be true or false": good_tool() | {"enabled": "yes"},
            "call must be an object": good_tool() | {"call": "x.y"},
            "kwargs must be an object": good_tool(kwargs=[1]),
            "kwarg not JSON": good_tool(kwargs={"x": {1, 2}}),
            "unknown call key": good_tool(args=[1]),
        }
        for label, tool in cases.items():
            with self.subTest(label):
                self.assertTrue(tr.check_registry(good_registry(tool)), label)

    def test_script_is_an_unknown_key(self):
        issues = tr.check_registry(good_registry(good_tool() | {"script": "print(1)"}))
        self.assertEqual([i.message for i in issues], ["unknown key 'script'"])

    def test_short_name_is_not_checked_for_uniqueness(self):
        two = good_tool("a.b.d", "Other")
        two["short_name"] = "Name"
        self.assertEqual(tr.check_registry(good_registry(good_tool(), two)), [])


class LayoutChecks(unittest.TestCase):
    IDS = ["a.b.c", "x.y.z"]

    def issues(self, *items):
        return [i.message for i in tr.check_layout(good_layout(*items), self.IDS)]

    def test_a_good_layout_has_no_issues(self):
        item = {"type": "submenu", "label": "S", "items": [{"type": "tool", "tool": "a.b.c"}, {"type": "separator"}]}
        self.assertEqual(self.issues(item), [])

    def test_a_dangling_reference(self):
        self.assertEqual(self.issues({"type": "tool", "tool": "a.b.cc"}), ["tool 'a.b.cc' is not in the registry"])

    def test_the_same_tool_twice_anywhere_in_the_layout(self):
        messages = self.issues({"type": "tool", "tool": "a.b.c"},
                               {"type": "submenu", "label": "S", "items": [{"type": "tool", "tool": "a.b.c"}]})
        self.assertEqual(len(messages), 1)
        self.assertIn("already used at items[0]", messages[0])

    def test_an_item_without_type(self):
        self.assertEqual(self.issues({"tool": "a.b.c"}), ["missing key 'type'"])

    def test_an_unknown_item_type(self):
        self.assertEqual(len(self.issues({"type": "button"})), 1)

    def test_duplicate_sibling_submenu_labels(self):
        messages = self.issues({"type": "submenu", "label": "S", "items": []}, {"type": "submenu", "label": "S", "items": []})
        self.assertEqual(len(messages), 1)
        self.assertIn("already used by items[0]", messages[0])

    def test_the_same_label_in_different_parents_is_fine(self):
        inner = {"type": "submenu", "label": "S", "items": []}
        self.assertEqual(self.issues({"type": "submenu", "label": "S", "items": [inner]}), [])

    def test_unknown_and_missing_keys_per_type(self):
        self.assertEqual(self.issues({"type": "separator", "label": "x"}), ["unknown key 'label'"])
        self.assertEqual(self.issues({"type": "submenu", "label": "S"}), ["missing key 'items'"])
        self.assertEqual(self.issues({"type": "tool"}), ["missing key 'tool'"])

    def test_a_tool_item_that_is_not_a_string_id(self):
        self.assertEqual(self.issues({"type": "tool", "tool": 5}), ["'tool' must be a tool id string"])

    def test_where_names_the_nested_path(self):
        data = good_layout({"type": "submenu", "label": "S", "items": [{"type": "separator"}, {"type": "tool", "tool": "nope"}]})
        self.assertEqual([i.where for i in tr.check_layout(data, self.IDS)], ["items[0].items[1]"])


class Versions(unittest.TestCase):

    def test_upgrade_runs_the_steps_in_order(self):
        calls = []

        def step(n):
            def run(data):
                calls.append(n)
                data["trail"] = data.get("trail", []) + [n]
            return run

        data = {"version": 2}
        tr.upgrade(data, 4, {2: step(2), 3: step(3)})
        self.assertEqual(calls, [2, 3])
        self.assertEqual(data, {"version": 4, "trail": [2, 3]})

    def test_upgrade_with_nothing_to_do_changes_nothing(self):
        data = {"version": 2, "tools": []}
        tr.upgrade(data, 2, {})
        self.assertEqual(data, {"version": 2, "tools": []})

    def test_upgrade_rejects_a_gap(self):
        with self.assertRaisesRegex(tr.ToolDataError, "no step from version 3 to 4"):
            tr.upgrade({"version": 2}, 4, {2: lambda data: None})

    def test_upgrade_rejects_a_newer_version_and_a_bad_one(self):
        with self.assertRaisesRegex(tr.ToolDataError, "newer mayadev"):
            tr.upgrade({"version": 5}, 4, {})
        for bad in ("2", 0, True, 1.5):
            with self.subTest(bad):
                with self.assertRaises(tr.ToolDataError):
                    tr.upgrade({"version": bad}, 2, {})

    def test_reading_runs_the_updates_before_the_check(self):
        """An update step sees the old format, and the check sees the new one."""
        temp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp, True)
        path = os.path.join(temp, "r.json")
        old = {"version": 1, "tools": [{"id": "a.b.c", "title": "Name", "short_name": "N", "call": {"module": "m", "function": "f"}}]}
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(old, handle)

        def rename_title(data):
            for tool in data.get("tools", []):
                tool["name"] = tool.pop("title", "")

        with mock.patch.object(tr, "REGISTRY_UPDATES", {1: rename_title}):
            registry = tr.read_registry(path)
        self.assertEqual(registry.tools["a.b.c"].name, "Name")

    def test_the_version_is_always_written_at_the_current_one(self):
        self.assertEqual(tr.registry_to_dict(tr.Registry())["version"], tr.REGISTRY_VERSION)
        self.assertEqual(tr.layout_to_dict(tr.Layout("m"))["version"], tr.LAYOUT_VERSION)


class Calls(TempDirTest):

    def setUp(self):
        super().setUp()
        with open(self.path(f"{FIXTURE_MODULE}.py"), "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_SOURCE)
        sys.path.insert(0, self.temp)
        self.addCleanup(sys.path.remove, self.temp)
        self.addCleanup(sys.modules.pop, FIXTURE_MODULE, None)

    def issues(self, function, **kwargs):
        call = tr.ToolCall(FIXTURE_MODULE, function, kwargs)
        return tr.check_calls(tr.Registry({"a.b.c": tr.Tool("a.b.c", "N", "N", call)}))

    def test_a_good_call_has_no_issues(self):
        self.assertEqual(self.issues("plain"), [])
        self.assertEqual(self.issues("with_args", count=2, scale=3, flag=True, mode="b", label=None), [])

    def test_a_missing_module(self):
        registry = tr.Registry({"a.b.c": tr.Tool("a.b.c", "N", "N", tr.ToolCall("toolfixture_nope", "x"))})
        issues = tr.check_calls(registry)
        self.assertEqual(len(issues), 1)
        self.assertIn("cannot import module 'toolfixture_nope'", issues[0].message)
        self.assertEqual(issues[0].where, "tools[0] (a.b.c).call")

    def test_an_empty_module_or_function_is_an_issue_not_a_crash(self):
        for call in (tr.ToolCall("", ""), tr.ToolCall(FIXTURE_MODULE, "")):
            with self.subTest(call):
                issues = tr.check_calls(tr.Registry({"a.b.c": tr.Tool("a.b.c", "N", "N", call)}))
                self.assertEqual(len(issues), 1)

    def test_a_module_that_raises_when_imported_is_an_issue_not_a_crash(self):
        with open(self.path("toolfixture_broken.py"), "w", encoding="utf-8") as handle:
            handle.write("raise RuntimeError('broken at import')\n")
        self.addCleanup(sys.modules.pop, "toolfixture_broken", None)
        issues = tr.check_calls(tr.Registry({"a.b.c": tr.Tool("a.b.c", "N", "N", tr.ToolCall("toolfixture_broken", "x"))}))
        self.assertIn("broken at import", issues[0].message)

    def test_a_missing_function_and_a_non_callable(self):
        self.assertIn(f"no function 'nope' in {FIXTURE_MODULE}", self.issues("nope")[0].message)
        self.assertIn("no function 'not_callable'", self.issues("not_callable")[0].message)

    def test_an_unknown_kwarg(self):
        self.assertIn("kwarg 'extra' is not a parameter", self.issues("plain", extra=1)[0].message)

    def test_a_missing_required_argument(self):
        messages = [i.message for i in self.issues("with_args")]
        self.assertEqual(messages, ["required argument 'count' is not given"])

    def test_wrong_value_types(self):
        cases = {
            "count": "two", "scale": "big", "flag": 1, "mode": "c", "label": 5,
        }
        for name, value in cases.items():
            with self.subTest(name):
                kwargs = {"count": 1, name: value}
                issues = self.issues("with_args", **kwargs)
                self.assertEqual(len(issues), 1, issues)
                self.assertIn(f"kwarg '{name}'", issues[0].message)

    def test_bool_is_not_an_int_and_int_is_a_float(self):
        self.assertTrue(self.issues("with_args", count=True))
        self.assertEqual(self.issues("with_args", count=1, scale=2), [])

    def test_matches_annotation_leaves_other_annotations_unchecked(self):
        self.assertTrue(tr.matches_annotation([1], list[int]))
        self.assertTrue(tr.matches_annotation("x", object))


class RunningATool(TempDirTest):

    def setUp(self):
        super().setUp()
        with open(self.path(f"{FIXTURE_MODULE}.py"), "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_SOURCE)
        sys.path.insert(0, self.temp)
        self.addCleanup(sys.path.remove, self.temp)
        self.addCleanup(sys.modules.pop, FIXTURE_MODULE, None)

    def tool(self, function, **kwargs):
        return tr.Tool("a.b.c", "N", "N", tr.ToolCall(FIXTURE_MODULE, function, kwargs))

    def test_run_tool_calls_the_function_with_the_kwargs(self):
        self.assertEqual(tr.run_tool(self.tool("plain")), "plain")
        self.assertEqual(tr.run_tool(self.tool("with_args", count=3, mode="b")), (3, 1.0, False, "b", None))

    def test_a_missing_function_raises_tool_error_naming_the_tool(self):
        with self.assertRaisesRegex(tr.ToolError, f"Tool a.b.c: no function 'nope' in {FIXTURE_MODULE}"):
            tr.run_tool(self.tool("nope"))

    def test_a_missing_module_raises_tool_error_and_keeps_the_cause(self):
        tool = tr.Tool("a.b.c", "N", "N", tr.ToolCall("toolfixture_nope", "x"))
        with self.assertRaises(tr.ToolError) as caught:
            tr.run_tool(tool)
        self.assertIsInstance(caught.exception.__cause__, ImportError)

    def test_an_exception_from_the_function_is_raised_unchanged_with_its_own_traceback(self):
        try:
            tr.run_tool(self.tool("boom"))
        except ValueError as err:
            self.assertEqual(str(err), "inside the tool")
            frames = [frame.filename for frame in traceback.extract_tb(err.__traceback__)]
        else:
            self.fail("the tool's exception was swallowed")
        self.assertTrue(any(f.endswith(f"{FIXTURE_MODULE}.py") for f in frames), frames)

    def test_the_module_is_imported_on_each_run_so_a_reload_is_seen(self):
        tool = self.tool("plain")
        self.assertEqual(tr.run_tool(tool), "plain")
        del sys.modules[FIXTURE_MODULE]
        with open(self.path(f"{FIXTURE_MODULE}.py"), "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_SOURCE.replace('return "plain"', 'return "changed"'))
        self.assertEqual(tr.run_tool(tool), "changed")


class ErrorMessage(unittest.TestCase):

    def test_the_message_lists_every_issue_under_its_file(self):
        error = tr.ToolDataError.combine([
            tr.ToolDataError([tr.Issue("tools[5] (x.y)", "unknown key 'enabeld'"), tr.Issue("tools[9]", "id is used")], "reg.json"),
            tr.ToolDataError([tr.Issue("items[6].items[2]", "tool 'x' is not in the registry")], "menu.json"),
        ])
        self.assertEqual(str(error), "\n".join([
            "reg.json: 2 problems",
            "  tools[5] (x.y): unknown key 'enabeld'",
            "  tools[9]: id is used",
            "menu.json: 1 problem",
            "  items[6].items[2]: tool 'x' is not in the registry",
        ]))
        self.assertEqual(len(error.issues), 3)


if __name__ == "__main__":
    unittest.main()
