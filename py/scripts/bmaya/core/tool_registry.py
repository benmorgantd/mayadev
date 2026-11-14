"""The tool registry and menu layout files: dataclasses, the check pass, versions, atomic IO and running a tool.

A tool is data: an id, labels and one function call. A registry file holds the tools, and one layout file per
menu says which tools sit where. Every file is checked before anything is built from it, and the check reports
every problem at once (design: RigModules design/tool-registry.md, D47). This module is Maya-free, so the check
and the file IO run in plain Python. check_calls imports the tool modules, and run_tool imports one on a click.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import json
import os
import re
import types
import typing
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence

JsonValue = typing.Union[None, bool, int, float, str, list, dict]

REGISTRY_VERSION = 2
LAYOUT_VERSION = 2
# n -> the step from version n to n + 1, run in place on the raw JSON. Version 2 is the first format, so the next
# format change adds the first step.
REGISTRY_UPDATES: dict[int, Callable[[dict], None]] = {}
LAYOUT_UPDATES: dict[int, Callable[[dict], None]] = {}

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")

_TOOL_KEYS = ("id", "name", "short_name", "call", "icon", "enabled")
_TOOL_REQUIRED = ("id", "name", "short_name", "call")
_CALL_KEYS = ("module", "function", "kwargs")
_CALL_REQUIRED = ("module", "function")
_ITEM_KEYS = {
    "tool": ("type", "tool", "enabled"),
    "separator": ("type",),
    "submenu": ("type", "label", "items"),
}
_ITEM_REQUIRED = {"tool": ("type", "tool"), "separator": ("type",), "submenu": ("type", "label", "items")}


# ----------------------------------------------------------------------------------------------------------------
# Data


@dataclasses.dataclass
class ToolCall:
    module: str
    function: str
    kwargs: dict[str, JsonValue] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class Tool:
    id: str
    name: str
    short_name: str
    call: ToolCall
    icon: str | None = None
    enabled: bool = True


@dataclasses.dataclass
class Registry:
    tools: dict[str, Tool] = dataclasses.field(default_factory=dict)  # by id, in file order


@dataclasses.dataclass
class ToolItem:
    tool: str
    enabled: bool = True


@dataclasses.dataclass
class Separator:
    pass


@dataclasses.dataclass
class Submenu:
    label: str
    items: list[LayoutItem] = dataclasses.field(default_factory=list)


LayoutItem = typing.Union[ToolItem, Separator, Submenu]


@dataclasses.dataclass
class Layout:
    label: str
    items: list[LayoutItem] = dataclasses.field(default_factory=list)

    def tool_items(self) -> Iterator[ToolItem]:
        """Every tool item, depth first."""
        return _walk_tool_items(self.items)


def _walk_tool_items(items: Sequence[LayoutItem]) -> Iterator[ToolItem]:
    for item in items:
        if isinstance(item, ToolItem):
            yield item
        elif isinstance(item, Submenu):
            yield from _walk_tool_items(item.items)


# ----------------------------------------------------------------------------------------------------------------
# Errors


@dataclasses.dataclass
class Issue:
    where: str  # "tools[12] (rigmodules.pose.flip).call.kwargs"
    message: str


class ToolDataError(Exception):
    """Every Issue of one load or save. The message lists them, one per line, under the file path."""

    def __init__(self, issues: Sequence[Issue], path: str = "") -> None:
        self.reports: list[tuple[str, list[Issue]]] = [(path, list(issues))]
        super().__init__(self._format())

    @classmethod
    def combine(cls, errors: Sequence[ToolDataError]) -> ToolDataError:
        """One error that reports the files of all of them."""
        combined = cls([])
        combined.reports = [report for error in errors for report in error.reports]
        combined.args = (combined._format(),)
        return combined

    @property
    def issues(self) -> list[Issue]:
        return [issue for _, issues in self.reports for issue in issues]

    def _format(self) -> str:
        blocks = []
        for path, issues in self.reports:
            count = f"{len(issues)} problem{'s' if len(issues) != 1 else ''}"
            lines = [f"{path}: {count}" if path else count]
            lines += [f"  {issue.where}: {issue.message}" if issue.where else f"  {issue.message}" for issue in issues]
            blocks.append("\n".join(lines))
        return "\n".join(blocks)


class ToolError(Exception):
    """A tool's module or function can't be found, so it can't run."""


