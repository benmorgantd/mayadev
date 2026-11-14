# Clips

How an asset holds animation that leaves the rig: FBX clips in `exports`, skeleton data from other tools in `sources`, the skeleton export, and the engine properties file. The data model (control data against skeleton data) and the reasons are in RigModules' `docs/library.md` and `design/control-library.md` (D42). This page covers what mayadev writes and reads.

## Control data and skeleton data

| Kind | Folder | File | Written by |
|---|---|---|---|
| Control pose | `controlposes/` | `<name>.json` | `cmds.saveRigPose` |
| Control animation | `controlanims/` | `<name>.json` | `cmds.saveRigAnimation` |
| Skeleton clip | `exports/<name>/` | `<name>.fbx` and files beside it | `rigmodules.jointclip` |
| Skeleton data from outside | `sources/` | `<name>.fbx` (and `<name>.bonemap.json`) | Copied in by hand |

Control data binds to a rig's controls by markup, so it survives renames and rebuilds, and it keeps what joints can't (IK/FK blend, spaces, the animator's keys and tangents). Skeleton data is for another rig or skeleton, mocap and the engine. All four folders belong to the asset, so every variant on its skeleton shares them.

> RigModules' `docs/library.md` lists the ControlAnim in `controlanims/` as `<name>.anim.json`. The mayadev handler writes `controlanims/<name>.json`. The `.anim.json` name is used only for the ControlAnim that sits beside an exported clip. RigModules' `design/control-library.md` has the same name. Either the handler or the two RigModules pages moves, and that is the author's call ([`status.md`](status.md#known-problems)).

## An export bundle

An export is a folder, because it is a bundle:

```
exports\
  walk\
    walk.fbx                  what the joints do
    walk.anim.json            what the rig did: the ControlAnim the clip was captured from
    walk.animproperties.json  what the engine importer reads
    walk.bonemap.json         optional: joint markup for an FBX from another tool
  hero_skeleton.fbx           the skeleton export, in the folder itself: not a clip
  hero_skeleton.bonemap.json
```

| File | Written | Read | Purpose |
|---|---|---|---|
| `<name>.fbx` | `rigmodules.jointclip.write_fbx` | `rigmodules.jointclip.read_fbx` | The clip's joint animation |
| `<name>.anim.json` | `cmds.saveRigAnimation`, when a clip is captured from a rig | Restore: the `sidecar` flag of `cmds.animateRigFromJointClip` | Gives back what joints can't, with the animator's own keys |
| `<name>.animproperties.json` | `bmaya.asset.animproperties.write` | `animproperties.read` | How the clip plays and what rides on it. Read only by the engine importer |
| `<name>.bonemap.json` | The skeleton export, or by hand | `rigmodules.jointclip.read_fbx(..., bone_map)` | Joint markup, asset id and skeleton id for a file that carries none |

A clip name follows `CLIP_NAME`: it starts with a letter or digit and holds letters, digits, `_`, `-` and spaces.

## Saving a clip

```python
from bmaya.asset import Asset
from bmaya.maya import assethandlers

hero = Asset("shooter\\main\\characters\\hero")
assethandlers.register()
assethandlers.save_anim_clip(hero, "walk", rig_root="hero:rigRootModule1", start_frame=1, end_frame=48)
```

`save_anim_clip` versions only that clip's FBX, checks it out, calls `AnimClipHandler.save`, and tells source control about a new file. `handlers.save(hero, "exports", ...)` would copy the whole `exports` folder, so use `save_anim_clip`.

`AnimClipHandler.save(asset, path, name=, ...)`:

| Argument | Meaning |
|---|---|
| `name` | The clip name. Required, and checked against `CLIP_NAME` |
| `joint_clip` | A RigModules JointClip file to write as FBX |
| `rig_root`, `start_frame`, `end_frame` | Capture the rig's export joints over the range. Instead of `joint_clip`: pass one or the other, never both |
| `own_folder` | `True` (default): write `<path>/<name>/<name>.fbx`. `False`: write `<path>/<name>.fbx`, for a file the user chose in a dialog |
| `properties` | An `AnimProperties` to write as the clip's properties file, replacing one that is there |

A clip captured from a rig also gets its ControlAnim beside it. An export folder's clip gets the default properties when it has no properties file, and an existing file is kept, so a re-export never overwrites the engine data someone edited. A clip written with `own_folder=False` gets no properties. Nothing is written when an argument is wrong, and the temporary JointClip file is removed afterwards.

## Loading a clip

```python
clip = bmaya.asset.handlers.load(hero, "exports", name="walk")
cmds.animateRigFromJointClip(
    "hero:rigRootModule1", jointClip=clip.joint_clip,
    **({"sidecar": clip.sidecar} if clip.sidecar else {}))
```

`AnimClipHandler.load` finds `<path>/<name>/<name>.fbx` (an exports folder), or `<path>/<name>.fbx` (a folder of FBX files, such as the one a file dialog chose from), reads it through `rigmodules.jointclip.read_fbx` into a JointClip file, and returns an `AnimClip`:

| Field | Meaning |
|---|---|
| `name` | The clip name |
| `fbx` | The FBX path |
| `joint_clip` | The JointClip file read from the FBX: a temporary named after the clip in `%TEMP%\bmaya_joint_clips`, which the next load of the same name overwrites. Pass it to `cmds.animateRigFromJointClip(jointClip=...)` or `cmds.poseRigFromJointPose(jointPose=...)` |
| `sidecar` | The ControlAnim beside the FBX, or `None`, for the `sidecar` flag |
| `properties` | The `AnimProperties` beside the FBX, or `None` |

The bone map is the `bone_map=` argument, or the one beside the FBX when there is one. A missing clip raises `FileNotFoundError` naming the clips the folder has.

`SourceClipHandler` (file type `sources`) loads the same way and never saves: copy a mocap take or vendor skeleton and its bone map into the `sources` folder yourself.

## The skeleton export

The engine needs the skeleton as its own asset, and an animation pairs with the skeleton export it matches by joint names and hierarchy.

| Function | Does |
|---|---|
| `assethandlers.save_skeleton_export(asset, rig_root)` | Writes `exports/<name>_skeleton.fbx` (the rig's export joints at rest) and `<name>_skeleton.bonemap.json` (with the asset's id and its skeleton's id) through `rigmodules.jointclip.write_skeleton_fbx`. Existing files are versioned and checked out first. Returns the FBX and the bone map |
| `assethandlers.get_skeleton_export_path(asset)` | Where the skeleton export is, or will be |
| `assettools.check_clip_skeleton(asset_id, fbx)` | Compares a clip with the skeleton export through `rigmodules.jointclip.check_skeleton_match`. Raises `FileNotFoundError` when the asset has no skeleton export, and `ValueError` naming every joint that differs |

## Clip properties

`bmaya.asset.animproperties` is the engine's data about one exported clip, `<name>.animproperties.json`. Only the engine importer reads it. It never names a rig, a control or a RigModules node, so it stays valid when the rig changes. It is Maya-free, like the rest of `bmaya.asset`.

```json
{
    "formatVersion": 1,
    "loop": false,
    "rootMotion": false,
    "additive": "none",
    "events": [ { "name": "footstep", "frame": 12.0 } ],
    "curves": [ { "name": "footLock_l", "keys": [ [1.0, 0.0], [12.0, 1.0] ] } ]
}
```

| Key | Type | Meaning |
|---|---|---|
| `formatVersion` | int | `1` |
| `loop` | bool | Whether the clip loops. Required |
| `rootMotion` | bool | Whether the engine extracts root motion. Required |
| `additive` | string | `"none"`, `"local"` (relative to a reference pose, in each joint's space) or `"mesh"` (relative, in mesh space) |
| `events` | list | `{ "name": non-empty string, "frame": number }`. Frames are the clip's own frame numbers, the ones in its FBX |
| `curves` | list | Engine float curves, not joint animation (a foot lock, a blend weight): `{ "name": unique non-empty string, "keys": [[frame, value], ...] }`, at least one key, in strictly increasing frame order |

Unknown keys, missing keys, wrong types and non-finite numbers are all errors, and the message lists every problem found. The defaults (`AnimProperties()`) are a one-shot clip with no root motion, nothing additive and no events or curves.

| Function or class | Does |
|---|---|
| `AnimProperties`, `AnimEvent`, `AnimCurve` | Frozen dataclasses. `AnimProperties` validates on construction and has `to_json()` and `from_json(data)` |
| `get_path(fbx)` | The properties file of the clip whose FBX is `fbx` |
| `read(path)` | Raises `FileNotFoundError` and `AnimPropertiesError` (with the path in the message) |
| `write(path, properties)` | Writes through a `.tmp` file, so a failed write leaves an existing file as it was |
| `assettools.set_clip_properties(fbx, **changes)` | Changes fields of the file beside an FBX (`loop`, `root_motion`, `additive`, `events`, `curves`), starting from the defaults when it has none |

Properties are written with `indent=4` and keys in the order above, not sorted like the other asset JSON, which is a difference to know about when diffing.

## Menu tools

The **clip** submenu of the RigModules menu, and the animation tools of the **pose** submenu, call these. The full tool list is in [`tools.md`](tools.md#clip).

Before the asset's folder exists the capture tools ask for a `.fbx` file instead and write it with `own_folder=False`. Pose From Joint Pose uses a clip with one pose and can't use a clip with more than one.
