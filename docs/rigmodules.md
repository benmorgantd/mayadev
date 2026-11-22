# Using RigModules

Everything mayadev takes from [RigModules](https://github.com/benmorgantd/cpp-rigmodules): what crosses the boundary, who calls it, and the rules for adding to it. This page is the list to check when a RigModules command or `rigmodules` function changes.

mayadev depends on RigModules and never the reverse (D24). A mayadev tool reaches a built rig only through the `rigmodules` Python package and the plugin's commands, never by walking node connections or parsing names. RigModules' own documentation for each name is in its `docs/commands.md` and `docs/python.md`.

## What mayadev needs installed

| Piece | From RigModules | Used for |
|---|---|---|
| The plugin `RigModules.mll` | `cpp/x64/Release` | Every `cmds.*Rig*` command. Loaded at startup from `RIGMODULES_PLUGIN` ([`setup.md`](setup.md)) |
| The `rigmodules` package | `python/rigmodules`, put on `PYTHONPATH` by `RigModules.mod` | The query, template, pose, skin weight, display layer, group and FBX functions |

The package imports no Qt, no `bmaya`, reads no environment variables and no asset paths, so it works in a bare mayapy with only the plugin loaded. mayadev supplies the paths.

Modules that import `rigmodules` at the top (`bmaya.maya.activerig`, `posetools`, `assettools`, `assethandlers`) fail on import without it. `bmaya.core.asset` never imports it.

## Commands called

Python `maya.cmds` calls, with the module that makes them.

| Command | Called from | Used for |
|---|---|---|
| `cmds.createRigFromTemplate(*joints, template=, asset=, namespace=, parentRig=)` | `assettools.build_rig` | Build a rig on the skeleton it just created. `build_rig` always passes `namespace`, because the skeleton goes in first: `{asset name}_{rig}`, the same as RigModules' default (D54). It passes `parentRig` (the parent's rig root) only for a rig whose `rig.json` has a `parent` (D55): RigModules requires it for a template with `parent:` ids and refuses it for one without |
| `cmds.setRigLook(rig_root, mesh=, file=, rigidMesh=, asset=, look=, ignoreSkeletonHash=)` | `assettools.apply_look` | Put the rig in a look: the imported meshes and their weight files (RigModules D54 phase 5), and the marked meshes with no file yet, which `rigidMesh` binds to the top skin joint (D68). Fails on a weight file with another skeleton's hash unless `ignoreSkeletonHash`, deletes the previous look's meshes, records the look |
| `cmds.rigJointMarkup(*joints, query=True)`, `edit=True, side=` and `remove=True` | Registry tools (Print and Remove Joint Markup, Mirror Joints and Add Twist Joints, in `assettools`) | Inspect, clear, mirror and create joint markup |
| `cmds.rigJointMarkup(*joints, query=True)` (the whole scene's joints in one call), `edit=True, usage=/side=/export=/skin=`, the four value flags to create, and `remove=True` | `markupmodel.MarkupModel` (the Asset Editor's Markup tab, RigModules D61) | Show the selection's markup, edit it across every selected joint in one undo step, and keep (side, usage) unique per namespace before the build asks |
| `cmds.getRigControls(rig_root)` | Registry tool (Select All Controls, in `posetools`) | Every control of the active rig |
| `cmds.getRigMirrorControl(control)` | Registry tool (Select Mirror Controls, in `posetools`) | The control on the other side |
| `cmds.mirrorRigControlShapes(rig_root, leftToRight=)` | Registry tools (Mirror Shapes, in `assettools`) | Copy shapes across sides |
| `cmds.mirrorRigControlShapes(rig_root, leftToRight=)` | `shapemodel.ShapeModel.mirror` (the Asset Editor's Shapes tab) | The same, for the rigs of the selected controls |
| `cmds.renameRigNodes(*nodes, base=, side=, startIndex=)` and `renameRigNodes(name, query=True)`, through `rigmodules.naming.rename_nodes` and `parse` | `namingmodel.NamingModel` (the Asset Editor's Naming tab) | Rename the selection into the naming convention with a root, side and start number, and mirror Left and Right names. `parse` is given the leaf name: the query returns nothing for a `\|long\|path` |
| `setAttr` on a `rigControlNode`'s `shapeType` (an enum index), `shapeTransform` (a matrix, 16 numbers in row vector order), `filled` and `wireframeAlpha`, and `attributeQuery(listEnum=True)` on `shapeType` | `shapemodel.ShapeModel` | Set the shape of every selected control. These are the attributes of RigModules `docs/controls.md`: renaming one, or changing the matrix order or the enum, breaks this tab |
| `cmds.saveRigControlShapes(rig_root, file=)`, `cmds.loadRigControlShapes(...)` | `assethandlers.RigShapesHandler`, `assettools` (no-asset fallback) | The rig's `shapes.json` |
| `cmds.setRigMeshId(newId=)` | `assettools.mark_meshes_for_skinning` | Give meshes the id weight files match on |
| `cmds.smoothSkinWeights(iterations=, strength=)` | `assettools.smooth_skin_weights` | Smooth the selected vertices' (or meshes') skin weights over their neighbors, one undo step (RigModules D64) |
| `cmds.skinBrushCtx(name)`, `cmds.skinBrushCtx(name, edit=True, operation=, radius=, strength=)` | `assettools.activate_skin_brush`, `skinbrush.SkinBrushSession` (the settings panel) | The skin brush tool: paints the weights under a brush as you drag (`operation` is `smooth`, `restDelta` or `restEdge`, the last two RigModules D66), one undo step per stroke (RigModules D65). GUI only |
| `cmds.saveRigSkinWeights(mesh, file=)`, `cmds.loadRigSkinWeights(...)` | `assethandlers.RigSkinWeightsHandler` | One weight file per mesh |
| `cmds.saveRigPose(*scope, file=, meta=)`, `cmds.loadRigPose(*scope, file=, mirror=)` | `assethandlers.ControlPoseHandler`, `posetools.load_pose` | Poses, with the caller's part of the `meta` block (`author`, `template`, `skeleton`, `tags`, `description`), and a mirror applied to the file's data (D51). The rig fills `assetId`, `rigName`, `skeletonHash`, `pluginVersion` and `created` (D54) |
| `cmds.saveRigAnimation(*scope, file=, startFrame=, endFrame=, meta=)` | `assethandlers.ControlAnimHandler`, `AnimClipHandler` | Animations, and the ControlAnim beside a clip |
| `cmds.loadRigAnimation(*scope, file=, offset=, mirror=)` | `assethandlers.ControlAnimHandler`, `posetools.load_animation` | Load animation, offset and optionally mirrored |
| `cmds.zeroRigControls`, `cmds.mirrorRigPose(leftToRight=)`, `cmds.flipRigPose` | `posetools` | The pose tools |
| `cmds.setRigControlSpace(control, label=)` | `rigpanel.RigPanelSession.set_space` | Switch the selected control's space, either kind (a constraint's or the TwoBoneIk pole's), without moving it |
| `cmds.setRigIkFkBlend(module, blend=)` | `rigpanel.RigPanelSession.set_ik_fk` | Switch a TwoBoneIk limb to IK (1) or FK (0), matched so the limb's joints stay put |
| `query.find_ik_fk_limb(control)` | `rigpanel.RigPanelSession.refresh_limb` | The selected limb's module, six controls, settings control and `ikFkBlend` (RigModules D52) |
| `cmds.poseRigFromJointPose(*scope, jointPose=)` | `assettools.pose_from_joint_pose_interactive` | Restore controls from a one-pose clip |
| `cmds.animateRigFromJointClip(*scope, jointClip=, sidecar=)` | `assettools.animate_from_joint_clip_interactive` | Restore keys from a clip |

`scope` is a rig root, or controls of one rig. Paths go to commands with forward slashes.

## `rigmodules` functions called

| Function | Called from | Used for |
|---|---|---|
| `query.get_rig_info(node)` | `assettools` (every tool that finds an asset) | A node of a rig to its asset id, rig name (the rig's folder name), namespace and rig root. Raises when the node isn't in a rig |
| `query.find_rig_info(node)` | `activerig` | The same, returning `None` when the node isn't in a rig |
| `query.get_rigs(namespace=None)` | `activerig`, `assettools.build_rig` | The rigs in the scene, or in a namespace (which holds at most one, RigModules D54). `build_rig` refuses a namespace that already holds one |
| `query.RigInfo` | `activerig` | The result type. mayadev reads `rig_root`, `asset_id`, `rig_name` (the rig) and `namespace`. It also has `skeleton_hash` (also what `apply_look` compares a spanning look's weight files against), `parent_rig_root` (the rig root an attachment follows, `None` otherwise, D55), `rig_version`, `plugin_version` and `publish_version` (RigModules D54 renamed `variant` and removed `asset_root`) |
| `query.RIG_CONTROL_TYPE` | `posetools.get_scope` | The node type of a rig control, to filter the selection |
| `query.get_rig_controls(rig_root)`, `query.find_control(node)` | `posetools.get_selected_modules` | Map a selection to the modules of the active rig |
| `query.find_control(node)`, `query.find_rig_info(node)`, `query.get_rigs()`, `query.RIG_CONTROL_TYPE` | `markupmodel`, `shapemodel`, `assetfiles.AssetFilesModel` | Read the selected controls' markup, find a control's rig, and find the chosen asset's rig in the scene |
| `skinweights.read_file_skeleton_hash(path)` | `assettools.apply_look` | The `skeletonHash` a weight file was saved from, `""` for a file with none. Used to give a rig and its attachment the files of their own skeletons from one weights folder, and to fail early, naming the files, when the skeleton changed since the weights were saved |
| `template.get_rig_name(path)` | `assettools.new_rig`, `RigTemplateHandler` | The `rigName` of a template file, offered as the new rig's name |
| `pose.key_rig(rig_root)`, `pose.key_modules(rig_root, modules)` | `posetools` | Key every channel of a rig, or of chosen modules |
| `pose.key_controls(controls, time=)` | `rigpanel.RigPanelSession.set_space` | Key the switched control (or the six controls of a switched limb) on the previous frame and the current one |
| `query.find_control_space(control)` | `rigpanel.RigPanelSession.refresh_space` | The selected control's constraint, space labels and current space (RigModules `getRigControlSpace`, D50) |
| `query.get_rigs()`, `query.get_rig_controls(rig_root)` | `rigpanel.RigPanelSession.refresh` | The rigs in the scene and the active rig's controls, for the active rig panel |
| `query.get_rig_controls(rig_root)`, `query.RigControl` (`node`, `module`, `module_type`, `side`, `usage`) | `librarybrowser.LibrarySession` | The rig's masks, and the controls a mask picks |
| `library.get_data_file_info(rig_root, files)`, `library.DataFileInfo` | `librarybrowser.read_file_infos` | What each library file holds, and which of its controls the rig lacks, in one command call (`getRigDataFileInfo`, D51) |
| `library.set_data_file_meta(file, meta)` | `librarybrowser.LibrarySession.set_meta` | Edit a file's tags and description without loading it |
| `skinweights.get_mesh_id(mesh)`, `get_skinned_meshes(namespace)`, `get_meshes(namespace)`, `read_file_mesh_id(path)` | `assethandlers.RigSkinWeightsHandler`, `assettools.save_model` | Find skinned meshes and match weight files by `meshId` |
| `skinweights.get_meshes_by_name(namespace)`, `read_file_mesh_name(path)`, `set_mesh_id(mesh, mesh_id)` | `assethandlers.RigSkinWeightsHandler.load(by_name=True)` | Load Skin Weights by Name: match a file to a mesh by name and give the mesh the file's `meshId` (D68) |
| `displaylayers.add_meshes(rig_root, nodes)`, `groups.parent_meshes(rig_root, nodes)` | `assettools.apply_look` | Put an imported model into the rig's display layers and mesh group |
| `jointclip.write_fbx`, `read_fbx`, `capture_joint_clip` | `assethandlers.AnimClipHandler` | Clip FBX in and out, and capture a rig's export joints |
| `jointclip.write_skeleton_fbx`, `check_skeleton_match` | `assethandlers.save_skeleton_export`, `assettools.check_clip_skeleton` | The skeleton export and its match check |

## What flows the other way

Nothing in RigModules imports `bmaya`. These are the places RigModules documentation names mayadev, and they must stay true:

- The asset id format. `bmaya.core.asset.assetid` and RigModules' `core/AssetId` use the same rules, except that `assetid` also refuses an id that starts with `user` (the folder of each user's library: RigModules' `core/AssetId` does not yet), and a built rig stores its `assetId` in the rig root. A change to the rules is a change in both repos in one go.
- The folder names `controlposes`, `controlanims`, `exports` and `sources`, and the file names `<name>.controlpose.json` and `<name>.controlanim.json`, which RigModules' `docs/library.md` describes ([`assets.md`](assets.md#library) covers the library).
- The asset model, `design/asset-model.md`, which `bmaya.core.asset` implements (D29).

## Rules for crossing the boundary

1. **Ask `rigmodules`, never the nodes.** A tool that needs a rig's asset, controls, modules or meshes calls a `rigmodules` function. No `cmds.listConnections` into a rig, no splitting node names, no `getAttr` on a module node's attribute.
2. **A missing capability is a RigModules change first.** Add the command or function there, with its tests and docs, then call it here, and add its name to the tables above in the same change.
3. **Names are public API.** RigModules treats control, attribute, child plug and socket names as API because saved poses, animation and exports depend on them. mayadev stores the data, not the names: control data goes through markup (`side`, `usage`), never node names.
4. **mayadev owns paths.** RigModules commands take a file path and read or write it. Where that file lives, the version copy and the source control call are mayadev's (`bmaya.core.asset.handlers`).
5. **No `bmaya` import in `rigmodules`, and no environment variables there.** If a function there needs a path, mayadev passes it.

## When a RigModules name changes

Search this repo for the old name, in code and in `tests/`. The registry calls only mayadev functions, so a command is named inside a function and a name search finds it there. A `rigmodules` function that a registry entry names directly is caught by `check_calls` (the Registry Editor's Save and `tests/rigging/rigmodules_menu`), but a command called inside a mayadev function is not: only the name search and that function's test find it.

The Maya tests in `tests/asset` and `tests/rigging` run against a real plugin (`RIGMODULES_PLUGIN`) and are the check that every call here still exists. Without the variable they skip, so a green run with skips has not checked the boundary ([`../tests/README.md`](../tests/README.md)).