# ----------------------------------------------------------------------------------------------------------------
# Versions


def upgrade(data: dict, current: int, updates: Mapping[int, Callable[[dict], None]]) -> None:
    """Runs the steps from data["version"] to current in order, in place. A missing version is version 1.
    Raises ToolDataError for a version newer than current, or for a gap in the table."""
    start = data.get("version", 1)
    if isinstance(start, bool) or not isinstance(start, int) or start < 1:
        raise ToolDataError([Issue("version", f"must be a whole number from 1, not {start!r}")])
    if start > current:
        raise ToolDataError([Issue("version", f"{start} was written by a newer mayadev (this one reads up to {current})")])
    for version in range(start, current):
        step = updates.get(version)
        if step is None:
            if version == start:
                raise ToolDataError([Issue("version", f"version {version} is no longer read")])
            raise ToolDataError([Issue("version", f"the update table has no step from version {version} to {version + 1}")])
        step(data)
        data["version"] = version + 1
    data["version"] = current


# ----------------------------------------------------------------------------------------------------------------
# The check pass: structure


def check_registry(data: dict) -> list[Issue]:
    """Every structural problem of a registry's raw JSON, at its current version."""
    issues: list[Issue] = []
    if not isinstance(data, dict):
        return [Issue("", "the file must hold an object")]
    _check_keys(data, ("version", "tools"), "", issues)
    tools = data.get("tools")
    if not isinstance(tools, list):
        issues.append(Issue("tools", "must be a list"))
        return issues

    ids: dict[str, int] = {}
    names: dict[str, int] = {}
    for index, tool in enumerate(tools):
        where = f"tools[{index}]"
        if not isinstance(tool, dict):
            issues.append(Issue(where, "must be an object"))
            continue
        if isinstance(tool.get("id"), str):
            where = f"{where} ({tool['id']})"
        _check_keys(tool, _TOOL_KEYS, where, issues)
        _check_required(tool, _TOOL_REQUIRED, where, issues)
        _check_tool_values(tool, where, issues)

        tool_id = tool.get("id")
        if isinstance(tool_id, str) and ID_PATTERN.match(tool_id):
            if tool_id in ids:
                issues.append(Issue(where, f"id '{tool_id}' is already used by tools[{ids[tool_id]}]"))
            else:
                ids[tool_id] = index
        name = tool.get("name")
        if isinstance(name, str) and name.strip():
            if name.casefold() in names:
                issues.append(Issue(where, f"name '{name}' is already used by tools[{names[name.casefold()]}]"))
            else:
                names[name.casefold()] = index
    return issues


def _check_keys(data: dict, allowed: Collection[str], where: str, issues: list[Issue]) -> None:
    for key in data:
        if key not in allowed:
            issues.append(Issue(where, f"unknown key '{key}'"))


def _check_required(data: dict, required: Collection[str], where: str, issues: list[Issue]) -> None:
    for key in required:
        if key not in data:
            issues.append(Issue(where, f"missing key '{key}'"))


def _check_tool_values(tool: dict, where: str, issues: list[Issue]) -> None:
    if "id" in tool and not (isinstance(tool["id"], str) and ID_PATTERN.match(tool["id"])):
        issues.append(Issue(where, f"id {tool['id']!r} must be dot-separated lowercase segments such as 'rigmodules.pose.flip'"))
    for key in ("name", "short_name"):
        if key in tool and not (isinstance(tool[key], str) and tool[key].strip()):
            issues.append(Issue(where, f"'{key}' must be a non-empty string"))
    if tool.get("icon") is not None and not isinstance(tool.get("icon"), str):
        issues.append(Issue(where, "'icon' must be a string or null"))
    if "enabled" in tool and not isinstance(tool["enabled"], bool):
        issues.append(Issue(where, "'enabled' must be true or false"))
    if "call" in tool:
        _check_call(tool["call"], f"{where}.call", issues)


