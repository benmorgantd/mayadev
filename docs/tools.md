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

`bmaya.maya_ui.menus` draws the menus: `ToolMenu(menu_id, layout, registry).build_ui()` deletes any menu with that id and builds it on Maya's main menu bar, and `build_menus()` does it for every menu in `bmaya.maya.constants.MENUS`:

| `MenuSpec` | Maya menu id | Layout | Plugin |
|---|---|---|---|
| bmaya tool menu | `bmaya_menu` | `bmaya_menu.json` | none: always built |
| RigModules menu | `rigmodules_menu` | `rigmodules_menu.json` | `RigModules`: built only while it is loaded |

`build_menus()` reads the registry and **every** layout and checks them all before it touches a menu, so a bad edit leaves the current menus in place, and one reload shows every broken file. The layout of a menu whose plugin isn't loaded is still checked. A menu item's command is `run_tool(tool)`, so each click imports its module and a module that fails to import breaks only its own items.

### Editors

Both are Qt windows opened from the **bmaya tool menu**.

**Tool Registry Editor** (`bmaya.maya_ui.tool_registry_editor.show_window`): create, edit, run and delete tools. The window is widgets over a `bmaya.core.tool_registry_edit.RegistryEditSession`, which holds the state and every rule below (the picked tool, the unsaved flag, the status, the checked save) and runs in plain Python. Its `tools_changed`, `selection_changed` and `changed` events tell a view what to redraw. The editors are opened once: a second **Registry Editor** menu item closes the open one first, and raises it instead when it holds unsaved edits you keep.

| Part | Does |
|---|---|
| New Tool | Asks for the id, checked as you type, and the name. `short_name` starts as the name, and the call starts empty. The id is read-only afterwards |
| Module | A text field with a completer over every module under `bmaya` and `rigmodules`, found by reading the folders (nothing is imported). Any import path can be typed |
| Function | A drop-down filled when the module imports: the public functions defined in that module, with the first docstring line shown under it |
| Arguments | A form built from the function's signature: a widget chosen by annotation (check box for `bool`, spin box for `int` and `float`, text for `str`, drop-down for `Literal` and `Enum`, JSON text for anything else) and a **Set** check box. An unset row shows the default greyed and is **not saved**, so `kwargs` holds only what was chosen. A parameter with no default is always set. A saved kwarg the function no longer has shows as a red row with a Remove button |
| Status | `OK`, or the first problem of the tool's call. Run is enabled only on `OK`, and runs the tool as edited |
| Open Registry | Replaces the loaded registry with the file's, and asks first when there are unsaved edits. A file that fails its check is refused with the full report |
| Save Registry | Runs the structure check and the calls check on the whole registry, and, for the master registry, every menu layout against it. Deleting a tool a layout still uses is an error that names the layout. A refused save shows the full report and writes nothing |

**Tool Menu Editor** (`bmaya.maya_ui.menus.show_window`): arrange registry tools into submenus, separators and order.

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

Built only while the plugin is loaded (`MenuSpec.plugin` in `bmaya.maya.constants.MENUS`), and deleted when it unloads. It is a set of submenus, in this order: panels, asset, mesh, joints, weights, shapes, control, pose, clip. A new tool goes in the submenu for its topic, and only a tool animators use constantly goes at the top level. Dialogs are small, and errors report in the Script Editor.

