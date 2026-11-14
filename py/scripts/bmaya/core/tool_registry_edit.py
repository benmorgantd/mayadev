"""The Registry Editor's state and commands, with no Qt: which tool is picked, what was edited, whether it is saved.

A view binds to a RegistryEditSession: it reads the state, calls the commands and listens to the events. Every
editing rule (dirty tracking, the status line, the checked save) is here, so mayapy or a plain-Python test can drive
it without a window (RigModules design/mayadev-ui.md, D49). The call picker's module and function lists are here for
the same reason. This module is Maya-free: the paths of the master registry and its layouts are arguments, and
check_call imports the tool modules.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import os
import types
import typing
from collections.abc import Sequence

from bmaya.core import tool_registry
from bmaya.core.observable import Event
from bmaya.core.tool_registry import Registry, Tool, ToolCall, ToolDataError

PACKAGES = ("bmaya", "rigmodules")
STATUS_OK = "OK"
# The Tool fields set_field edits. The id is not one of them: a rename is a hand edit of the registry and every layout.
FIELDS = ("name", "short_name", "icon", "enabled")


def list_modules() -> list[str]:
    """Every module under the tool packages, for the module completer. Reads the folders and imports nothing:
    pkgutil skips folders without an __init__.py, and bmaya and bmaya.maya are namespace packages."""
    names: list[str] = []
    for package in PACKAGES:
        spec = importlib.util.find_spec(package)
        if spec is None or not spec.submodule_search_locations:
            continue
        names.append(package)
        for location in spec.submodule_search_locations:
            for folder, folders, files in os.walk(location):
                folders[:] = [f for f in folders if not f.startswith(("_", "."))]
                relative = os.path.relpath(folder, location)
                prefix = package if relative == "." else f"{package}.{relative.replace(os.sep, '.')}"
                if relative != ".":
                    names.append(prefix)
                names += [f"{prefix}.{f[:-3]}" for f in files if f.endswith(".py") and f != "__init__.py"]
    return sorted(set(names))


def list_functions(module: types.ModuleType) -> list[str]:
    """The public functions defined in a module, in the order they are written."""
    functions = [
        (function.__code__.co_firstlineno, name)
        for name, function in inspect.getmembers(module, inspect.isfunction)
        if function.__module__ == module.__name__ and not name.startswith("_")
    ]
    return [name for _, name in sorted(functions)]


def import_module(name: str) -> tuple[types.ModuleType | None, str]:
    """The module, or None and the reason."""
    if not name:
        return None, "no module"
    try:
        return importlib.import_module(name), ""
    except Exception as err:  # a tool module can fail to import in any way
        return None, f"cannot import module '{name}': {err}"


class RegistryEditSession:
    """A registry being edited: the picked tool, the unsaved flag, and the commands on both.

    Events, each emitted with no arguments:
      tools_changed      the set of tools changed (a registry was loaded, a tool added or deleted)
      selection_changed  another tool was picked, or none
      changed            the picked tool or the unsaved flag changed
    """

    def __init__(self, registry: Registry | None = None, path: str = "", master_path: str = "",
                 layout_paths: Sequence[str] = ()) -> None:
        """master_path is the registry the menus are built from, and layout_paths their layout files: saving to
        master_path also checks every layout against the edited registry."""
        self.registry = registry or Registry()
        self.path = path
        self.master_path = master_path
        self.layout_paths = tuple(layout_paths)
        self.active_tool_id: str | None = None
        self.dirty = False
        self.tools_changed = Event()
        self.selection_changed = Event()
        self.changed = Event()
        self._input_problem = ""
        self._module_names: list[str] | None = None

    @classmethod
    def open(cls, path: str, master_path: str = "", layout_paths: Sequence[str] = ()) -> RegistryEditSession:
        """Raises FileNotFoundError naming the path, or ToolDataError with every problem of the file."""
        return cls(tool_registry.read_registry(path), path, master_path, layout_paths)

    # --- the registry ----------------------------------------------------------------------------------------

    def load(self, path: str) -> None:
        """Replaces the registry with a file's. Raises as open does, and then keeps the current registry."""
        registry = tool_registry.read_registry(path)
        self.registry = registry
        self.path = path
        self.dirty = False
        self.tools_changed.emit()
        self.select(None)

    @property
    def tool(self) -> Tool | None:
        """The picked tool."""
        return self.registry.tools.get(self.active_tool_id) if self.active_tool_id else None

    def search(self, text: str) -> list[str]:
        """The ids of the tools whose name, short name or id contains text, ignoring case, in registry order."""
        text = text.lower()
        return [tool.id for tool in self.registry.tools.values()
                if text in tool.name.lower() or text in tool.short_name.lower() or text in tool.id]

    def select(self, tool_id: str | None) -> None:
        """Picks a tool, or none. Raises KeyError for an id the registry doesn't have."""
        if tool_id is not None and tool_id not in self.registry.tools:
            raise KeyError(tool_id)
        self.active_tool_id = tool_id
        self._input_problem = ""
        self.selection_changed.emit()

    def id_problem(self, tool_id: str) -> str:
        """Why an id can't be given to a new tool, or an empty string."""
        if not tool_registry.ID_PATTERN.match(tool_id):
            return "The id is dot-separated lowercase segments, such as rigmodules.pose.flip."
        if tool_id in self.registry.tools:
            return f"The id '{tool_id}' is already used."
        return ""

    def add_tool(self, tool_id: str, name: str) -> None:
        """Adds a tool and picks it. Its call is empty, and a save is refused until one is set. Raises ValueError
        for a bad or used id, or an empty name."""
        problem = self.id_problem(tool_id) or ("" if name.strip() else "A tool needs a name.")
        if problem:
            raise ValueError(problem)
        self.registry.tools[tool_id] = Tool(tool_id, name.strip(), name.strip(), ToolCall("", ""))
        self.dirty = True
        self.tools_changed.emit()
        self.select(tool_id)

    def delete_tool(self) -> None:
        """Removes the picked tool. A layout that still uses it is reported when the registry is saved."""
        if self.active_tool_id is None:
            return
        self.registry.tools.pop(self.active_tool_id, None)
        self.dirty = True
        self.tools_changed.emit()
        self.select(None)

    # --- editing the picked tool -----------------------------------------------------------------------------

    def set_field(self, name: str, value: object) -> None:
        """Sets name, short_name, icon (an empty string clears it) or enabled. Nothing happens for the value it
        already has."""
        if name not in FIELDS:
            raise ValueError(f"'{name}' is not an editable field: {', '.join(FIELDS)}")
        tool = self._require_tool()
        if name == "icon":
            value = str(value) if str(value).strip() else None
        if getattr(tool, name) != value:
            setattr(tool, name, value)
            self._edited()

    def set_call(self, module: str, function: str, kwargs: dict[str, object] | None = None) -> None:
        """Sets the call. The kwargs are empty unless given, because another function has other parameters."""
        call = self._require_tool().call
        module, kwargs = module.strip(), dict(kwargs or {})
        self._input_problem = ""
        if (call.module, call.function, call.kwargs) != (module, function, kwargs):
            call.module, call.function, call.kwargs = module, function, kwargs
            self._edited()
        else:
            self.changed.emit()

    def set_kwargs(self, kwargs: dict[str, object]) -> None:
        """Sets the call's kwargs."""
        call = self._require_tool().call
        self._input_problem = ""
        if call.kwargs != kwargs:
            call.kwargs = dict(kwargs)
            self._edited()
        else:
            self.changed.emit()

    def report_input_problem(self, problem: str) -> None:
        """A view's input that can't become a value yet (JSON text that isn't JSON). It is the status until the next
        set_call, set_kwargs or pick, and the call keeps its last good kwargs."""
        self._input_problem = problem
        self.changed.emit()

    def status(self) -> str:
        """OK, or the first problem of the picked tool's call."""
        tool = self.tool
        if tool is None:
            return ""
        return self._input_problem or next(iter(tool_registry.check_call(tool.call)), "") or STATUS_OK

    def can_run(self) -> bool:
        return self.status() == STATUS_OK

    def run(self) -> object:
        """Runs the picked tool as it is being edited, the way a menu item does. An exception from the tool itself
        is raised unchanged."""
        return tool_registry.run_tool(self._require_tool())

    # --- the call picker -------------------------------------------------------------------------------------

    def module_names(self) -> list[str]:
        """list_modules(), found on first use because walking the packages imports each package."""
        if self._module_names is None:
            self._module_names = list_modules()
        return self._module_names

    def function_names(self, module_name: str, keep: str = "") -> list[str]:
        """The module's public functions, with keep added when it isn't one, so a saved call that no longer
        resolves is still shown."""
        module, _ = import_module(module_name.strip())
        names = list_functions(module) if module else []
        if keep and keep not in names:
            names.append(keep)
        return names

    def function(self) -> typing.Callable | None:
        """The picked tool's function, or None when its call doesn't resolve."""
        tool = self.tool
        if tool is None:
            return None
        module, _ = import_module(tool.call.module)
        function = getattr(module, tool.call.function, None) if module else None
        return function if callable(function) else None

    def doc(self) -> str:
        """The first line of the picked tool's function's docstring."""
        function = self.function()
        doc = inspect.getdoc(function) if function else None
        return doc.splitlines()[0] if doc else ""

    # --- saving ----------------------------------------------------------------------------------------------

    def check(self, path: str | None = None) -> ToolDataError | None:
        """The structure check and the calls check of the whole registry, and every menu layout against it when
        the path is the master registry. None when all pass."""
        path = path or self.path
        errors = []
        issues = tool_registry.check_registry(tool_registry.registry_to_dict(self.registry))
        issues += tool_registry.check_calls(self.registry)
        if issues:
            errors.append(ToolDataError(issues, path))
        if self.master_path and os.path.normcase(path) == os.path.normcase(self.master_path):
            for layout_path in self.layout_paths:
                try:
                    tool_registry.read_layout(layout_path, self.registry.tools)
                except FileNotFoundError as err:
                    errors.append(ToolDataError([tool_registry.Issue("", str(err))], layout_path))
                except ToolDataError as err:
                    errors.append(err)
        return ToolDataError.combine(errors) if errors else None

    def save(self, path: str | None = None) -> None:
        """Checks the whole registry and the layouts, then writes atomically to path, or to the path it was opened
        from. Raises ToolDataError with the full report and writes nothing when a check fails, ValueError when
        there is no path, or OSError."""
        target = path or self.path
        if not target:
            raise ValueError("no file to save to")
        report = self.check(target)
        if report is not None:
            raise report
        tool_registry.write_registry(self.registry, target)
        self.path = target
        self.dirty = False
        self.changed.emit()

    # --- private ---------------------------------------------------------------------------------------------

    def _require_tool(self) -> Tool:
        tool = self.tool
        if tool is None:
            raise ValueError("no tool is picked")
        return tool

    def _edited(self) -> None:
        self.dirty = True
        self.changed.emit()