def _check_call(call: object, where: str, issues: list[Issue]) -> None:
    if not isinstance(call, dict):
        issues.append(Issue(where, "must be an object"))
        return
    _check_keys(call, _CALL_KEYS, where, issues)
    _check_required(call, _CALL_REQUIRED, where, issues)
    for key in _CALL_REQUIRED:
        if key in call and not (isinstance(call[key], str) and call[key].strip()):
            issues.append(Issue(where, f"'{key}' must be a non-empty string"))
    if "kwargs" in call:
        kwargs = call["kwargs"]
        if not isinstance(kwargs, dict):
            issues.append(Issue(f"{where}.kwargs", "must be an object"))
        else:
            for name, value in kwargs.items():
                if not _is_json_value(value):
                    issues.append(Issue(f"{where}.kwargs", f"'{name}' must be a bool, number, string, null, or a list or object of those"))


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, list):
        return all(_is_json_value(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_json_value(v) for k, v in value.items())
    return False


def check_layout(data: dict, tool_ids: Collection[str]) -> list[Issue]:
    """Every structural problem of a layout's raw JSON, at its current version, against the registry's tool ids."""
    issues: list[Issue] = []
    if not isinstance(data, dict):
        return [Issue("", "the file must hold an object")]
    _check_keys(data, ("version", "label", "items"), "", issues)
    _check_required(data, ("label", "items"), "", issues)
    if "label" in data and not (isinstance(data["label"], str) and data["label"].strip()):
        issues.append(Issue("label", "must be a non-empty string"))
    if not isinstance(data.get("items"), list):
        if "items" in data:
            issues.append(Issue("items", "must be a list"))
        return issues
    _check_items(data["items"], "items", set(tool_ids), {}, issues)
    return issues


def _check_items(items: list, where: str, tool_ids: set[str], seen: dict[str, str], issues: list[Issue]) -> None:
    """seen: tool id -> where it was first used, shared across the whole layout."""
    labels: dict[str, int] = {}
    for index, item in enumerate(items):
        here = f"{where}[{index}]"
        if not isinstance(item, dict):
            issues.append(Issue(here, "must be an object"))
            continue
        item_type = item.get("type")
        if "type" not in item:
            issues.append(Issue(here, "missing key 'type'"))
            continue
        if item_type not in _ITEM_KEYS:
            issues.append(Issue(here, f"unknown item type {item_type!r} (expected tool, separator or submenu)"))
            continue
        _check_keys(item, _ITEM_KEYS[item_type], here, issues)
        _check_required(item, _ITEM_REQUIRED[item_type], here, issues)

        if item_type == "tool":
            _check_tool_item(item, here, tool_ids, seen, issues)
        elif item_type == "submenu":
            label = item.get("label")
            if "label" in item and not (isinstance(label, str) and label.strip()):
                issues.append(Issue(here, "'label' must be a non-empty string"))
            elif isinstance(label, str):
                if label in labels:
                    issues.append(Issue(here, f"submenu label '{label}' is already used by {where}[{labels[label]}]"))
                else:
                    labels[label] = index
            if isinstance(item.get("items"), list):
                _check_items(item["items"], f"{here}.items", tool_ids, seen, issues)
            elif "items" in item:
                issues.append(Issue(f"{here}.items", "must be a list"))


def _check_tool_item(item: dict, where: str, tool_ids: set[str], seen: dict[str, str], issues: list[Issue]) -> None:
    if "enabled" in item and not isinstance(item["enabled"], bool):
        issues.append(Issue(where, "'enabled' must be true or false"))
    tool = item.get("tool")
    if "tool" not in item:
        return
    if not isinstance(tool, str):
        issues.append(Issue(where, "'tool' must be a tool id string"))
    elif tool not in tool_ids:
        issues.append(Issue(where, f"tool '{tool}' is not in the registry"))
    elif tool in seen:
        issues.append(Issue(where, f"tool '{tool}' is already used at {seen[tool]}"))
    else:
        seen[tool] = where


# ----------------------------------------------------------------------------------------------------------------
# The check pass: calls


def check_calls(registry: Registry) -> list[Issue]:
    """Imports each tool's module and checks its function and kwargs. Needs Maya for most tool modules."""
    issues: list[Issue] = []
    for index, tool in enumerate(registry.tools.values()):
        where = f"tools[{index}] ({tool.id}).call"
        issues += [Issue(where, message) for message in check_call(tool.call)]
    return issues


def check_call(call: ToolCall) -> list[str]:
    """The problems of one call, as messages. Empty when it is runnable."""
    try:
        function = resolve_call(call)
    except ToolError as err:
        return [str(err)]
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return []  # a builtin with no signature: nothing to check
    try:
        hints = typing.get_type_hints(function)
    except Exception:  # an annotation that can't be evaluated is not checked
        hints = {}

    messages = []
    parameters = signature.parameters
    takes_any = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())
    for name, value in call.kwargs.items():
        parameter = parameters.get(name)
        if parameter is None or parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            if not takes_any:
                messages.append(f"kwarg '{name}' is not a parameter of {call.function}")
        elif parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            messages.append(f"parameter '{name}' of {call.function} is positional-only, so a kwarg can't give it")
        elif name in hints and not matches_annotation(value, hints[name]):
            messages.append(f"kwarg '{name}' is {value!r}, which does not match its annotation {hints[name]}")
    for name, parameter in parameters.items():
        required = parameter.default is inspect.Parameter.empty and parameter.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
        if required and name not in call.kwargs:
            messages.append(f"required argument '{name}' is not given")
    return messages


