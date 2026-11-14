# Setup

Environment variables, module files, what happens at startup, and the dev tools that reload RigModules without restarting Maya.

## Environment variables

Set these as user environment variables, or in `documents\maya\2026\Maya.env`. Maya.env only fills in a variable the system doesn't already set, so set each one in one place.

| Variable | Required | Read by | Meaning |
|---|---|---|---|
| `MAYADEV_ROOT` | Yes | `bmaya.maya.constants` | The repo root. Importing `bmaya.maya.constants` raises `EnvironmentError` without it, and so does anything that imports that module (`bmaya.core.log`, so nearly every module). The batch runner and `batch/docgen` read it too |
| `RIGGING_PROJECT_DIR` | For assets | `bmaya.core.asset.project.projects_root` | The folder that holds every game's projects. Asset ids are relative to it. `ProjectError` without it, and the asset tools log a warning and fall back to file dialogs |
| `RIGMODULES_PLUGIN` | No | `bmaya.maya.constants` | The `RigModules.mll` that startup loads. Default: the plugin name `RigModules`, which works only when the plugin is on `MAYA_PLUG_IN_PATH` |
| `BMAYA_VERSIONS_DIR` | No | `bmaya.core.asset.versions` | Where local version copies go. Default: `%LOCALAPPDATA%\bmaya\versions` |
| `MAYA_SKIP_USERSETUP_PY` | Tests | Maya | Set to `1` by the test runners so Maya starts without `userSetup.py` and tests see the plugin alone |

Point `RIGMODULES_PLUGIN` at a copy of the build, not at `cpp\x64\Release\RigModules.mll` itself. A loaded plugin locks its file, so the next RigModules build fails while Maya has the original loaded. The reload tools below copy it for you, but only after the first reload: startup loads the path you gave directly.

Example:

```
RIGGING_PROJECT_DIR=C:\Users\morga\Documents\Art\Maya\rigs
MAYADEV_ROOT=C:\Users\morga\Documents\mayadev
RIGMODULES_PLUGIN=C:\Users\morga\Documents\maya\plug-ins\RigModules.mll
```

`py/scripts/Maya.env` in the repo holds one line, `MAYA_NO_WARNING_FOR_MISSING_DEFAULT_RENDERER=1`, and no paths.

## Module files

Maya reads `.mod` files from `documents\maya\modules`. There are two, one per repo, so either can move or version on its own (D24):

- **`mayadev.mod`** puts `py\scripts` on `PYTHONPATH` and `MAYA_SCRIPT_PATH`, so `bmaya` and `userSetup.py` are found.
- **`RigModules.mod`** puts RigModules' `python` folder on `PYTHONPATH`, so `rigmodules` is found. Copy it from the RigModules repo root and replace its `.` with the repo's full path (RigModules' `docs/python.md` has the steps). It does not add the plugin path.

Neither file is in this repo today. An example `mayadev.mod` in Maya's module syntax, not checked against a Maya install:

```
+ mayadev 1.0 C:\Users\morga\Documents\mayadev
PYTHONPATH+:=py/scripts
MAYA_SCRIPT_PATH+:=py/scripts
```

`py/easyInstall.py` and `py/dragIntoMaya.mel` are an older install route. They write a `bm.mod` that points at a scripts folder you browse to, and know nothing about `RigModules`, `MAYADEV_ROOT` or the other variables above. Use the module files.

## Startup

`py/scripts/userSetup.py` defers everything, so Maya's own startup finishes first. The order, from `_run_deferred_setup`:

| Step | Does | Skipped in batch |
|---|---|---|
| (`user_setup`) | Sets `scriptEditorInfo` to write history to `~\Documents\maya\logs\maya_logs_<timestamp>.txt` | Yes |
| 1 | The registration passes ([`architecture.md`](architecture.md#the-registration-pass)): `bmaya.maya.startup.register()` sends the log to Maya's Script Editor in a GUI session, and `bmaya.maya_ui.startup.register()` installs the Qt prompter and the dev reload's menu hooks | The UI pass. A batch session logs to stdout |
| 2 | `bmaya.core.log.init_logger()` | |
| 3 | Starts the progress manager, and opens the progress window, kept in `_progress_window` | The window |
| 4 | `_load_rigmodules`: `cmds.loadPlugin(RIGMODULES_PLUGIN)`. On `RuntimeError` it logs a warning and carries on without the plugin | |
| 5 | `_setup_tool_menus`: `build_menus()` reads `toolsets/master_tool_registry.json` and every layout, checks them, and builds the **bmaya tool menu** (`bmaya_menu`) and, while the plugin is loaded, the **RigModules** menu (`rigmodules_menu`). A missing or invalid file is logged with every problem (`log.error`) and the menus are skipped, so steps 4 and 6 still run ([`tools.md`](tools.md#checks-and-errors)) | Yes |
| 6 | `_start_active_rig_tracker`: only when the plugin loaded | Yes |

The plugin loads before the menus because the RigModules menu is built only while it is loaded. The tracker needs the plugin because it asks `rigmodules.query` which rig a node belongs to.

A batch session logs to stdout, which the batch framework captures ([`framework.md`](framework.md#logger)). With no prompter registered, a menu tool run in batch raises on its first question instead of waiting on a dialog.

## Dev reload

The **dev** submenu of the bmaya tool menu swaps a new RigModules build in without restarting Maya (`bmaya.maya.devreload`, and `bmaya.maya_ui.tool_views.tool_menu.reload_menus` for Reload Menu). It is in the bmaya menu, which has no plugin, so it is still there after an unload. All three run deferred, so a menu item can start them: the menus are rebuilt while the item's own callback would still be on the stack otherwise.

| Tool | Does | Scene |
|---|---|---|
| Reload RigModules (dev) | Tears down, then loads a copy of `RIGMODULES_PLUGIN` from `%TEMP%\rigmodules_dev\<timestamp>`, and puts the tracker and the menus back (`build_menus()`) | Thrown away |
| Unload RigModules (dev) | Tears down and leaves Maya without the plugin, so the build is unlocked for a rebuild. The RigModules menu goes with the plugin, and Reload, in the bmaya menu, brings it back | Thrown away |
| Reload Menu (dev) | `build_menus()`: reads the layout and registry files again and rebuilds both menus, so edits to them show. A broken file is reported and the current menus stay | Untouched |

`devreload` doesn't import the menus: the UI's registration pass gives it two hooks, delete the menus that need the plugin before an unload and `build_menus()` after a load. Without them (mayapy) nothing runs there.

Tear down is: stop the active rig tracker, delete the menus that need the plugin (the first hook), clear the selection, `file -new`, flush undo (undo entries keep C++ node references alive), refresh (VP2 caches render items for the control nodes), unload the plugin. Reload and Unload also drop every `rigmodules` module from `sys.modules`, so the next import reads the package again. Reload needs `RIGMODULES_PLUGIN` to be a path to the `.mll` and raises `RuntimeError` when it isn't. These are development tools only.
