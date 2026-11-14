# Framework

The general tooling under the asset and rig code: the logger, the progress manager, the events registry, the batch framework, the Qt base classes and the doc generator. None of it knows about rigs.

## Logger

`bmaya.core.log` wraps the standard `logging` module under the logger name `bmaya`.

```python
import bmaya.core.log

bmaya.core.log.info("Saved the skeleton")
bmaya.core.log.warning("These meshes have no meshId")
```

| Function | Does |
|---|---|
| `init_logger(is_batch=False)` | Configures the `bmaya` logger at `DEBUG`, replacing its handlers, with one handler at `INFO`. Format `[LEVEL] file.py:line >> message` |
| `get_logger()` | The logger, initializing it on first use |
| `debug`, `info`, `warning`, `error` | Log at that level. They set `stacklevel`, so the file and line are the caller's. `error` attaches the exception when one is being handled |

The default handler, `MayaLogHandler`, sends `ERROR` and above to `MGlobal.displayError`, `WARNING` to `displayWarning` and the rest to `displayInfo`, so messages show in Maya's Script Editor and command line. With `is_batch=True` the handler writes to `sys.stdout`, which the batch framework captures.

Startup calls `init_logger()` without `is_batch`, so a batch session (`mayapy` running `userSetup.py`) also gets the Maya handler. Pass the flag where stdout is the target.

## Progress manager

`bmaya.core.progressmanager.ProgressManager` is a singleton that tracks one task's progress, which a UI watches.

| Member | Does |
|---|---|
| `start(status, max_value=100)` | Begins a session |
| `update(value, status=None)`, `increment(amount=1, status=None)` | Set or advance the value. Ignored when no session is active |
| `end()` | Ends the session and resets the value |
| `register_callback(callback)` | One UI callback, called on every change. A bound method is held weakly, with the window kept alive through `_ui_window` |
| `with ProgressManager():` | Ends the session on exit, and logs an error when the block raised. It never swallows the exception |

`userSetup.py` uses it to report startup steps, and `bmaya.maya_ui.qtbase.ProgressWindow` is the window that shows it.

## Events registry

`bmaya.maya.eventsregistry.EventsRegistry` is a singleton that owns the session's `OpenMaya` (API 2) callbacks, so each is tracked, can be paused, and is removed on exit. It registers its own `kMayaExiting` callback that unregisters everything.

```python
from bmaya.maya.eventsregistry import EventsRegistry

registry = EventsRegistry()
registry.add_selection_changed_callback("my_tool_selection", on_selection)
registry.pause("my_tool_selection")
registry.unregister("my_tool_selection")
```

| Method | Callback registered |
|---|---|
| `add_maya_closing_callback(key, fn)` | Maya is about to exit |
| `add_maya_new_scene_callback(key, fn)`, `add_maya_open_scene_callback(key, fn)` | After a new scene, and after a scene opens |
| `add_selection_changed_callback(key, fn)` | The selection changed |
| `add_node_added_callback(key, fn, node_type="dependNode")` | A node of the type was added |
| `unregister(key)`, `unregister_all()` | Remove one or every callback |
| `pause(key)`, `resume(key)` | Suspend and restore a callback without losing its registration. Both return whether they changed anything |
| `callbacks`, `active_callbacks` | The registered keys' data, and the keys that aren't paused |

Every callback has a unique string `key`. Registering a key that exists logs a warning and replaces the old callback. The categories are the `EventType` constants: `MAYA_CLOSING`, `NODE_ADDED`, `SELECTION_CHANGED`, `SCENE_NEW`, `SCENE_OPEN`.

`@pause_callbacks([EventType.NODE_ADDED])` pauses every callback of the listed categories while the decorated function runs and resumes them in a `finally`, so an error can't leave a callback paused. Use it around code that makes many nodes.