def matches_annotation(value: object, hint: object) -> bool:
    """Whether a JSON value fits a simple annotation: bool, int, float, str, None, unions and Literal of those.
    Anything else is not checked and matches."""
    if hint is type(None) or hint is None:
        return value is None
    if hint is bool:
        return isinstance(value, bool)
    if hint is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if hint is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if hint is str:
        return isinstance(value, str)
    origin = typing.get_origin(hint)
    if origin is typing.Literal:
        return any(value == option and type(value) is type(option) for option in typing.get_args(hint))
    if origin is typing.Union or origin is types.UnionType:
        return any(matches_annotation(value, option) for option in typing.get_args(hint))
    return True


# ----------------------------------------------------------------------------------------------------------------
# Running a tool


def resolve_call(call: ToolCall, tool_id: str = "") -> Callable[..., object]:
    """The function a call names. Imports its module now, so a module reloaded since the menu was built is read
    again. Raises ToolError when the module or the function can't be found."""
    prefix = f"Tool {tool_id}: " if tool_id else ""
    if not call.module.strip():
        raise ToolError(f"{prefix}no module is set")
    try:
        module = importlib.import_module(call.module)
    except Exception as err:  # a tool module can fail to import in any way, and that breaks only its own tools
        raise ToolError(f"{prefix}cannot import module '{call.module}': {err}") from err
    function = getattr(module, call.function, None) if call.function else None
    if not callable(function):
        raise ToolError(f"{prefix}no function '{call.function}' in {call.module}")
    return function


def run_tool(tool: Tool) -> object:
    """resolve_call(tool.call)(**tool.call.kwargs). An exception from the function itself is raised unchanged."""
    return resolve_call(tool.call, tool.id)(**tool.call.kwargs)


# ----------------------------------------------------------------------------------------------------------------
# Dataclasses and raw JSON


def registry_to_dict(registry: Registry) -> dict:
    return {
        "version": REGISTRY_VERSION,
        "tools": [
            {
                "id": tool.id,
                "name": tool.name,
                "short_name": tool.short_name,
                "call": {
                    "module": tool.call.module,
                    "function": tool.call.function,
                    "kwargs": dict(tool.call.kwargs),
                },
                "icon": tool.icon,
                "enabled": tool.enabled,
            }
            for tool in registry.tools.values()
        ],
    }


def registry_from_dict(data: dict) -> Registry:
    """Builds a Registry from JSON that passed check_registry."""
    registry = Registry()
    for raw in data["tools"]:
        call = raw["call"]
        tool = Tool(
            id=raw["id"],
            name=raw["name"],
            short_name=raw["short_name"],
            call=ToolCall(call["module"], call["function"], dict(call.get("kwargs", {}))),
            icon=raw.get("icon"),
            enabled=raw.get("enabled", True),
        )
        registry.tools[tool.id] = tool
    return registry


def layout_to_dict(layout: Layout) -> dict:
    return {"version": LAYOUT_VERSION, "label": layout.label, "items": [_item_to_dict(i) for i in layout.items]}


def _item_to_dict(item: LayoutItem) -> dict:
    if isinstance(item, ToolItem):
        return {"type": "tool", "tool": item.tool, "enabled": item.enabled}
    if isinstance(item, Separator):
        return {"type": "separator"}
    return {"type": "submenu", "label": item.label, "items": [_item_to_dict(i) for i in item.items]}


