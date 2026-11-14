# Architecture

How the `bmaya` package is organized, how a tool call flows from a menu item to a file on disk, and the recipes for extending it. The reader is someone changing mayadev. For using it, start at the [README](../README.md).

## The two-repo split

mayadev and RigModules are separate repos with one dependency direction: **mayadev depends on RigModules, never the reverse** (D24).

- RigModules owns the rig: module nodes, template, controls, poses, animation data, weight files, and the `python/rigmodules` package that wraps its commands.
- mayadev owns the pipeline around it: where files live, saving and versioning, menus, the active rig, skinning and joint tools, Qt, logging and batch.

The test for where a piece of Python goes (RigModules' `design/mayadev-integration.md`): would it have to change if a RigModules node, attribute, command flag or template key changed? If yes it belongs in RigModules' `python/`. If no it stays here. So mayadev tools reach a rig only through `rigmodules` and its commands, never by walking node connections or parsing names. [`rigmodules.md`](rigmodules.md) lists every call that crosses the line.

## Layers

```
userSetup.py                       startup only: calls into the layers below
  maya_ui/                         Qt windows and the menu builder
  maya/                            tools and handlers: import maya and rigmodules
    assettools   posetools   activerig   devreload   assethandlers
    eventsregistry   batch/   util/   rigging/   modeling/
  asset/                           the file model: no Maya, no rigmodules
  core/                            logger, progress, tool registry, batch base, file utils
```

| Layer | May import | Must not import |
|---|---|---|
| `bmaya.asset` | the standard library, itself | `maya`, `rigmodules`, `bmaya.core`, `bmaya.maya` |
| `bmaya.core` | the standard library, `bmaya.core` | Everything else, with one exception (below) |
| `bmaya.maya` | `maya`, `rigmodules`, `bmaya.asset`, `bmaya.core` | `bmaya.maya_ui` |
| `bmaya.maya_ui` | `PySide6`, `maya`, `bmaya.core`, `bmaya.maya` | |
| `userSetup.py` | any of the above | |

These rules describe the code today, and nothing checks them. The exception is `core/log.py`, which imports `maya.api.OpenMaya` for its handler and `bmaya.maya.constants` for nothing it uses (a `TODO` in the file says to move the handler to a Maya-level module). Because `bmaya.maya.constants` raises without `MAYADEV_ROOT`, importing the logger needs the variable set and a Maya session, so `bmaya.core` is not usable in plain Python yet. `bmaya.asset` is, and the asset tests run that way.

`bmaya.asset` stays Maya-free on purpose: it runs in mayapy, farm jobs and tools outside Maya, and its tests need no Maya. Anything that needs Maya goes in `bmaya.maya`, and the two meet through the handler pattern below.

## Source map

| Path under `py/scripts/bmaya` | Contents |
|---|---|
| `asset/__init__.py` | Exports `Asset`, `AssetError`, `AssetIdError`, `Project`, `ProjectError`, `Registry`, `projects_root` |
| `asset/assetid.py` | Id rules: `is_valid`, `check`, `tokens`, `name`, `key`, `equals`, `to_relative_path`, `from_relative_path`, `SEPARATOR` |
| `asset/project.py` | `Project`, `FileType`, `DEFAULT_PROJECT`, `projects_root`, `read_json`, `write_json` |
| `asset/asset.py` | `Asset`: paths, variants, `create`, `from_path`; the nesting check |
| `asset/registry.py` | `Registry`: the in-memory index of a project |
| `asset/publishes.py` | `make_id`, `list_ids`, `latest`, `info`, `create` |
| `asset/versions.py` | Local version copies: `version`, `list_versions`, `versions_root` |
| `asset/sourcecontrol.py` | `SourceControl` (does nothing), `current`, `set_current` |
| `asset/handlers.py` | `FileHandler`, `register`, `save`, `load` |
| `asset/animproperties.py` | `AnimProperties` and the `<name>.animproperties.json` file |
| `core/log.py` | The `bmaya` logger and its Maya handler |
| `core/progressmanager.py` | `ProgressManager` singleton |
| `core/tool_registry.py` | The tool registry and layout files, Maya-free: the dataclasses (`Tool`, `ToolCall`, `Registry`, `Layout` and its items), the check pass, version updates, atomic read and write, `run_tool` ([`tools.md`](tools.md)) |
| `core/decorators.py` | `decorator_maker`, `log_fn_duration` |
| `core/constants.py` | Naming constants of the older rig builder (see [`status.md`](status.md)) |
| `core/util/` | `version_file` (a `.Versions` folder beside a file), `firstOrDefault` |
| `core/batch/base_batch_framework.py` | `BaseBatchEnvironment`, `BaseBatchPackage` |
| `maya/constants.py` | `MAYADEV_ROOT`, the toolset paths, `MenuSpec` and `MENUS`, `RIGMODULES_PLUGIN`, `IS_BATCH` |
| `maya/assethandlers.py` | The Maya handlers and `register()`, `AnimClip`, `save_control_file`, `save_anim_clip`, `save_skeleton_export` |
| `maya/assettools.py` | The asset, pose, clip and weight tools: plain functions, then the `*_ui` menu entry points |
| `maya/posetools.py` | Zero, mirror, flip and key tools on the selection or the active rig |
| `maya/activerig.py` | `get_active_rig`, `ActiveRigTracker` |
| `maya/devreload.py` | Reload and unload RigModules, reload the menus |
| `maya/eventsregistry.py` | `EventsRegistry`, `EventType`, `pause_callbacks` |
| `maya/batch/` | `MayaBatchEnvironment`, `MayaStandaloneBatchPackage`, `run_batch_test` |
| `maya/rigging/`, `maya/modeling/`, `maya/util/` | Skinning, joint authoring and generic Maya helpers, mostly older code ([`status.md`](status.md)) |
| `maya_ui/qtbase.py` | Window, widget, tree, table, dialog and progress window base classes |
| `maya_ui/tool_registry_editor.py`, `maya_ui/tool_views/tool_menu.py` | The two editors, `ToolMenu` and `build_menus` |
| `maya_ui/namingTool/` | A small naming window |

## A tool call, end to end

Take **Save Control Shapes...** from the RigModules menu.

1. The menu item runs the tool `rigmodules.shapes.save`, whose call is `bmaya.maya.assettools.save_control_shapes_ui()` (`run_tool` imports the module and calls the function, see [`tools.md`](tools.md)).
2. The `*_ui` function gets the active rig from `bmaya.maya.activerig.get_active_rig()` and calls the plain function `save_control_shapes(node)`.
3. That asks RigModules which asset and variant the rig belongs to: `rigmodules.query.get_rig_info(node)`. It does not read node names.
4. It builds an `Asset` from the id and checks the asset folder exists. Without one it falls back to a file dialog and calls `cmds.saveRigControlShapes` directly.
5. With one it calls `bmaya.asset.handlers.save(asset, "shapes", variant, rig_root=...)`.
6. `handlers.save` asks the asset for the path (`asset.path("shapes", variant)`, pure), keeps a local version of the existing file, tells source control to check it out, makes the folder, and hands the path to the registered `RigShapesHandler`.
7. The handler calls `cmds.saveRigControlShapes(rig_root, file=path)`. Source control gets `add` if the file is new.

Every file tool follows this shape: a `*_ui` function for the menu, a plain function with arguments for scripts and batch, an asset lookup, then `handlers.save` or `handlers.load`.

## The file handler pattern

Where a file lives is kept apart from how it is read and written.

- `bmaya.asset` knows paths: `project.json` maps a file type key (`shapes`, `weights`, `rig`) to a path pattern, and `Asset.path(file_type, variant)` fills it in.
- A `FileHandler` knows one format. `bmaya.asset.handlers` keeps a registry of handlers by file type key and never imports one, so the asset layer stays Maya-free.
- `bmaya.maya.assethandlers.register()` registers the Maya handlers once per session. Every tool calls it before `handlers.save` or `handlers.load`, and it is safe to call repeatedly.
- `handlers.save` does the shared work (version copy, source control, folders) so a handler writes only its format. A file type with no handler raises `NotImplementedError`.

[`assets.md`](assets.md) lists each file type and its handler.

## Conventions the code follows

- Plain functions that take arguments, with `*_ui` wrappers that ask with dialogs. Batch jobs call the plain ones.
- Long names in command calls, keyword arguments for flags: `cmds.saveRigControlShapes(rig_root, file=path)`.
- Windows paths go to RigModules commands with forward slashes (`path.replace("\\", "/")`), because a backslash in a command string is an escape.
- Maya's API 2 (`maya.api.OpenMaya`) for new code. Older files use API 1 or mix the two ([`status.md`](status.md)).
- A write is atomic where it matters: JSON goes through a `.tmp` file and `os.replace`, and JSON keys are sorted with one item per line so files diff and merge cleanly under Perforce.
- Errors say what to do next: `"{id} has no asset.json at {folder}. Create it with New Asset first."`

## Recipes

### Add a menu tool

1. Write the function in the module that owns the topic. A tool for the active rig takes its scope from `bmaya.maya.activerig.get_active_rig()`, and a tool that works on controls falls back to the whole rig as `posetools.get_scope` does.
2. If it reads or writes an asset file, write a plain function with arguments, then a `*_ui` wrapper. Don't walk rig nodes to find the asset: use `rigmodules.query`.
3. Add a tool entry to `toolsets/master_tool_registry.json` (a new `id` named `<area>.<topic>.<action>`, a `name`, a `short_name` and a `call` naming the function and any `kwargs`), and put its id in the right submenu of `toolsets/rigmodules_menu.json`. The Registry Editor and the Menu Editor do this without hand-editing JSON, and refuse a save that fails the checks ([`tools.md`](tools.md#checks-and-errors)). A tool is a call into a function and has no code of its own: write the function first.
4. Add a test to `tests/rigging/rigmodules_menu` for the tool, run through `run_tool` by id, and one for the function itself. The layout test there pins the submenu order and the number of tools in the RigModules menu (38), so a new tool changes that count in the same change. `check_calls` runs over the whole registry there and fails when a call's module, function or kwargs don't resolve.
5. Document it in the tool table in [`tools.md`](tools.md) and the README tool areas if it is a new area.

### Add a file type

1. Add its key and path pattern to `DEFAULT_PROJECT["fileTypes"]` in `asset/project.py`. Use `{name}` and `{variant}` only, and give a variant path the form `<folder>/{variant}/...`. Add `"folder": True` if it is a folder. Existing projects keep their own `project.json`, so a new key is not in them until their file is edited.
2. Write the handler (below) if the format is one a tool writes or reads.
3. Update the project and file tables in [`assets.md`](assets.md).

### Add a handler

1. Subclass `bmaya.asset.handlers.FileHandler` in `bmaya/maya/assethandlers.py` and override `save` and `load`. Take what the handler needs as keyword arguments (`rig_root`, `namespace`, `name`), and raise a clear error when one is missing, as `_require_rig_root` does.
2. Register it in `assethandlers.register()` under its file type key.
3. A handler that must save under a name of its own (a pose, a clip) saves through a helper such as `save_control_file`, because `handlers.save` versions the whole path, which for a folder type is the whole folder.
4. Add a test in `tests/asset/test_maya_asset_handlers.py` (needs a RigModules plugin) and a row in the handler table in [`assets.md`](assets.md).

### Cross the boundary

When a tool needs something from a rig that `rigmodules` doesn't offer, the change is in RigModules first: a command or `python/rigmodules` function with its tests and docs, then the call here. Add the new name to the table in [`rigmodules.md`](rigmodules.md) in the same change.
