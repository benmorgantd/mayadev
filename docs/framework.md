# Framework

The general tooling under the asset and rig code: the logger, the progress manager, `Event`, the events registry, the batch framework, the Qt layer and the doc generator. None of it knows about rigs. How a tool asks the user (the `Prompter`) and the registration pass that wires the layers together are in [`architecture.md`](architecture.md#the-registration-pass).

## Logger

`bmaya.core.log` wraps the standard `logging` module under the logger name `bmaya`.

```python
import bmaya.core.log

bmaya.core.log.info("Saved the skeleton")
bmaya.core.log.warning("These meshes have no meshId")
```

| Function | Does |
|---|---|
| `init_logger()` | Configures the `bmaya` logger at `DEBUG`, replacing its handlers, with one `LogOutput` handler at `INFO`. Format `[LEVEL] file.py:line >> message` |
| `get_logger()` | The logger, initializing it on first use |
| `debug`, `info`, `warning`, `error` | Log at that level. They set `stacklevel`, so the file and line are the caller's. `error` attaches the exception when one is being handled |

| `register_writers(writers)`, `reset_writers()` | Fill the writers slot (a function per level), or put the default back |

The module is plain Python. `LogOutput` writes each record with the writer registered for the highest level at or below the record's, and with nothing registered for it, to `sys.stdout`, read when the record is written, so the batch framework's capture sees it. `bmaya.maya.startup.register()` fills the slot in a GUI session: `INFO` to `MGlobal.displayInfo`, `WARNING` to `displayWarning` and `ERROR` to `displayError`, so messages show in Maya's Script Editor and command line. A batch session (`mayapy`, or `maya -batch` running `userSetup.py`) keeps stdout.

## Progress manager

`bmaya.core.progressmanager.ProgressManager` is a singleton that tracks one task's progress: a view-model any number of views can watch.

| Member | Does |
|---|---|
| `start(status, max_value=100)` | Begins a session |
| `update(value, status=None)`, `increment(amount=1, status=None)` | Set or advance the value. Ignored when no session is active |
| `end()` | Ends the session and resets the value |
| `changed` | An `Event`, emitted on every change. Connect a view's refresh method to it |
| `with ProgressManager():` | Ends the session on exit, and logs an error when the block raised. It never swallows the exception |

`userSetup.py` uses it to report startup steps, and `bmaya.maya_ui.qtbase.ProgressWindow` is the window that shows it. The `Event` holds the window weakly, so whoever opens the window keeps a reference to it (`userSetup.py` keeps `_progress_window`).

## Event

`bmaya.core.observable.Event` is change notification without Qt, so a view-model in `bmaya.core` or `bmaya.maya` can tell a view what changed.

```python
from bmaya.core.observable import Event

changed = Event()
changed.connect(view.refresh)     # a Python bound method is held weakly: a closed view drops out
changed.emit()
```

| Method | Does |
|---|---|
| `connect(listener)`, `disconnect(listener)` | Add or remove a listener. Connecting the same one twice calls it once |
| `emit(*args)` | Calls every live listener in the order they connected |
| `listeners()` | The live listeners |

A Python bound method is held weakly. A function, a lambda or a built-in method (`list.append`) is held strongly.

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

Run it with mayapy (`batch\docgen\run.bat` is the working example, with `PYTHONPATH` set to `%MAYADEV_ROOT%\py\scripts`).

The framework runs in the process that hosts it, so it does not start mayapy and a crash ends the whole batch. To start a mayapy from a script, with a timeout and without a crash dialog, use `mayalaunch`, which this framework and RigModules share: `mayalaunch.run_mayapy(script, args, mayalaunch.child_environment(), timeout=...)`. It lives in RigModules (`python\mayalaunch`), which `RigModules.mod` puts on `PYTHONPATH`, so mayadev depends on it the same way it depends on `rigmodules`. A bare mayapy needs `%RIGMODULES_ROOT%\python` on `PYTHONPATH` (the batch files set it), and the framework raises an `ImportError` saying so when it is missing. `tests\core\test_maya_batch.py` runs a job through it end to end.

`run_suite` writes the job's results folder: `executed_script.py` (a copy of the job's source), `batch_config.json`, `processed_files.txt`, `succeeded_files.txt`, `failed_files.txt` (each failure with its traceback), `session_output.log` and `report_summary.md`, which it opens in the default application when the run ends. An exception in one item is recorded as a failure and the next item still runs.

## Qt layer

Layouts are written in Python: there are no Qt Designer files.

### Base classes

`bmaya.maya_ui.qtbase` (PySide6, for Maya 2026).