def layout_from_dict(data: dict) -> Layout:
    """Builds a Layout from JSON that passed check_layout."""
    return Layout(data["label"], [_item_from_dict(i) for i in data["items"]])


def _item_from_dict(raw: dict) -> LayoutItem:
    if raw["type"] == "tool":
        return ToolItem(raw["tool"], raw.get("enabled", True))
    if raw["type"] == "separator":
        return Separator()
    return Submenu(raw["label"], [_item_from_dict(i) for i in raw["items"]])


# ----------------------------------------------------------------------------------------------------------------
# Files


def read_registry(path: str) -> Registry:
    """Raises FileNotFoundError naming the path, or ToolDataError with every problem of the file."""
    data = _read_json(path, REGISTRY_VERSION, REGISTRY_UPDATES)
    _raise_if(check_registry(data), path)
    return registry_from_dict(data)


def read_layout(path: str, tool_ids: Collection[str]) -> Layout:
    """Raises FileNotFoundError naming the path, or ToolDataError with every problem of the file, including tools
    that are not in tool_ids."""
    data = _read_json(path, LAYOUT_VERSION, LAYOUT_UPDATES)
    _raise_if(check_layout(data, tool_ids), path)
    return layout_from_dict(data)


def write_registry(registry: Registry, path: str) -> None:
    """Checks, then writes atomically at the current version. An invalid registry is never written."""
    data = registry_to_dict(registry)
    _raise_if(check_registry(data), path)
    _write_json(path, data)


def write_layout(layout: Layout, path: str, tool_ids: Collection[str]) -> None:
    """Checks against the registry's tool ids, then writes atomically at the current version."""
    data = layout_to_dict(layout)
    _raise_if(check_layout(data, tool_ids), path)
    _write_json(path, data)


def load_all(registry_path: str, layout_paths: Sequence[str]) -> tuple[Registry, dict[str, Layout]]:
    """Reads the registry and every layout, and raises one ToolDataError for all the broken files, so one reload
    shows every problem. A broken registry also fails every layout, because their references can't be checked."""
    errors: list[ToolDataError] = []
    layouts: dict[str, Layout] = {}
    try:
        registry = read_registry(registry_path)
    except ToolDataError as err:
        errors.append(err)
        registry = None
    for path in layout_paths:
        try:
            if registry is None:
                # The structure of the layout can still be reported, without its references.
                data = _read_json(path, LAYOUT_VERSION, LAYOUT_UPDATES)
                _raise_if(check_layout(data, _all_references(data)), path)
            else:
                layouts[path] = read_layout(path, registry.tools)
        except ToolDataError as err:
            errors.append(err)
    if errors:
        raise ToolDataError.combine(errors)
    return registry, layouts


def _all_references(data: object) -> set[str]:
    """Every tool id a layout names, so a check without a registry reports structure only."""
    found: set[str] = set()
    if isinstance(data, dict):
        if isinstance(data.get("tool"), str):
            found.add(data["tool"])
        for value in data.values():
            found |= _all_references(value)
    elif isinstance(data, list):
        for value in data:
            found |= _all_references(value)
    return found


def _raise_if(issues: list[Issue], path: str) -> None:
    if issues:
        raise ToolDataError(issues, path)


def _read_json(path: str, current: int, updates: Mapping[int, Callable[[dict], None]]) -> dict:
    """Reads a file, then runs its version updates. Stops early only when the file isn't JSON or its version
    can't be read, because nothing after that means anything."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"The tool file '{path}' does not exist") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise ToolDataError([Issue("", f"not valid JSON: {err}")], path) from None
    if not isinstance(data, dict):
        raise ToolDataError([Issue("", "the file must hold an object")], path)
    try:
        upgrade(data, current, updates)
    except ToolDataError as err:
        raise ToolDataError(err.issues, path) from None
    return data


def _write_json(path: str, data: dict) -> None:
    """Serializes first, so a value that can't be written fails before the file is touched, then writes a temp
    file in the same folder and replaces the original with it, so a crash can't leave a truncated file."""
    text = json.dumps(data, indent=4, ensure_ascii=False) + "\n"
    temp = f"{path}.tmp"
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            os.remove(temp)
        except OSError:
            pass
        raise
