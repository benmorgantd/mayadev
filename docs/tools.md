# Tools and menus

How a tool is defined, how the two menus are built from it, what every RigModules menu tool does, and the active rig that most of them act on.

## Tool registry and menu layout

A tool is data, not a menu item: an id, labels and **one function call**. Two kinds of JSON file under `toolsets/` describe the menus, and both carry a `version` (now 2):

| File | Holds |
|---|---|
| `master_tool_registry.json` | Every tool. The source of truth |
| `bmaya_menu.json`, `rigmodules_menu.json` | A menu layout: which tools, in which submenus, in what order |

A tool can be in any number of layouts, or none. A menu item holds a call and no code, and the call is the same function a script or batch job uses.

### Registry entry

```json
{
    "version": 2,
    "tools": [
        {
            "id": "rigmodules.pose.mirror_left_to_right",
            "name": "Mirror Pose Left to Right",
            "short_name": "Pose L>R",
            "call": {
                "module": "bmaya.maya.posetools",
                "function": "mirror_pose_interactive",
                "kwargs": { "left_to_right": true }
            },
            "icon": null,
            "enabled": true
        }
    ]
}
```

| Key | Meaning |
|---|---|
| `id` | Identity, and how layouts (and a planned shelf) refer to a tool. Public, like a RigModules control name: renaming one breaks every layout that uses it |
| `name` | The menu label |
| `short_name` | The shelf label, kept for a planned shelf view. Required |
| `call.module`, `call.function` | The function the tool runs, by import path |
| `call.kwargs` | Keyword arguments, JSON values only (bool, number, string, null, lists and objects of those). An omitted argument takes the function's default. No positional arguments, so a reordered signature can't change what a tool does. Optional when reading, and `{}` is written |
| `icon` | Optional image path for the menu item |
| `enabled` | `false` greys the item out wherever it appears |

Every key is written on every save. `icon` and `enabled` may be left out when reading.

**Ids** are dot-separated lowercase segments (`^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$`), named `<area>.<topic>.<action>` by topic and not by menu position: `rigmodules.pose.flip`, `rigmodules.clip.capture_joint_clip`, `bmaya.joints.orient_to_world`, `bmaya.dev.reload_menu`. Within the registry an `id` and a `name` (compared case-insensitively) are unique. `short_name` is not checked until the shelf view exists. A rename is a hand edit of the registry and every layout, and the check below catches anything missed.

### Menu layout

```json
{
    "version": 2,
    "label": "RigModules",
    "items": [
        {
            "type": "submenu",
            "label": "pose",
            "items": [
                { "type": "tool", "tool": "rigmodules.pose.mirror_left_to_right", "enabled": true },
                { "type": "separator" }
            ]
        }
    ]
}
```

| Item `type` | Keys | Builds |
|---|---|---|
| `tool` | `tool` (a registry id), `enabled` (default `true`) | A menu item. Enabled only when both the tool's and the layout's `enabled` are true |
| `submenu` | `label`, `items` | A tear-off submenu. Sibling submenus have different labels |
| `separator` | | A divider |

A tool appears at most once in a layout, and every `tool` names an id in the registry.

### Checks and errors

Every file is checked before anything is built from it, and the check reports **every** problem, not the first. A problem names where it is:

```
toolsets/master_tool_registry.json: 2 problems
  tools[5] (bmaya.joints.orient_to_world): unknown key 'enabeld'
  tools[9]: id 'rigmodules.pose.flip' is already used by tools[4]
toolsets/rigmodules_menu.json: 1 problem
  items[6].items[2]: tool 'rigmodules.pose.flipp' is not in the registry
```

| Check | Covers | Runs |
|---|---|---|
| Structure (`check_registry`, `check_layout`) | Required and unknown keys, types, item types, the id format, every uniqueness rule above, layout references | On every read and before every write, so startup, Reload Menu and every Save run it |
| Calls (`check_calls`) | The module imports, the function exists, `kwargs` bind to its signature, required arguments are given, and each value fits a simple annotation (`bool`, `int`, `float`, `str`, `None`, unions and `Literal` of those) | The Registry Editor's Save, and the test suite. Not at startup, because it imports every tool module |