| Name | Is |
|---|---|
| `SimpleWindow`, `SimpleWidget` | A main window (with a `mainLayout`) and a widget, with a title. They delete themselves on close. Open one with `host.show`, which keeps one open per object name |
| `Tree`, `TreeItem` | Convenience subclasses for the Menu Editor. `Tree` has `items` and `topLevelItems`, and `TreeItem` has `parents`, `children` and `name` |
| `Dialog`, `ConfirmDialog` | A dialog, and a modal confirm that returns a boolean |
| `ProgressWindow` | Shows the progress manager: listens to its `changed` `Event`, shows itself while a task is active and hides when it ends |
| `PythonSyntaxHighlighter` | Python highlighting for a `QTextDocument`. No window uses it now: the registry editor picks a function and no longer holds script text |

### Theme

`bmaya.maya_ui.theme` is the one look every bmaya window shares: a dark, flat style modelled on Visual Studio Code's Dark+ (neutral greys, one blue accent, a chevron for every fold and drop-down). It replaces Maya's default grey, and in particular the bright blue a checked button gets. It is Qt only.

| Name | Does |
|---|---|
| `apply(widget)` | Styles a top-level widget and everything in it: its font size, background and style sheet. It never touches the application, so Maya's own windows keep their look. `host.show`, `SimpleWindow`, `Dialog` (so `ConfirmDialog`), `FormDialog` and the prompter's confirm box call it. A window made another way calls it once on its top-level widget |
| `Palette`, `DARK` | Every colour of the theme (`window`, `raised`, `header`, `input`, `border`, `text`, `accent`, `selection`, `error` ...). Change a colour here and nowhere else |
| `stylesheet(palette=DARK)` | The Qt style sheet. It covers buttons, fields, drop-downs, spin boxes, sliders, check boxes, radio buttons, lists, trees, tables, tabs, menus, scroll bars, progress bars and tool tips |
| `icon(name)`, `icon_folder()` | The icons the sheet needs (`chevron_down`, `chevron_right`, `chevron_up`, `check`, `dot`) and the ones for widgets to set with `button.setIcon(theme.icon("key"))` (`plus`, `minus`, `mirror`, `rotate`, `scale`, `translate`, `key` for a keyframe diamond, `module` for a cube), drawn in code into the temp folder `bmaya_theme/<palette hash>`, because a style sheet can only name an image by a file path |

A widget that must differ sets a property the sheet reads and not a style sheet of its own: `button.setProperty("primary", True)` for the accent button, `setProperty("muted", True)` or `setProperty("error", True)` on a label. A checked `QPushButton` (the Space buttons) shows in the accent colour by design. `ERROR_STYLE` in `widgets.py` takes its colour from the palette. The Naming Tool's orange Rename button still sets its own colours, and `QtPrompter`'s text, choice and file dialogs are Qt's static dialogs, which have no instance to style, so they keep Maya's look.

### Host

`bmaya.maya_ui.host` is Maya as the host of a window. It and `menus.py` are the only files in `maya_ui` that import Maya, and a test checks that. Outside Maya every function still works.

| Name | Does |
|---|---|
| `parent_window()` | Maya's main window as a Qt widget, to parent a tool to so it stays above Maya's. `None` in mayapy and in plain Python |
| `show(widget, object_name=..., dock=False, width=385, height=735, beside="AttributeEditor")` | Sets the widget's object name and shows it, **once**: a visible window with the same object name is closed first. When that window refuses to close (the Registry Editor with unsaved edits the user keeps), it is raised and the new widget is dropped. Returns the window on screen. `dock=True` puts the widget in a workspace control tabbed with the one named by `beside` (the Attribute Editor by default, and also when `beside` is not open), and is a plain window outside a GUI Maya. The control is named `<object name>WorkspaceControl` (`dock_control_name`), because Maya refuses a control whose name another object has, and the control and the widget are deleted when it closes. |
| `find(object_name)` | The visible top-level widget with that object name |
| `defer(function)` | Calls `function` when Maya is idle (`maya.utils.executeDeferred`), or from the Qt event loop outside Maya |

Each window's `show_window()` is `host.show(Window(parent=host.parent_window()), object_name=...)`. A window's constructor takes its parent and never looks for Maya itself.

### Prompter and forms

`bmaya.maya_ui.prompter.QtPrompter(parent_window)` is the `Prompter` of a GUI session: each question is a Qt dialog on the window `parent_window()` returns. `bmaya.maya_ui.startup` registers it with `host.parent_window`. It imports no Maya.

| Question | Dialog |
|---|---|
| `ask_text(title, message, default="")` | `QInputDialog.getText`. Empty or cancelled is `None` |
| `choose(title, message, options)` | `QInputDialog.getItem`, not editable |
| `confirm(title, message, accept="OK")` | A `QMessageBox` with an `accept` button and Cancel, Cancel the default |
| `ask_file(title, file_filter, save, folder="")` | `QFileDialog.getSaveFileName` or `getOpenFileName`. `file_filter` is Qt's, `"Pose files (*.json)"` |
| `ask_folder(title, folder="")` | `QFileDialog.getExistingDirectory` |
| `ask_form(title, value)` | A `FormDialog`: a `DataclassForm` for the dataclass instance `value`, with OK and Cancel. OK stays open, with the problem shown, while a field's value is invalid |