Most tools act on the **active rig**, so nobody selects a rig root ([below](#the-active-rig)). The tools that ask for an asset id fill it in with the active rig's asset id. A rig can be built anywhere before its asset exists. Once the asset folder exists, the shape, weight and rig tools always use the asset's paths, so a file never lands in two places. Before it exists, they fall back to a file or folder dialog.

#### panels

| Tool | Does |
|---|---|
| Active Rig Panel | Opens the [active rig panel](#the-active-rig-panel), docked beside the Attribute Editor (`bmaya.maya_ui.rigpanel.show_window`) |
| Library Browser | Opens the [library browser](#the-library-browser), docked the same way (`bmaya.maya_ui.librarybrowser.show_window`) |

#### asset

| Tool | Select | Does |
|---|---|---|
| New Project... | nothing | Writes a `project.json` into a folder you pick (`Project.create`) |
| New Asset... | nothing | Asks for an asset id and one of the project's asset types, then writes the asset's `asset.json` |
| New Rig... | nothing | Asks for the asset, a template to copy, the rig's name (the template's `rigName` is offered) and its skeleton, then copies the template into `rigs/<rig>` with its `rigName` set to the rig's name and writes `rig.json` (`new_rig`) |
| New Look... | nothing | Asks for the asset, the look's name (`default` is offered for the first) and the skeleton its meshes bind to, then writes `looks/<look>/look.json` (`new_look`) |
| Save Skeleton... | nothing | Saves every joint in the scene as a skeleton of the asset: `skeletons/<skeleton>/skeleton.json`, the only form a skeleton is stored in. The scene is not saved or renamed. Every joint must be marked, and none may be driven by a rig. Nothing is written when one fails |
| Load Skeleton... | nothing | Creates a skeleton's joints from its `skeleton.json`, at rest and marked, and selects them |
| Save Model... | nothing | Saves the selected meshes (every mesh when none is selected) as a look's model file: meshes only, from their undeformed shape, with no skinning, no history and no joints. The scene is left as it was. Warns about meshes without a `meshId` |
| Build Rig from Asset... | nothing | `build_rig`: creates the rig's skeleton, builds its template, then loads the shapes, and puts the look on the rig with `apply_look` (the look is recorded on the rig). The look is asked for only when the rig can wear more than one ([`assets.md`](assets.md#building-a-rig-from-an-asset)) |
| Save Rig | active rig | Saves the open scene as the rig's scene file. Before the asset folder exists, uses a file dialog |

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
| Save Skin Weights... | active rig | Saves every skinned mesh in the rig's namespace to a look's `weights` folder, one file per mesh (the look is asked for when the rig can wear several). Before the asset folder exists, uses a folder dialog |
| Load Skin Weights... | active rig | Loads the folder onto the meshes, matched by `meshId`, as one undo step |

#### shapes

| Tool | Select | Does |
|---|---|---|
| Mirror Shapes Left to Right / Right to Left | active rig | `cmds.mirrorRigControlShapes` from one side to the other |
| Save Control Shapes... / Load Control Shapes... | active rig | Saves or loads the rig's `shapes.json`. Before the asset folder exists, uses a file dialog |

#### control

| Tool | Select | Does |
|---|---|---|
| Select All Controls | active rig | Selects every control in the rig (`cmds.getRigControls`) |
| Select Mirror Controls | controls | Selects the controls on the other side instead (`cmds.getRigMirrorControl`) |

#### pose

The pose tools act on the selected rig controls, or on the whole active rig when no control is selected, so an animator can work on a limb or on everything with the same tool (`bmaya.maya.posetools.get_scope`). The pose commands set values and key nothing, so keying is its own tool. Each tool has a plain function with the scope as an argument (`zero_pose(scope)`, `mirror_pose(scope, left_to_right)`, `flip_pose(scope)`, each returning how many controls changed), and the `*_interactive` menu tool is that function on `get_scope()`.

### The active rig panel

`bmaya.maya_ui.rigpanel.show_window` (RigModules `design/active-rig-panel.md`, D50) opens a panel on the active rig, in labelled sections that fold when you press their title (a down arrow open, a right arrow folded): **Rig**, **Select**, **Pose**, **Space** and **IK/FK**.

- **Rig** shows the active rig, with a drop-down when the scene has more than one, and Refresh. With no rig in the scene it says so, and the other sections are off.
- **Select** has All and Mirror (the controls on the other side of the selected ones), then one button per module and side, each with the module (cube) icon. Mirror, the three mirror and flip buttons, Key (a keyframe diamond) and Key Module (a cube) have icons too; Zero has none. A button selects that module's controls, and Ctrl or Shift adds them to the selection. The panel does not list controls: Maya's Outliner does that, and a copy would need the Outliner's own selection, icons and spacing to feel right.
- **Pose** has Zero, Mirror L>R, Mirror R>L, Flip, Key and Key Module. They act on the selected controls, or on the whole rig when none is selected, as the menu tools do.
- **Space** appears only while exactly one selected control has a space switch (a rig built with a `Parent`, `Orient` or `Point` constraint of two or more drivers). It shows the control's name and a button per space, with the current one pressed. Pressing another switches to it, and the control keeps its place in the world (`setRigControlSpace`). A TwoBoneIk limb's pole has a space switch too, `Parent` and `Ik`. A switch keys nothing, unless the **Key** box is ticked: then the control's channels are keyed on the previous frame and on the current one, so the animation holds the old space up to the switch. One undo reverts the switch and its keys. The panel reads the selected control only while it is showing.
- **IK/FK** appears while the selection is one to six controls of one TwoBoneIk limb, so a limb's group button shows it. It shows the limb's name and mode (`IK`, `FK` or `blend 0.50`) and an **IK** and an **FK** button, with the current mode pressed. Pressing the other one runs `setRigIkFkBlend`: the limb's joints stay where they are. A switch keys nothing, unless the **Key** box is ticked: then all six controls, the settings control with its `ikFkBlend` included, are keyed on the previous frame and on the current one. One undo reverts the switch and its keys. `ikFkBlend` is a double, so between the two keys a sub-frame shows a blend. A limb starts in IK, so Zero puts it back in IK.

An error from a button goes to the log. The out-of-date line is not built yet.

The window is widgets and connections only. `bmaya.maya.rigpanel.RigPanelSession` is the view-model, and has no Qt: `rigs`, `rig` and `groups` (a `ControlGroup` per module and side, read once per refresh), the `changed` event, and `spaces_changed` and `space` (a `SpaceState`: the selected control, its constraint, the space labels and the current index), `limb_changed` and `limb` (a `LimbState`: the limb's module, controls, settings control and `ikFkBlend`, with `mode` `IK`, `FK` or `Blend`), and the commands the buttons call (`set_active`, `select_group`, `select_all`, `select_mirrors`, `zero`, `mirror`, `flip`, `key_rig`, `key_modules`, `set_space(label, key=False)`, `set_ik_fk(mode, key=False)`, `refresh_space`, `refresh_limb` and `watch_selection(bool)`). It follows `ActiveRigTracker.changed`, so a script that changes the active rig updates an open panel. `close()` stops it following, and the window calls it when it is destroyed, which a docked panel is with its workspace control and often with no close event. The docked panel is checked in a GUI Maya by `tests/gui/rigpanel/run.bat` (manual).

### The library browser

`bmaya.maya_ui.librarybrowser.show_window` (RigModules `design/library-browser.md`, D51) opens one docked window on the active rig's pose and animation library, and follows the active rig. It lists the files of three sources: **Approved** (the rig's own `controlposes` and `controlanims`), **Shared** (those of the rig it was copied from, when `rig.json` names a source) and **User** (your own, [`assets.md`](assets.md#library)). Each has a chip that shows or hides it.

- **Poses and Animations** are two tabs, two libraries.
- **Search** is the box under the tabs: free words match the name, tags and description, and `tag:fist`, `template:Human`, `by:bmorgan`, `region:hands`, `status:final`, `category:` and the other terms ([`assets.md`](assets.md#library)) match a field. **Filter** lists the tags, templates, regions, statuses and categories in use, and picking one writes its term in the box (a second pick takes it out), so nobody needs the syntax.
- **List** shows a name (with a pose or keyframe icon) and the source. **Details** adds tags, template, author, date and frames, and a click on a header sorts. A file that can't be read is red, and one that has controls the rig lacks is amber.
- **Under the list** are what the selected file holds (controls, channels, unmatched controls), its template, skeleton and author, its description, and warnings: controls the rig lacks, a frame rate the scene doesn't have (the load would be refused), and a status or rig region that the project's `project.json` doesn't list.
- **Apply** loads the selected file onto the **scope**: *Auto* (the selected controls, else the whole rig), *Selection*, *Whole rig* or a **mask**, the rig's own (one per module type, side and module), the team's and your own, picked by control markup and never by name, and narrowed by the selection. **Mirror** puts the Left side on the Right and the Right on the Left in the file's data before it is written. **Start at** is for animations: empty means the frames it was saved on, and **Now** fills the current frame. Apply is one undo step. Only a double click, Return or the button applies: a click, a hover or an arrow key only selects. **Masks** saves the selected controls as a mask of yours (it becomes the scope), and deletes one of yours.
- **Save** writes the scope into your own library: type a name (a free one, `pose_001`, is offered) and press Return, with comma-separated **Tags** if you like (the tags in use are offered as you type). A pose stores the scope's channels, and an animation its keys over the playback range, which the window shows. A name you already have asks before it replaces. The tags clear after a save.
- **Right click** a file for Apply, Copy to My Library (Approved and Shared files), and Rename, Edit Tags and Description and Delete (your own files only: the others are disabled, not hidden). Delete keeps a local version.
- The window reads the library again each time it opens and on Refresh, and nothing watches the disk. An error from any button goes to the log and to the line at the bottom.

The window is widgets and connections only. `bmaya.maya.librarybrowser.LibrarySession` is the view-model, with no Qt ([`architecture.md`](architecture.md)); the window asks the questions a session must not (replace, rename, delete, a mask's name) through the `Prompter` and a small tags dialog. The docked window is checked in a GUI Maya by `tests/gui/librarybrowser/run.bat` (manual).

| Tool | Does |
|---|---|
| Save Pose... | Saves the pose under a name you type (a free `pose_001` is offered), in your own library of the rig: `<projects root>\user\<login>\animlibrary\<asset id>\<rig>\controlposes`, as `<name>.controlpose.json` with the author, template and skeleton in its `meta`. No source control. Asks before replacing a file. Before the asset folder exists, a file dialog |
| Load Pose... | Loads a pose file chosen in a dialog that opens in your own library, else in the asset's `controlposes` (`posetools.load_pose`, one undo step) |
| Save Animation... | Saves the keys over the playback range under a name, in your own library's `controlanims`, as `<name>.controlanim.json`. Before the asset folder exists, a file dialog |
| Load Animation... | Loads an animation file, keyed at the frames it was saved on (`posetools.load_animation`, one undo step) |
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
| Save Skeleton Export | Writes the active rig's skeleton export into the `exports` folder of its skeleton. Needs the asset folder |
| Check Clip Against Skeleton... | Checks an animation FBX against the skeleton export of the active rig's skeleton, naming every joint whose name or parent differs |
| Edit Clip Properties... | Sets loop, root motion and additive type of a clip's `animproperties` in a small dialog, keeping its events and curves |

### Scripts call the same functions

Every tool above is a call into `bmaya.maya.assettools`, `bmaya.maya.posetools` or `bmaya.maya.rigging.joint`, and those functions take arguments, so scripts and batch jobs call them without the dialogs. The functions at the top of `assettools` (`new_rig`, `new_look`, `save_skeleton`, `load_skeleton`, `save_model`, `build_rig`, `save_rig`, `save_control_shapes`, `load_control_shapes`, `save_pose`, `save_animation`, `save_joint_clip`, `save_skeleton_export`, `check_clip_skeleton`, `set_clip_properties`, `save_skin_weights`, `load_skin_weights`, `mark_meshes_for_skinning`) are the scriptable ones. The `*_interactive` functions below them are the menu's entry points: they read the active rig and ask through a `Prompter` (Qt dialogs in a GUI session), then call them. A script can run an entry point too, with its answers in a `bmaya.core.prompts.ScriptedPrompter` ([`architecture.md`](architecture.md#questions-a-tool-asks)). In mayapy with no prompter, a question raises `PromptError` naming it rather than waiting on a dialog.

```python
import bmaya.maya.assettools

bmaya.maya.assettools.new_rig("shooter\\main\\characters\\hero", r"C:\rigs\human.json", "body")   # rigs/body, rigName "body"
bmaya.maya.assettools.new_look("shooter\\main\\characters\\hero")                         # looks/default
bmaya.maya.assettools.save_skeleton("shooter\\main\\characters\\hero")                    # the scene's joints, skeletons/default/skeleton.json
bmaya.maya.assettools.save_model("shooter\\main\\characters\\hero", "default")            # the scene's meshes, meshes only
rig_root = bmaya.maya.assettools.build_rig("shooter\\main\\characters\\hero", "body")      # into hero_body, with the default look
bmaya.maya.assettools.save_control_shapes(rig_root)                                  # rigs/body/shapes.json
bmaya.maya.assettools.save_skin_weights(rig_root, "default")                         # looks/default/weights/*.json
bmaya.maya.assettools.apply_look(rig_root, "winter")                                 # swaps the rig's look: no controls or animation change
bmaya.maya.assettools.save_rig(rig_root)                                             # rigs/body/hero_body_rig.ma
```

## The active rig

`bmaya.maya.activerig` picks the RigModules rig the menu tools act on. Selecting any node of a rig (a control, a joint the rig drives, a module or the rig root) makes that rig active, and it stays active while other things are selected. A new or opened scene makes its first rig active. The Script Editor logs `Active rig: <rig root>` when it changes.

| Function | Does |
|---|---|
| `get_active_rig()` | The tracker's rig while it still exists, else the selection's rig, else the scene's first rig. Returns a `rigmodules.query.RigInfo`. Raises `RuntimeError("There is no RigModules rig in the scene.")` when there is none. Works without a tracker, so batch jobs and tests can call it |
| `rig_from_selection()` | The rig of the most recently selected node that belongs to one, or `None`. Checks at most the last 32 selected nodes, because it runs on every selection change |
| `first_rig_in_scene()` | The first rig `rigmodules.query.get_rigs()` returns, or `None` |
| `ActiveRigTracker()` | Singleton that follows the active rig through `EventsRegistry` selection, new-scene and open-scene callbacks. `current()` returns the running one, `stop()` removes its callbacks, `refresh()` recomputes the active rig |
| `ActiveRigTracker.changed` | An `Event` that emits the rig root (or `None`) when the active rig changes, and once more on `refresh()` when it stays the same, because the scene's rigs may have changed. It belongs to the class, so a listener survives `stop()` and a new tracker. `build_rig` makes the rig it builds the active one |

Nodes are matched to rigs by `rigmodules.query.find_rig_info`, which walks the rig's connections. A broken rig is skipped, because `getRigInfo` has already reported it. Startup starts the tracker once the plugin loads, and not in batch.

## Tests

The registry, its checks and `run_tool` are tested in `tests/core`, with `build_menus` and both editors offscreen in mayapy. The RigModules menu layout, every registry call and each tool run in Maya are tested in `tests/rigging/rigmodules_menu`, the asset tools in `tests/asset/test_maya_asset_tools.py`, the tracker in `tests/asset/test_maya_active_rig.py` and the panel's session, the tracker event and the plain pose functions in `tests/asset/test_maya_rigpanel.py`, and the panel window over a fake session, and on a real rig when `RIGMODULES_PLUGIN` is set, in `tests/core/test_maya_rigpanel_view.py` ([`../tests/README.md`](../tests/README.md)).