A missing file raises `FileNotFoundError` naming the path. A file that isn't JSON, or has a version it can't read, reports that one problem. A file without `version` is version 1, which is no longer read. A version newer than the code raises "written by a newer mayadev".

### Versions

Each format has its own version (`REGISTRY_VERSION`, `LAYOUT_VERSION`) and an update table (`REGISTRY_UPDATES`, `LAYOUT_UPDATES`), the Python form of RigModules' `FormatUpdate`. Reading runs the update steps from the file's version to the current one on the raw JSON, then the structure check, which sees only the current format. Saving always writes the current version, so updating a file on disk is open and save. A step works on raw JSON alone (it reads no other file and imports no tool module) and uses `.get`, because it runs before the check. The tables are empty at version 2, and the next format change adds the first step and a test with a file of the old version. There is no version per tool: a tool's contents are content, and only the shape of the file is versioned.

### Code

`bmaya.core.tool_registry` is plain Python, with no Maya import:

| Name | Is |
|---|---|
| `Tool`, `ToolCall`, `Registry` | Dataclasses. `Registry.tools` maps id to `Tool`, in file order |
| `Layout`, `ToolItem`, `Separator`, `Submenu` | Dataclasses. `Layout.tool_items()` yields every tool item, depth first |
| `read_registry(path)`, `read_layout(path, tool_ids)` | Read, update, check and build. Each returns a **new** object, so opening a file never merges into one already loaded |
| `write_registry(registry, path)`, `write_layout(layout, path, tool_ids)` | Check, then write a `.tmp` file in the same folder, flush, `os.fsync` and `os.replace` over the original. An invalid file is never written, and a failed write leaves the original. UTF-8, with `ensure_ascii=False` |
| `load_all(registry_path, layout_paths)` | Reads the registry and every layout and raises one `ToolDataError` for all the broken files |
| `check_registry`, `check_layout`, `check_calls`, `check_call` | The checks. They return `Issue(where, message)` lists (`check_call`, one tool's messages) |
| `resolve_call(call)`, `run_tool(tool)` | Import the module **on each run** and call `function(**kwargs)`. A missing module or function raises `ToolError("Tool <id>: no function '<name>' in <module>")`. An exception from the function is raised unchanged, with its own traceback. Nothing calls `exec` |
| `upgrade(data, current, updates)` | Runs update steps |

`bmaya.maya_ui.tool_views.tool_menu` draws the menus: `ToolMenu(menu_id, layout, registry).build_ui()` deletes any menu with that id and builds it on Maya's main menu bar, and `build_menus()` does it for every menu in `bmaya.maya.constants.MENUS`:

| `MenuSpec` | Maya menu id | Layout | Plugin |
|---|---|---|---|
| bmaya tool menu | `bmaya_menu` | `bmaya_menu.json` | none: always built |
| RigModules menu | `rigmodules_menu` | `rigmodules_menu.json` | `RigModules`: built only while it is loaded |

`build_menus()` reads the registry and **every** layout and checks them all before it touches a menu, so a bad edit leaves the current menus in place, and one reload shows every broken file. The layout of a menu whose plugin isn't loaded is still checked. A menu item's command is `run_tool(tool)`, so each click imports its module and a module that fails to import breaks only its own items.

### Editors

Both are Qt windows opened from the **bmaya tool menu**.

**Tool Registry Editor** (`bmaya.maya_ui.tool_registry_editor.show_window`): create, edit, run and delete tools.

| Part | Does |
|---|---|
| New Tool | Asks for the id, checked as you type, and the name. `short_name` starts as the name, and the call starts empty. The id is read-only afterwards |
| Module | A text field with a completer over every module under `bmaya` and `rigmodules`, found by reading the folders (nothing is imported). Any import path can be typed |
| Function | A drop-down filled when the module imports: the public functions defined in that module, with the first docstring line shown under it |
| Arguments | A form built from the function's signature: a widget chosen by annotation (check box for `bool`, spin box for `int` and `float`, text for `str`, drop-down for `Literal` and `Enum`, JSON text for anything else) and a **Set** check box. An unset row shows the default greyed and is **not saved**, so `kwargs` holds only what was chosen. A parameter with no default is always set. A saved kwarg the function no longer has shows as a red row with a Remove button |
| Status | `OK`, or the first problem of the tool's call. Run is enabled only on `OK`, and runs the tool as edited |
| Open Registry | Replaces the loaded registry with the file's, and asks first when there are unsaved edits. A file that fails its check is refused with the full report |
| Save Registry | Runs the structure check and the calls check on the whole registry, and, for the master registry, every menu layout against it. Deleting a tool a layout still uses is an error that names the layout. A refused save shows the full report and writes nothing |

**Tool Menu Editor** (`bmaya.maya_ui.tool_views.tool_menu.show_window`): arrange registry tools into submenus, separators and order.

- A tool row has a check box, and the check box is the item's `enabled`. Its tooltip is the tool id.
- Open Menu Layout uses `read_layout`, so a bad file is refused with its report and the tree is left as it was. Save uses `write_layout`, which checks against the loaded registry.

Saving in an editor and then running **Reload Menu (dev)** shows the change without restarting Maya.

## Menus

### bmaya tool menu

| Submenu | Tool | Does |
|---|---|---|
| (top level) | Tool Registry Editor, Tool Menu Editor | The two editors above |
| Joints | Create Joint at Center | `joint.create_joint_at_selection_center()` |
| Joints | Zero Transforms | `joint.zero_transforms_interactive`: `cmds.makeIdentity` on the selection (translate, rotate, scale) |
| Joints | Orient to World, Orient to Mesh | `joint.orient_to_world_interactive` on the selected joints, and `joint.orient_to_mesh_interactive` (the last selection is the mesh) |
| dev | Reload RigModules (dev), Unload RigModules (dev), Reload Menu (dev) | See [`setup.md`](setup.md#dev-reload). They are in this menu, which has no plugin, so they stay reachable after an unload |

### RigModules menu

Built only while the plugin is loaded (`MenuSpec.plugin` in `bmaya.maya.constants.MENUS`), and deleted when it unloads. It is a set of submenus, in this order: asset, mesh, joints, weights, shapes, control, pose, clip. A new tool goes in the submenu for its topic, and only a tool animators use constantly goes at the top level. Dialogs are small, and errors report in the Script Editor.

Most tools act on the **active rig**, so nobody selects a rig root ([below](#the-active-rig)). The tools that ask for an asset id fill it in with the active rig's asset id. A rig can be built anywhere before its asset exists. Once the asset folder exists, the shape, weight and rig tools always use the asset's paths, so a file never lands in two places. Before it exists, they fall back to a file or folder dialog.

#### asset

| Tool | Select | Does |
|---|---|---|
| New Project... | nothing | Writes a `project.json` into a folder you pick (`Project.create`) |
| New Asset... | nothing | Asks for an asset id and one of the project's asset types, then writes the asset's `asset.json` |
| New Variant... | nothing | Copies a template you pick into the asset as the variant named by its `rigName` (`new_variant`) |
| Save Skeleton... | nothing | Saves the open scene as the asset's skeleton file. Refused when the asset uses another asset's skeleton |
| Save Model... | nothing | Saves the open scene as a variant's model file, the meshes it skins. Warns about meshes without a `meshId` |
| Build Rig from Asset... | nothing | `build_rig`: imports the skeleton, builds the variant's template, then loads the shapes, model and skin weights the asset has ([`assets.md`](assets.md#building-a-rig-from-an-asset)) |
| Save Rig | active rig | Saves the open scene as the variant's rig file. Before the asset folder exists, uses a file dialog |

#### mesh

| Tool | Select | Does |
|---|---|---|
| Mark Meshes for Skinning | meshes | Gives each selected mesh a `meshId` (`cmds.setRigMeshId`), the id its weight files are matched by. A mesh keeps the id it has, and the log says how many were new and how many kept theirs |
| Mark Meshes with New Ids | meshes | The same, but replaces their ids. Use it on a duplicated mesh, which copied its source's id |

Mark meshes in the model scene, before **Save Model...**, so every build imports meshes that already carry their ids.

#### joints

| Tool | Select | Does |
|---|---|---|
| Print Joint Markup | joints | Prints each joint's markup JSON (`cmds.rigJointMarkup(query=True)`) |
| Remove Joint Markup | joints | Removes their markup (`cmds.rigJointMarkup(remove=True)`) |

#### weights

| Tool | Select | Does |
|---|---|---|
| Save Skin Weights... | active rig | Saves every skinned mesh in the rig's namespace to the variant's `weights` folder, one file per mesh. Before the asset folder exists, uses a folder dialog |
| Load Skin Weights... | active rig | Loads the folder onto the meshes, matched by `meshId`, as one undo step |

#### shapes

| Tool | Select | Does |
|---|---|---|
| Mirror Shapes Left to Right / Right to Left | active rig | `cmds.mirrorRigControlShapes` from one side to the other |
| Save Control Shapes... / Load Control Shapes... | active rig | Saves or loads the variant's `shapes.json`. Before the asset folder exists, uses a file dialog |

#### control

| Tool | Select | Does |
|---|---|---|
| Select All Controls | active rig | Selects every control in the rig (`cmds.getRigControls`) |
| Select Mirror Controls | controls | Selects the controls on the other side instead (`cmds.getRigMirrorControl`) |

#### pose

The pose tools act on the selected rig controls, or on the whole active rig when no control is selected, so an animator can work on a limb or on everything with the same tool (`bmaya.maya.posetools.get_scope`). The pose commands set values and key nothing, so keying is its own tool.

| Tool | Does |
|---|---|
| Save Pose... | Saves the pose under a name you type, in the asset's `controlposes` folder. Asks before replacing a file. Before the asset folder exists, a file dialog |
| Load Pose... | Loads a pose file chosen in a dialog that opens in `controlposes` (`cmds.loadRigPose`) |
| Save Animation... | Saves the keys over the playback range under a name, in `controlanims` (`cmds.saveRigAnimation`). Before the asset folder exists, a file dialog |
| Load Animation... | Loads an animation file, keyed at the frames it was saved on (`cmds.loadRigAnimation`) |
| Load Animation Mirrored... | The same, with the Left side's keys on the Right and the Right's on the Left |
| Mirror Pose | `cmds.mirrorRigPose`. The command picks the source side: the side of the selected controls when they share one, else Left |
| Mirror Pose Left to Right / Right to Left | The same, with the direction chosen |
| Flip Pose | `cmds.flipRigPose`: swaps the sides |
| Zero Pose | `cmds.zeroRigControls`: every control to its rest |
| Key All Controls | `rigmodules.pose.key_rig`: keys every channel on every control of the active rig |
| Key Selected Modules | `rigmodules.pose.key_modules`: keys the controls of the modules the selection names (a selected module node, or the module of a selected control). Raises when the selection names none |

#### clip

Clips are FBX files ([`clips.md`](clips.md)).

| Tool | Does |
|---|---|
| Capture Joint Clip... | Captures the active rig's export joints over the playback range as a clip, under a name typed in a dialog, in the asset's `exports` folder. Asks for a `.fbx` file before the asset folder exists |
| Capture Joint Pose... | The same at the current frame, as a clip with one pose |
| Pose From Joint Pose... | Sets the selected controls, or the whole active rig, from a one-pose clip chosen in a dialog that opens in `exports` (`cmds.poseRigFromJointPose`). Uses the bone map beside the FBX when there is one |
| Animate From Joint Clip... | Keys them from a clip (`cmds.animateRigFromJointClip`), with the ControlAnim beside the FBX as the sidecar when there is one |
| Save Skeleton Export | Writes the active rig's skeleton export into its asset's `exports` folder. Needs the asset folder |
| Check Clip Against Skeleton... | Checks an animation FBX against the asset's skeleton export, naming every joint whose name or parent differs |
| Edit Clip Properties... | Sets loop, root motion and additive type of a clip's `animproperties` in a small dialog, keeping its events and curves |

### Scripts call the same functions

Every tool above is a call into `bmaya.maya.assettools`, `bmaya.maya.posetools` or `bmaya.maya.rigging.joint`, and those functions take arguments, so scripts and batch jobs call them without the dialogs. The functions at the top of `assettools` (`new_variant`, `save_skeleton`, `save_model`, `build_rig`, `save_rig`, `save_control_shapes`, `load_control_shapes`, `save_pose`, `save_animation`, `save_joint_clip`, `save_skeleton_export`, `check_clip_skeleton`, `set_clip_properties`, `save_skin_weights`, `load_skin_weights`, `mark_meshes_for_skinning`) are the scriptable ones. The `*_interactive` functions below them are the menu's entry points: they read the active rig and ask through a `Prompter` (Qt dialogs in a GUI session), then call them. A script can run an entry point too, with its answers in a `bmaya.core.prompts.ScriptedPrompter` ([`architecture.md`](architecture.md#questions-a-tool-asks)). In mayapy with no prompter, a question raises `PromptError` naming it rather than waiting on a dialog.

```python
import bmaya.maya.assettools

bmaya.maya.assettools.new_variant("shooter\\main\\characters\\hero", r"C:\rigs\Human.json")   # variant "Human"
bmaya.maya.assettools.save_skeleton("shooter\\main\\characters\\hero")              # the open scene
bmaya.maya.assettools.save_model("shooter\\main\\characters\\hero", "Human")        # the open scene, meshes only
rig_root = bmaya.maya.assettools.build_rig("shooter\\main\\characters\\hero", "Human")
bmaya.maya.assettools.save_control_shapes(rig_root)                                # variants/Human/shapes.json
bmaya.maya.assettools.save_skin_weights(rig_root)                                  # variants/Human/weights/*.json
bmaya.maya.assettools.save_rig(rig_root)                                           # variants/Human/hero_Human_rig.ma
```

## The active rig

`bmaya.maya.activerig` picks the RigModules rig the menu tools act on. Selecting any node of a rig (a control, a joint the rig drives, a module or the rig root) makes that rig active, and it stays active while other things are selected. A new or opened scene makes its first rig active. The Script Editor logs `Active rig: <rig root>` when it changes.

| Function | Does |
|---|---|
| `get_active_rig()` | The tracker's rig while it still exists, else the selection's rig, else the scene's first rig. Returns a `rigmodules.query.RigInfo`. Raises `RuntimeError("There is no RigModules rig in the scene.")` when there is none. Works without a tracker, so batch jobs and tests can call it |
| `rig_from_selection()` | The rig of the most recently selected node that belongs to one, or `None`. Checks at most the last 32 selected nodes, because it runs on every selection change |
| `first_rig_in_scene()` | The first rig `rigmodules.query.get_rigs()` returns, or `None` |
| `ActiveRigTracker()` | Singleton that follows the active rig through `EventsRegistry` selection, new-scene and open-scene callbacks. `current()` returns the running one, `stop()` removes its callbacks, `update_from_scene()` recomputes |

Nodes are matched to rigs by `rigmodules.query.find_rig_info`, which walks the rig's connections. A broken rig is skipped, because `getRigInfo` has already reported it. Startup starts the tracker once the plugin loads, and not in batch.

## Tests

The registry, its checks and `run_tool` are tested in `tests/core`, with `build_menus` and both editors offscreen in mayapy. The RigModules menu layout, every registry call and each tool run in Maya are tested in `tests/rigging/rigmodules_menu`, the asset tools in `tests/asset/test_maya_asset_tools.py` and the tracker in `tests/asset/test_maya_active_rig.py` ([`../tests/README.md`](../tests/README.md)).
