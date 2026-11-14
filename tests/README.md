# Tests

The mayadev tests use `unittest`. Most of them need nothing but Python, and the ones that need Maya run in `mayapy` against a RigModules plugin build. They were read for this page, not run: the environment that wrote it has no Maya.

## Running them

| Suite | Command | Needs |
|---|---|---|
| `bmaya.core.asset` model and `animproperties` | `python -m unittest discover -s tests/asset -p "test_asset_*.py"` | Python 3 |
| Handlers, tools and active rig | `tests\asset\run.bat` (after the line above) | mayapy, a RigModules `.mll` in `RIGMODULES_PLUGIN` |
| Tool registry, layer rules, slots, prompts, `Event` | `python -m unittest discover -s tests/core -p "test_core_*.py"` | Python 3 |
| Editors, `build_menus`, registration passes, Qt prompter and forms | `tests\core\run.bat` (after the line above) | mayapy (offscreen Qt, no plugin) |
| RigModules menu layout and tools | `tests\rigging\rigmodules_menu\run.bat` | Layout checks: Python. `check_calls` over the registry: mayapy. Tool runs: mayapy and `RIGMODULES_PLUGIN` |
| Startup smoke test | `tests\basic\startup_test\run.bat` | mayapy, `MAYADEV_ROOT` |