`bmaya.maya.activerig.ActiveRigTracker` is the main client ([`tools.md`](tools.md#the-active-rig)).

## Batch framework

A mayapy runner for a function over a list of scene files, with logs and a Markdown report.

| Class | Layer | Does |
|---|---|---|
| `BaseBatchEnvironment` | `bmaya.core.batch` | Makes a results folder, `<root_dir>\<prefix>_<timestamp>` (`root_dir` defaults to `~\Documents\batch\logs`), and a file log in it. Plain Python |
| `BaseBatchPackage` | `bmaya.core.batch` | A job: a file list (or a JSON config with `file_list`), and `execute(item_path)` to override. `run_suite(environment, open_report=True)` runs it over every item. Pass `open_report=False` for an unattended run |
| `MayaBatchEnvironment` | `bmaya.maya.batch` | Adds Maya: redirects stdout and stderr, at the OS level and in Python, into `session_output.log` in `<root_dir>\<folder>` (`root_dir` defaults to `~\Documents\maya\mayabatch_logs`), then starts standalone Maya, with `userSetup.py`. Restores everything and uninitializes on exit. The redirect and Maya's start and stop are `mayalaunch`'s (below) |
| `MayaStandaloneBatchPackage` | `bmaya.maya.batch` | Opens each file with `cmds.file(open=True, force=True)` before `execute`. An empty file list runs once on a new blank scene |
| `run_batch_test(job_class, file_list=None, config_path=None)` | `bmaya.maya.batch.runner` | Adds `MAYADEV_ROOT\py\scripts` to `sys.path`, builds the job and runs it inside a `MayaBatchEnvironment` |

A job is a subclass with `execute` returning `(success, message)`:

```python
from bmaya.maya.batch.runner import run_batch_test
from bmaya.maya.batch.maya_batch_framework import MayaStandaloneBatchPackage


class CheckJoints(MayaStandaloneBatchPackage):
    def execute(self, item_path):
        import maya.cmds as cmds
        return bool(cmds.ls(type="joint")), "has joints"


if __name__ == "__main__":
    run_batch_test(CheckJoints, file_list=[r"D:\scenes\hero.ma"])
```

Run it with mayapy (`tests\basic\startup_test\run.bat` is the working example, with `PYTHONPATH` set to `%MAYADEV_ROOT%\py\scripts`).

The framework runs in the process that hosts it, so it does not start mayapy and a crash ends the whole batch. To start a mayapy from a script, with a timeout and without a crash dialog, use `mayalaunch`, which this framework and RigModules share: `mayalaunch.run_mayapy(script, args, mayalaunch.child_environment(), timeout=...)`. It lives in RigModules (`python\mayalaunch`), which `RigModules.mod` puts on `PYTHONPATH`, so mayadev depends on it the same way it depends on `rigmodules`. A bare mayapy needs `%RIGMODULES_ROOT%\python` on `PYTHONPATH` (the batch files set it), and the framework raises an `ImportError` saying so when it is missing. `tests\core\test_maya_batch.py` runs a job through it end to end.

`run_suite` writes the job's results folder: `executed_script.py` (a copy of the job's source), `batch_config.json`, `processed_files.txt`, `succeeded_files.txt`, `failed_files.txt` (each failure with its traceback), `session_output.log` and `report_summary.md`, which it opens in the default application when the run ends. An exception in one item is recorded as a failure and the next item still runs.

## Qt base classes

`bmaya.maya_ui.qtbase` (PySide6, for Maya 2026).

| Name | Is |
|---|---|
| `get_maya_main_window()` | The main window as a Qt widget, to parent a tool to |
| `loadUiFile(designerFile, parent)` | Loads a Designer `.ui` file |
| `SimpleWindow`, `SimpleWidget` | A main window and a widget with an optional Designer file and a title. Pass `get_maya_main_window()` as `parent` to keep a window above Maya's. `SimpleWindow` deletes an existing UI of the same title first and deletes itself on close |
| `DockableWidget` | A widget that docks into Maya's UI (`dock(width, height)`) |
| `Table`, `List`, `Tree`, `TreeItem` | Convenience subclasses. `Tree` has `items()` and `topLevelItems()`, and `TreeItem` has `parents()`, `children()` and `name()` |
| `Dialog`, `ConfirmDialog` | A dialog, and a modal confirm that returns a boolean |
| `ProgressWindow` | The window the progress manager updates (`refresh_ui`) |
| `PythonSyntaxHighlighter` | Python highlighting for a `QTextDocument`. No window uses it now: the registry editor picks a function and no longer holds script text |

`bmaya.maya_ui.namingTool` is a small window (a name, a side and a type) built on `SimpleWindow`. It reads its side and type names from `bmaya.core.constants`, the older rig builder's naming constants ([`status.md`](status.md)).

## Doc generator (deprecated)

`batch/docgen/main.py` is a batch job (`CodebaseDocGenerator`) that writes the API reference in `py/scripts/docs` and updates `py/scripts/mkdocs.yml`. It, the mkdocs site and the two old guides are deprecated ([`README.md`](README.md#the-old-mkdocs-site-deprecated)): the maintained documentation is this `docs/` folder. The generator still works, logs a deprecation warning, and is kept only because its API pages have no replacement.

`batch/docgen/run.bat` runs it in mayapy, and `start_docs_server.bat` serves the site with `python -m mkdocs serve` at `http://127.0.0.1:8000`. It walks `py/scripts/bmaya`, skips `__init__.py` and the batch folders, and for each module tries to import and inspect it, falling back to parsing the source with `ast` when the import fails. A file that fails both (the three Python 2 files listed in [`status.md`](status.md)) is logged as an error and gets no page. It then rewrites the `nav` in `mkdocs.yml` (everything above `nav:` is kept) and starts the server.

The generated pages are not edited by hand, and a module's top docstring is the first thing a reader of its page sees.