`bmaya.maya_ui.widgets` builds editors from type hints, for every form:

| Name | Is |
|---|---|
| `field_widget(hint, on_change=None)` | One value's widget: a check box for `bool`, spin boxes for `int` and `float`, a line edit for `str`, a drop-down for `Literal` and `Enum`, JSON text for anything else. `X \| None` is `X`. `on_change()` is called when the user edits it |
| `show_value(widget, hint, value)`, `read_value(widget, hint)` | Put a value in the widget and take it out. An `Enum` field takes a member or its value and reads back its member. `read_value` raises `ValueError` for JSON text that isn't JSON |
| `DataclassForm(value)` | A labelled editor per field of a dataclass instance, with a `changed` signal. `value()` returns a copy with the edits, and raises `ValueError` naming a field whose JSON text isn't JSON |
| `CollapsibleSection(title, expanded=True)` | A framed section with a bold title bar that folds it: a down chevron when open, a right chevron when folded (`header` is a `QPushButton` named `sectionHeader`, which the theme styles). Put widgets in `content_layout`. `set_expanded`, `is_expanded` and a `toggled(bool)` signal |
| `SignatureForm(function, kwargs)` | One row per parameter of a function, filled from saved `kwargs`: an editor and a **Set** check box. An unset row shows the default greyed and `kwargs()` leaves it out. A parameter with no default is always set. A saved kwarg the function no longer has is a red row with a Remove button (`stale`, `remove_stale(name)`). `kwargs()` keeps an `Enum` argument as its value, which is what the registry's JSON holds. Build a new form when the function changes |

```python
@dataclasses.dataclass(frozen=True)
class ClipSettings:                  # bmaya.maya.assettools
    loop: bool = False
    root_motion: bool = False
    additive: typing.Literal[bmaya.core.asset.animproperties.ADDITIVE_TYPES] = "none"

settings = prompter.ask_form("Clip Properties", ClipSettings(loop=True))   # two check boxes and a drop-down
```

### ListModel

`widgets.ListModel(roles, items, columns=None)` is a Qt item model over a Python list (RigModules D51). A view-model sets the items with `set_items` (a model reset), and a view shows them as a `QListView` (one column) or a `QTableView` (columns). `roles` maps a Qt role (`DisplayRole`, `ToolTipRole`, `DecorationRole`, `UserRole`) to a function of an item, and `columns` is a list of `(header, display function)`. A role other than the display one applies to every column. `row_of(matches)` finds an item's row again after a reset, which is how a view keeps its selection. It is a `QAbstractTableModel` and not the `QAbstractListModel` the design named, so one model serves the list and the details table. It holds none of its owner's logic. A `QSortFilterProxyModel` works over it (the library browser sorts its table that way, by a column's sort key through a role). A subclass that overrides `data` can change a role per column: the browser's `EntryModel` puts the icon in the Name column only.

### TagsEdit

`widgets.TagsEdit` is a `QLineEdit` for tags separated by commas. `set_tags_in_use(tags)` gives it the tags a library already uses, and while the animator types a tag a pop-up offers those that start with it, ignoring case, so a library keeps one spelling of a tag. Picking one replaces only the word under the cursor. `tags()` returns the tags trimmed, with no empty ones and no repeats, and `set_tags(tags)` writes them back. The library browser uses it for Save and for Edit Tags.

### Naming tool

`bmaya.maya_ui.namingTool` is a small window (a name, a side and a type) built on `SimpleWindow`. It reads its side and type names from `bmaya.core.constants`, the older rig builder's naming constants ([`status.md`](status.md)).

## Doc generator (deprecated)

`batch/docgen/main.py` is a batch job (`CodebaseDocGenerator`) that writes the API reference in `py/scripts/docs` and updates `py/scripts/mkdocs.yml`. It, the mkdocs site and the two old guides are deprecated ([`README.md`](README.md#the-old-mkdocs-site-deprecated)): the maintained documentation is this `docs/` folder. The generator still works, logs a deprecation warning, and is kept only because its API pages have no replacement.

`batch/docgen/run.bat` runs it in mayapy, and `start_docs_server.bat` serves the site with `python -m mkdocs serve` at `http://127.0.0.1:8000`. It walks `py/scripts/bmaya`, skips `__init__.py` and the batch folders, and for each module tries to import and inspect it, falling back to parsing the source with `ast` when the import fails. A file that fails both (the three Python 2 files listed in [`status.md`](status.md)) is logged as an error and gets no page. It then rewrites the `nav` in `mkdocs.yml` (everything above `nav:` is kept) and starts the server.

The generated pages are not edited by hand, and a module's top docstring is the first thing a reader of its page sees.
