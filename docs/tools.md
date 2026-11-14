# Tools and menus

How a tool is defined, how the two menus are built from it, what every RigModules menu tool does, and the active rig that most of them act on.

## Tool registry and menu layout

A tool is data, not a menu item. Two kinds of JSON file under `toolsets/` describe the menus:

| File | Holds |
|---|---|
| `master_tool_registry.json` | Every tool: a GUID, a name and a Python snippet. The source of truth |
| `bmaya_menu.json`, `rigmodules_menu.json` | A menu layout: which tools, in which submenus, in what order |

A tool can be in any number of layouts, or none (the registry's `Create a Cube` is in no menu).

### Registry entry

```json
{
    "guid": "99e72b04-4a77-4492-962a-1a96e91991e1",
    "name": "New Project...",
    "short_name": "New Project...",
    "script": "import bmaya.maya.assettools\nbmaya.maya.assettools.new_project_ui()\n",
    "icon": null,
    "enabled": true
}
```

| Key | Meaning |
|---|---|
| `guid` | Identity. Layouts refer to tools by it, so a tool can be renamed freely |
| `name` | The menu label |
| `short_name` | Defaults to `name` |
| `script` | Python source, run with `exec` in `bmaya.maya_ui.tool_views.tool_menu`'s globals, which have `cmds` (`maya.cmds`) imported. A script should import what else it uses |
| `icon` | Optional image path for the menu item |
| `enabled` | `false` greys the item out wherever it appears |

`bmaya.core.tool_registry.ToolRegistry` loads and saves the file (`load_registry`, `save_registry`) and holds `Tool` objects by GUID. It is plain Python.

### Menu layout

```json
{
    "label": "RigModules",
    "items": [
        {
            "type": "submenu",
            "label": "asset",
            "items": [
                { "type": "tool", "guid": "99e72b04-4a77-4492-962a-1a96e91991e1", "enabled": true }
            ]
        }
    ]
}
```

| Item `type` | Keys | Builds |
|---|---|---|
| `tool` | `guid`, `enabled` (default `true`) | A menu item. Enabled only when both the tool's and the layout's `enabled` are true. A GUID missing from the registry shows a disabled `Missing Tool (Ref: <first 8 characters>)` item, so a broken layout still loads |
| `submenu` | `label`, `items` | A tear-off submenu |
| `separator` | | A divider |

`ToolMenu(menu_id).load_layout(path)` reads a layout and `build_ui(registry)` deletes any menu with the same id and builds it on Maya's main menu bar. Startup builds `bmaya_menu.json` as the menu `test` and `rigmodules_menu.json` as `rigmodules_menu` ([`setup.md`](setup.md#startup)).

### Editors

Both are Qt windows opened from the **bmaya tool menu**.

| Editor | Opened by | Does |
|---|---|---|
| Tool Registry Editor (`bmaya.maya_ui.tool_registry_editor.show_ui`) | Tool Registry Editor | Create, edit, run and delete tools, with a syntax-highlighted script editor. File menu: Open Registry, Save Registry, Save Registry As |
| Tool Menu Editor (`bmaya.maya_ui.tool_views.tool_menu.show_menu_editor_ui`) | Tool Menu Editor | Arrange tools from the registry into submenus, separators and order, and save the layout. File menu: Load Master Registry, Open Menu Layout, Save Menu Layout, Save Menu Layout As |

Saving a registry or layout in an editor and then running **Reload Menu (dev)** shows the change without restarting Maya.

## Menus

### bmaya tool menu

| Submenu | Tool | Does |
|---|---|---|
| (top level) | Tool Registry Editor, Tool Menu Editor | The two editors above |
| Joints | Create Joint at Center | `joint.create_joint_at_selection_center()` |
| Joints | Zero Transforms | `cmds.makeIdentity` on the selection (translate, rotate, scale) |
| Joints | Orient to World, Orient to Mesh | `joint.orient_to_world`, `joint.orient_to_mesh` (the last selection is the mesh). **Both scripts import `bmaya.maya.rigging.joints`, and the module is `joint`, so they fail today** ([`status.md`](status.md)) |

### RigModules menu

Built only when the plugin loads. It is a set of submenus, in this order: asset, mesh, joints, weights, shapes, control, pose, clip, dev. A new tool goes in the submenu for its topic, and only a tool animators use constantly goes at the top level. Dialogs are small, and errors report in the Script Editor.

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

#### dev

Reload RigModules (dev), Unload RigModules (dev) and Reload Menu (dev). See [`setup.md`](setup.md#dev-reload).

### Scripts call the same functions

Every tool above is a call into `bmaya.maya.assettools` or `bmaya.maya.posetools`, and those functions take arguments, so scripts and batch jobs call them without the dialogs. The functions at the top of `assettools` (`new_variant`, `save_skeleton`, `save_model`, `build_rig`, `save_rig`, `save_control_shapes`, `load_control_shapes`, `save_pose`, `save_animation`, `save_joint_clip`, `save_skeleton_export`, `check_clip_skeleton`, `set_clip_properties`, `save_skin_weights`, `load_skin_weights`, `mark_meshes_for_skinning`) are the scriptable ones, and the `*_ui` functions below them ask and call them.

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

The menu layout and every script are tested in `tests/rigging/rigmodules_menu`, the asset tools in `tests/asset/test_maya_asset_tools.py` and the tracker in `tests/asset/test_maya_active_rig.py` ([`../tests/README.md`](../tests/README.md)).