- `tests\asset\run.bat` runs the plain Python tests first and stops if they fail, then the Maya ones.
- The Maya tests **skip** without `RIGMODULES_PLUGIN`, or without `maya`, so a run with skips has not checked the boundary with RigModules ([`../docs/rigmodules.md`](../docs/rigmodules.md)). Read the skip count.
- Copy the `.mll` and point `RIGMODULES_PLUGIN` at the copy when a Maya session has the build loaded, because a loaded plugin locks the file.
- The Maya tests need RigModules' `rigmodules` and `mayalaunch` packages on `PYTHONPATH` (`RigModules.mod`, or its `python` folder). `test_maya_batch.py` skips without `mayalaunch`.
- The batch files set `MAYA_SKIP_USERSETUP_PY=1` so Maya starts without `userSetup.py` and the tests see the plugin alone. They call `C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe`.
- The startup test runs through the batch framework, which writes a results folder under `~\Documents\maya\mayabatch_logs` ([`../docs/framework.md`](../docs/framework.md#batch-framework)).

## What each folder covers

| Path | Tests | Covers |
|---|---|---|
| `tests/asset/test_asset_model.py` | 44 | Ids, projects, assets, nesting, the registry, publishes, local versions, source control calls, handler dispatch. A temporary projects root, local versions in a temp folder, source control calls recorded |
| `tests/asset/test_asset_animproperties.py` | 16 | The `animproperties` file: defaults, validation messages, read and write |
| `tests/asset/test_maya_asset_handlers.py` | 21 | Each Maya handler on real scenes: shapes, scenes, clips (with ControlAnim, bone map and properties), control poses and animations, sources, the skeleton export, argument checks |
| `tests/asset/test_maya_asset_tools.py` | 51 | The `assettools` functions: variants, build, saves and loads, the questions answered by a `ScriptedPrompter` |
| `tests/asset/test_maya_active_rig.py` | 9 | `get_active_rig` and the tracker |
| `tests/asset/test_maya_rigpanel.py` | 22 | The tracker's `changed` event, the plain pose functions, `RigPanelSession` (groups, following the active rig, selecting, the pose and key commands, a broken rig) and `group_controls` |
| `tests/core/test_maya_rigpanel_view.py` | 9 | The active rig panel's window offscreen over a fake session: the tree, the filter, clicks and ctrl-clicks, every button, a command error, the empty state, the rig picker, reload on change. One test runs it on a real session and rig, and skips without `RIGMODULES_PLUGIN` |
| `tests/core/test_core_layers.py` | 8 | The layer rules, read from the source: `core` imports no Maya, Qt or higher layer, `maya` no `maya_ui` or Qt, no Maya dialog anywhere and no Maya UI command outside `maya_ui`, `maya_ui` imports Maya only in `host.py` and `menus.py`, slots filled only by a `startup.register()`, and the known Python 2 files |
| `tests/core/test_core_tool_registry_edit.py` | 36 | `RegistryEditSession` with no Qt: picking, field and call edits and their events, the status line and an input problem, add and delete, the checked save (the full report, the master registry against its layouts, save as), load, the call picker's module and function lists |
| `tests/core/test_core_slots.py` | 14 | The log writers slot, the prompter slot, `NoPrompter` and `ScriptedPrompter`, `Event`, the progress manager's `changed` |
| `tests/core/test_core_tool_registry.py` | 54 | The registry and layout files: round trip of the repo files, every check (unknown and missing keys, duplicate ids and names, bad ids, dangling and repeated layout references, call checks against fixture modules), versions and `upgrade`, atomic writes, `load_all`, `run_tool` |
| `tests/core/test_maya_batch.py` | 3 | A batch job in its own mayapy, started through `mayalaunch`: the results folder, the log, `root_dir`, `open_report` |
| `tests/core/test_maya_ui_layer.py` | 30 | Both registration passes (batch and GUI), the order of the dev reload hooks, `field_widget`, `DataclassForm` and `SignatureForm`, `QtPrompter` with its dialogs replaced, `FormDialog` refusing an invalid value, `host` (one window per object name, a window that refuses to close, `defer`) |
| `tests/core/test_maya_tool_editors.py` | 29 | Both editors offscreen: the tree and `Layout` round trip, the Registry Editor's widgets bound to its session (list, search, fields, call picker, status line, save, open, delete), `build_menus` with the drawing replaced |
| `tests/rigging/rigmodules_menu/test_maya_rigmodules_menu.py` | 43 | The layout (eight submenus, 38 tools, the dev tools in the bmaya menu), `check_calls` over the repo registry, then each tool run through `run_tool` in Maya, including the joint tools |
| `tests/basic/startup_test/main.py` | 1 | Maya starts through the batch framework and logs |

Not covered: the events registry, the reload half of dev reload, the Qt classes other than the two tool editors, skinning, most joint tools and the generic utilities ([`../docs/status.md`](../docs/status.md#test-coverage) lists proposed tests).

## Writing a test

- A test of anything in `bmaya.core` is plain Python: `bmaya.core.asset` in `tests/asset/test_asset_*.py`, the rest in `tests/core/test_core_*.py`. Add `py/scripts` to `sys.path` as the existing files do. It must not import `maya`.
- A test that needs Maya goes in `test_maya_*.py` in the same folder. Initialize `maya.standalone` once for the class, load the plugin from `RIGMODULES_PLUGIN`, and `skipTest` when either is missing, as `test_maya_rigmodules_menu.py` does.
- File names matter: the batch files discover `test_asset_*.py` and `test_maya_*.py` separately, so a Maya test named `test_asset_*` runs in plain Python and fails.
- Use a temporary directory for every file a test writes, and remove it with `addCleanup`. Point `BMAYA_VERSIONS_DIR` and `RIGGING_PROJECT_DIR` at temporary folders so a test never touches real assets or the machine's version copies.
- Answer a tool's questions with a `bmaya.core.prompts.ScriptedPrompter`, never a mock of a dialog. A function called directly takes it as `prompter=` (`self.answers(...)` in `test_maya_asset_tools.py`), and its `asked` list holds each question, for checking a dialog's starting folder or a confirm's button. A tool run by id through `run_tool` gets its answers through the prompter slot (`with self.answers(...)` in `test_maya_rigmodules_menu.py`, which also fails on unused answers). With no prompter, a question raises `PromptError`, which is how a test shows a tool asks nothing.
- Write expected values by hand, not by recording what the code produced.
- A new menu tool changes the tool count in the layout test, and needs its function tested. `check_calls` already checks that its call resolves.
- A test that registers a slot (the prompter, the log writers, the reload hooks) resets it in a cleanup.
- A test of a Qt window in mayapy creates the `QApplication` **before** `maya.standalone.initialize`, as `test_maya_tool_editors.py` does. Standalone otherwise starts a `QCoreApplication`, and creating a widget aborts the process. Set `QT_QPA_PLATFORM=offscreen`, and make a `QMessageBox` a test failure unless the test expects it.
- A change to a registry or layout format adds an update step and a test with a file of the old version.
