# Architecture

How the `bmaya` package is organized, how a tool call flows from a menu item to a file on disk, and the recipes for extending it. The reader is someone changing mayadev. For using it, start at the [README](../README.md).

## The two-repo split

mayadev and RigModules are separate repos with one dependency direction: **mayadev depends on RigModules, never the reverse** (D24).

- RigModules owns the rig: module nodes, template, controls, poses, animation data, weight files, and the `python/rigmodules` package that wraps its commands.
- mayadev owns the pipeline around it: where files live, saving and versioning, menus, the active rig, skinning and joint tools, Qt, logging and batch.

The test for where a piece of Python goes (RigModules' `design/mayadev-integration.md`): would it have to change if a RigModules node, attribute, command flag or template key changed? If yes it belongs in RigModules' `python/`. If no it stays here. So mayadev tools reach a rig only through `rigmodules` and its commands, never by walking node connections or parsing names. [`rigmodules.md`](rigmodules.md) lists every call that crosses the line.

## Layers

```
userSetup.py                       startup only: the registration passes, then the menus and the active rig
  maya_ui/                         Qt: windows, the Qt prompter, form widgets, the menu builder
  maya/                            tools and handlers: import maya and rigmodules
    assettools   posetools   activerig   librarybrowser   devreload   assethandlers   startup
    eventsregistry   batch/   util/   rigging/   modeling/
  core/                            plain Python: logger, progress, prompts, Event, tool registry, batch base
    asset/                         the file model: no Maya, no rigmodules
```

| Layer | May import | Must not import |
|---|---|---|
| `bmaya.core` (with `bmaya.core.asset`) | the standard library, `bmaya.core` | `maya`, `rigmodules`, `bmaya.maya`, `bmaya.maya_ui`, PySide6 |
| `bmaya.maya` | `maya`, `rigmodules`, `bmaya.core` | `bmaya.maya_ui`, PySide6 |
| `bmaya.maya_ui` | `PySide6`, `maya`, `bmaya.core`, `bmaya.maya` | |
| `userSetup.py` | any of the above | |

Dependencies run `core` > `maya` > `maya_ui`, never the other way. Maya's dialog commands (`promptDialog`, `confirmDialog`, `layoutDialog`, `fileDialog2`) are used nowhere: dialogs are Qt. Maya's other UI commands (`cmds.menu`, `cmds.workspaceControl`) are used only in `maya_ui`. `tests/core/test_core_layers.py` checks all of this by reading the source (RigModules D49).

`bmaya.core` is plain Python: it runs in mayapy, farm jobs and tools outside Maya, and its tests need no Maya. Anything that needs Maya goes in `bmaya.maya`. The two meet in two ways: the file handler pattern and the registration pass, both below.

## The registration pass

When `core` needs something only a higher layer can give (where log text goes, how to ask the user, what runs around a plugin reload), `core` doesn't import it. It declares a **slot**: the interface and a default that works with nothing registered. At startup each higher layer runs one registration pass that fills the slots it can.

```python
# bmaya/maya/startup.py
def register() -> None:
    if cmds.about(batch=True):
        bmaya.core.log.reset_writers()      # batch: stdout, which the batch framework captures
        return
    bmaya.core.log.register_writers({logging.INFO: om.MGlobal.displayInfo, ...})
```

`userSetup.py` calls `bmaya.maya.startup.register()`, then `bmaya.maya_ui.startup.register()` when Maya isn't in batch. Plain Python and tests call neither and get the defaults.

| Slot | Owner | Default | Filled by |
|---|---|---|---|
| Log writers by level | `bmaya.core.log.LogOutput.writers` (`register_writers`, `reset_writers`) | stdout | `bmaya.maya.startup`: `MGlobal.displayInfo`, `displayWarning`, `displayError`, in a GUI session |
| The prompter | `bmaya.core.prompts` (`register_prompter`, `reset_prompter`, `current`) | `NoPrompter`: raises naming the question | `bmaya.maya_ui.startup`: `QtPrompter` |
| Reload hooks | `bmaya.maya.devreload` (`register_hooks`, `reset_hooks`) | nothing runs | `bmaya.maya_ui.startup`: delete the plugin menus before an unload, build the menus after a load |

Rules for a slot:

- The owner defines its type and a default that works with nothing registered. A missing GUI service fails loudly (`NoPrompter`), never silently.
- It's read when used, never copied at import, so a module imported earlier, or reloaded, sees the current value.
- Only a `startup.register()` fills it. A test pins that, so every link from a lower layer to a higher one is in `maya/startup.py` or `maya_ui/startup.py`. Tests may register their own and reset it in a cleanup.
- `register()` replaces what it registered before, so calling it again is safe.

The file handlers in `bmaya.core.asset.handlers` work the same way, with one difference: every tool calls `bmaya.maya.assethandlers.register()` itself, so a mayapy job that never ran startup still has them (below).

**A slot or an `Event`:** a slot holds one implementation per session. `bmaya.core.observable.Event` is for many listeners that come and go, such as views watching a view-model: `ProgressManager.changed` is one, and the progress window listens to it.

## Questions a tool asks

A menu tool asks the user through a `bmaya.core.prompts.Prompter`: `ask_text`, `choose`, `confirm`, `ask_file`, `ask_folder` and `ask_form` (a dataclass instance, edited in a form built from its fields' type hints). The tool takes `prompter=None` and asks `bmaya.core.prompts.current()` when none is passed:

```python
def save_pose_interactive(prompter: bmaya.core.prompts.Prompter | None = None) -> str | None:
    prompter = _prompter(prompter)              # the one passed in, else the session's
    ...
    name = prompter.ask_text("Save Pose", "Pose name, saved in ...:")
```

| Prompter | Where | Use |
|---|---|---|
| `QtPrompter` | `bmaya.maya_ui.prompter` | A GUI session: Qt dialogs (`QInputDialog`, `QMessageBox`, `QFileDialog`, a `FormDialog`) on Maya's main window |
| `ScriptedPrompter(answers)` | `bmaya.core.prompts` | Tests and batch jobs: answers in order, records each question in `asked`, raises on a question past the last answer |
| `NoPrompter` | `bmaya.core.prompts` | The default: raises `PromptError` naming the question, so a headless run never waits on a dialog |

None of the code that asks imports a UI, so every tool runs in mayapy with a `ScriptedPrompter`, and its plain function runs with no prompter at all.

## Source map

| Path under `py/scripts/bmaya` | Contents |
|---|---|
| `core/asset/__init__.py` | Exports `Asset`, `AssetError`, `AssetIdError`, `Project`, `ProjectError`, `Registry`, `projects_root` |
| `core/asset/assetid.py` | Id rules: `is_valid`, `check`, `tokens`, `name`, `key`, `equals`, `to_relative_path`, `from_relative_path`, `SEPARATOR` |
| `core/asset/project.py` | `Project`, `FileType`, `DEFAULT_PROJECT`, `projects_root`, `read_json`, `write_json` |
| `core/asset/asset.py` | `Asset`: paths by owner, `skeletons`, `rigs`, `looks`, `rig`, `look`, `skeleton_of`, `add_rig`, `add_look`, `create`, `from_path`; the nesting check |
| `core/asset/textures.py` | `textures.json`, a look's texture sidecar: `TextureMap`, `Material`, `MeshEntry`, the slots of each shader, `read`, `write`, `check` |
| `core/asset/records.py` | `rig.json` and `look.json`: `SkeletonRef`, `RigRef`, `RigRecord`, `LookRecord` and their readers and writers |
| `core/asset/registry.py` | `Registry`: the in-memory index of a project |
| `core/asset/context.py` | `AssetContext`: the asset id and the chosen skeleton, rig and look the Asset Editor works on, with a `changed` event. `current()` is `None` unless the editor is open |
| `core/shapemath.py` | `decompose` and `compose`: a control's `shapeTransform` (16 numbers, row vector convention) as translate, rotate in degrees (XYZ) and scale, with a negative X scale for a reflection |
| `core/fieldset.py` | `FieldSpec`, `FieldState` and `combine`: fields edited across a selection, and a field's one value or "mixed" over it. The Asset Editor's markup and shape tabs share it |
| `core/asset/catalog.py` | `project_folders` and `asset_ids`: every project and asset below the projects root, for the Asset Editor's list |
| `core/asset/publishes.py` | `make_id`, `list_ids`, `latest`, `info`, `create` |
| `core/asset/versions.py` | Local version copies: `version`, `version_if_changed`, `list_versions`, `find_version`, `restore`, `versions_root` |
| `core/asset/sourcecontrol.py` | `SourceControl` (does nothing), `current`, `set_current` |
| `core/asset/handlers.py` | `FileHandler`, `register`, `save`, `load` |
| `core/asset/library.py` | The pose and animation library on disk, no Maya: sources (Approved, Shared, User), listing, `Index`, search, masks, rename and delete ([`assets.md`](assets.md#library)) |
| `core/asset/animproperties.py` | `AnimProperties` and the `<name>.animproperties.json` file |
| `core/log.py` | The `bmaya` logger, `LogOutput` and its writers slot |
| `core/observable.py` | `Event`: change notification without Qt |
| `core/prompts.py` | `Prompter`, `NoPrompter`, `ScriptedPrompter`, `Question`, `PromptError`, the prompter slot |
| `core/progressmanager.py` | `ProgressManager` singleton, with its `changed` `Event` |
| `core/tool_registry.py` | The tool registry and layout files, Maya-free: the dataclasses (`Tool`, `ToolCall`, `Registry`, `Layout` and its items), the check pass, version updates, atomic read and write, `run_tool` ([`tools.md`](tools.md)) |
| `core/tool_registry_edit.py` | `RegistryEditSession`: the Registry Editor's state and commands with no Qt (picked tool, edits, unsaved flag, status, checked save), and the call picker's `list_modules`, `list_functions` and `import_module` ([`tools.md`](tools.md#editors)) |
| `core/decorators.py` | `decorator_maker`, `log_fn_duration` |
| `core/constants.py` | Naming constants of the older rig builder (see [`status.md`](status.md)) |
| `core/util/` | `version_file` (a `.Versions` folder beside a file), `firstOrDefault` |
| `core/batch/base_batch_framework.py` | `BaseBatchEnvironment`, `BaseBatchPackage` |
| `maya/startup.py` | `register()`: the Maya layer's registration pass |
| `maya/constants.py` | `MAYADEV_ROOT`, the toolset paths, `MenuSpec`, `MENUS` and `menu_layout_paths`, `RIGMODULES_PLUGIN`, `IS_BATCH` |
| `maya/assethandlers.py` | The Maya handlers (`RigSkeletonHandler`, `ModelHandler` with `export_meshes`) and `register()`, `AnimClip`, `save_control_file`, `save_anim_clip`, `save_skeleton_export` |
| `maya/assettextures.py` | Reads a rig scene's standardSurface shading into a `TextureMap` and builds it again from one: `read_scene`, `save_file`, `apply`, `remove_materials` |
| `maya/assettools.py` | The asset, pose, clip and weight tools: plain functions, then the `*_interactive` menu entry points, which ask through a `Prompter`, and `ClipSettings` |
| `maya/posetools.py` | Zero, mirror, flip, key, load pose and load animation tools on the selection or the active rig: plain functions with a scope, and the `*_interactive` entry points |
| `maya/activerig.py` | `get_active_rig`, `ActiveRigTracker` and its `changed` event |
| `maya/librarybrowser.py` | `LibrarySession`, the library browser's view-model with no Qt: the listing that follows the active rig, search, scope, apply, save, tags, rename, delete and masks, and what the window can't compute itself: `facets` (the values in use), `name_taken`, `current_frame`, `playback_range`, `mask_from_selection`, and the project's vocabulary warnings in `details`. `read_file_infos` is its `Index` reader, `rig_masks` its masks from a rig |
| `maya/asseteditor.py` | `AssetEditorSession`, the Asset Editor's view-model with no Qt: the asset context, the callbacks that keep it current (all removed by `close()`), and the create, switch and refresh commands |
| `maya/shapemodel.py` | `ShapeModel`, the Asset Editor's Shapes tab view-model with no Qt: the selected rig controls' shape fields as one value or mixed, Set and Adjust edits across all of them with `setAttr` (one undo step each), and mirroring the shapes of their rigs |
| `maya/markupmodel.py` | `MarkupModel`, the Asset Editor's Markup tab view-model with no Qt: the selected joints' markup as mixed fields, edits across all of them (set, add, remove, one undo step each, side and usage kept unique per skeleton), and the selected rig controls' markup, read only |
| `maya/namingmodel.py` | `NamingModel`, the Asset Editor's Naming tab view-model with no Qt: the selection's name root, side and start number (filled from its first node that is in the convention), renaming it in selection order (joints, controls, modules, constraints and meshes) and mirroring Left and Right names, all through RigModules' `renameRigNodes` |
| `maya/assetfiles.py` | `AssetFilesModel`, `FileRow`, `RowTool` and the `FileAction` table: one row per file of the chosen asset, with its status, Save, Load, its scene tools (the Markers row's Add Foot Markers) and Build Rig |
| `maya/rigpanel.py` | `RigPanelSession`, `ControlGroup`, `SpaceState` and `LimbState`: the active rig panel's view-model, no Qt |
| `maya/devreload.py` | Reload and unload RigModules, and the reload hooks slot |
| `maya/eventsregistry.py` | `EventsRegistry`, `EventType`, `pause_callbacks` |
| `maya/batch/` | `MayaBatchEnvironment`, `MayaStandaloneBatchPackage`, `run_batch_test` |
| `maya/rigging/`, `maya/modeling/`, `maya/util/` | Skinning, joint authoring and generic Maya helpers, mostly older code ([`status.md`](status.md)) |
| `maya_ui/startup.py` | `register()`: the UI layer's registration pass |
| `maya_ui/prompter.py` | `QtPrompter`, `FormDialog` |
| `maya_ui/host.py` | Maya as the host of a window: `parent_window`, `show` (one window per object name, optionally docked), `dock_control_name`, `defer`. With `menus.py`, the only file in `maya_ui` that imports Maya |
| `maya_ui/rigpanel.py` | `RigPanel`, the active rig panel's window over a `RigPanelSession`, and `show_window` (docked) |
| `maya_ui/asseteditor.py` | `AssetEditor`, the Asset Editor's window over an `AssetEditorSession`, and `show_window` (docked) |
| `maya_ui/assetwidgets.py` | `AssetPicker`, `OwnerCombo`, `FileStatusTable` and `MixedFieldForm`: the Asset Editor's reusable widgets, over plain lists and `FieldSpec`s |
| `maya_ui/librarybrowser.py` | `LibraryBrowser`, the library browser's window over a `LibrarySession` (one `QTableView` as List or Details, search, filter menu, scope and apply, save, context menu), `EditMetaDialog`, and `show_window` (docked) |
| `maya_ui/menus.py` | The Maya menus (`ToolMenu`, `build_menus`, `delete_plugin_menus`, `reload_menus`) and the Menu Editor |
| `maya_ui/widgets.py` | `field_widget`, `show_value` and `read_value` (an editor chosen by a type hint), `DataclassForm`, `SignatureForm`, `ListModel` (a Qt item model over a list), `TagsEdit` (a line of comma-separated tags that completes the one being typed) |
| `maya_ui/qtbase.py` | Window, widget, tree, dialog and progress window base classes |
| `maya_ui/tool_registry_editor.py` | The Registry Editor window, widgets over a `RegistryEditSession` |
| `maya_ui/namingTool/` | A small naming window |

## A tool call, end to end

Take **Save Control Shapes...** from the RigModules menu.

1. The menu item runs the tool `rigmodules.shapes.save`, whose call is `bmaya.maya.assettools.save_control_shapes_interactive()` (`run_tool` imports the module and calls the function, see [`tools.md`](tools.md)).
2. The `*_interactive` function gets the active rig from `bmaya.maya.activerig.get_active_rig()` and calls the plain function `save_control_shapes(node, prompter=...)`.
3. That asks RigModules which asset and rig the rig belongs to: `rigmodules.query.get_rig_info(node)`. It does not read node names.
4. It builds an `Asset` from the id and checks the asset folder exists. Without one it asks the prompter for a file and calls `cmds.saveRigControlShapes` directly.
5. With one it calls `bmaya.core.asset.handlers.save(asset, "shapes", rig, rig_root=...)`.
6. `handlers.save` asks the asset for the path (`asset.path("shapes", rig)`, pure), keeps a local version of the existing file, tells source control to check it out, makes the folder, and hands the path to the registered `RigShapesHandler`.
7. The handler calls `cmds.saveRigControlShapes(rig_root, file=path)`. Source control gets `add` if the file is new.

Every file tool follows this shape: a `*_interactive` function for the menu, a plain function with arguments for scripts and batch, an asset lookup, then `handlers.save` or `handlers.load`.

## The file handler pattern

Where a file lives is kept apart from how it is read and written.

- `bmaya.core.asset` knows paths: `project.json` maps a file type key (`shapes`, `weights`, `rig`) to a path pattern, and `Asset.path(file_type, owner)` fills it in.
- A `FileHandler` knows one format. `bmaya.core.asset.handlers` keeps a registry of handlers by file type key and never imports one, so the asset layer stays Maya-free.
- `bmaya.maya.assethandlers.register()` registers the Maya handlers once per session. Every tool calls it before `handlers.save` or `handlers.load`, and it is safe to call repeatedly.
- `handlers.save` does the shared work (version copy, source control, folders) so a handler writes only its format. A file type with no handler raises `NotImplementedError`.

[`assets.md`](assets.md) lists each file type and its handler.

## Conventions the code follows

- Plain functions that take arguments, with `*_interactive` entry points that take their scope from the session (the active rig, the selection, the playback range) and ask for the rest through a `Prompter`. Batch jobs call the plain ones. No `bmaya.maya` code opens a dialog.
- Long names in command calls, keyword arguments for flags: `cmds.saveRigControlShapes(rig_root, file=path)`.
- Windows paths go to RigModules commands with forward slashes (`path.replace("\\", "/")`), because a backslash in a command string is an escape.
- Maya's API 2 (`maya.api.OpenMaya`) for new code. Older files use API 1 or mix the two ([`status.md`](status.md)).
- A write is atomic where it matters: JSON goes through a `.tmp` file and `os.replace`, and JSON keys are sorted with one item per line so files diff and merge cleanly under Perforce.
- Errors say what to do next: `"{id} has no asset.json at {folder}. Create it with New Asset first."`

## Recipes

### Add a menu tool

1. Write the function in the module that owns the topic. A tool for the active rig takes its scope from `bmaya.maya.activerig.get_active_rig()`, and a tool that works on controls falls back to the whole rig as `posetools.get_scope` does.
2. If it reads or writes an asset file, write a plain function with arguments, then a `*_interactive` entry point that takes `prompter=None` and asks for anything else through `prompter.ask_*`. Don't walk rig nodes to find the asset: use `rigmodules.query`.
3. Add a tool entry to `toolsets/master_tool_registry.json` (a new `id` named `<area>.<topic>.<action>`, a `name`, a `short_name` and a `call` naming the function and any `kwargs`), and put its id in the right submenu of `toolsets/rigmodules_menu.json`. The Registry Editor and the Menu Editor do this without hand-editing JSON, and refuse a save that fails the checks ([`tools.md`](tools.md#checks-and-errors)). A tool is a call into a function and has no code of its own: write the function first.
4. Add a test to `tests/rigging/rigmodules_menu` for the tool, run through `run_tool` by id with its answers in `self.answers(...)`, and one for the function itself with a `ScriptedPrompter`. The layout test there pins the submenu order and the number of tools in the RigModules menu (38), so a new tool changes that count in the same change. `check_calls` runs over the whole registry there and fails when a call's module, function or kwargs don't resolve.
5. Document it in the tool table in [`tools.md`](tools.md) and the README tool areas if it is a new area.

### Add a file type

1. Add its key and path pattern to `DEFAULT_PROJECT["fileTypes"]` in `core/asset/project.py`. Use `{name}` and at most one owner, `{skeleton}`, `{rig}` or `{look}`, and give an owned path the form `<folder>/{owner}/...`. Add `"folder": True` if it is a folder. Existing projects need a step in `PROJECT_UPDATES` that adds the key, with `FORMAT_VERSION` bumped, so their `project.json` picks it up on the next load ([`assets.md`](assets.md#projectjson)).
2. Write the handler (below) if the format is one a tool writes or reads.
3. Update the project and file tables in [`assets.md`](assets.md).

### Add a handler

1. Subclass `bmaya.core.asset.handlers.FileHandler` in `bmaya/maya/assethandlers.py` and override `save` and `load`. Take what the handler needs as keyword arguments (`rig_root`, `namespace`, `name`), and raise a clear error when one is missing, as `_require_rig_root` does.
2. Register it in `assethandlers.register()` under its file type key.
3. A handler that must save under a name of its own (a pose, a clip) saves through a helper such as `save_control_file`, because `handlers.save` versions the whole path, which for a folder type is the whole folder.
4. Add a test in `tests/asset/test_maya_asset_handlers.py` (needs a RigModules plugin) and a row in the handler table in [`assets.md`](assets.md).

### Cross the boundary

When a tool needs something from a rig that `rigmodules` doesn't offer, the change is in RigModules first: a command or `python/rigmodules` function with its tests and docs, then the call here. Add the new name to the table in [`rigmodules.md`](rigmodules.md) in the same change.

### Add a slot

When `core` (or `maya`) needs something a higher layer provides, add a slot rather than an import.

1. In the owning module, define the interface (a `Callable` or a `typing.Protocol`), a default that works with nothing registered, a `register_*` function that replaces the value and a `reset_*` function that restores the default. Read the slot where it's used.
2. Fill it in the higher layer's `startup.register()`, and nowhere else. Add the `register_*` name to `SLOT_REGISTRATIONS` in `tests/core/test_core_layers.py`.
3. Test the default in plain Python (`tests/core/test_core_slots.py`), and the registration in mayapy (`tests/core/test_maya_ui_layer.py`).
4. Add it to the slot table in [The registration pass](#the-registration-pass).
