# Asset Layout

How assets sit on disk and how tools find their files with `bmaya.asset`. The design and its reasons are in RigModules' `design/asset-model.md` (decision D29).

`bmaya.asset` is plain Python, with no Maya import. It runs in Maya, mayapy, batch jobs and tools outside Maya. The Maya tools built on it are in `bmaya.maya.assettools` (see "Tools" below, and the menu in [Mayadev Env Setup](Mayadev Env Setup.md)).

It is built for Perforce without shared files: a routine save never touches a file someone else needs. Files in the depot change only when someone deliberately changes that asset.

## Asset ids

An asset id is the asset folder's path below `RIGGING_PROJECT_DIR`, with `|` between folders, at any depth:

```
shooter|main|characters|hero   ->   <RIGGING_PROJECT_DIR>\shooter\main\characters\hero
```

- Each folder name is letters, digits and `_`.
- Ids compare without case and are stored as written.
- A folder is an asset when it holds an `asset.json`. Assets never nest.
- The last token (`hero`) is the asset's name, and the default namespace its rigs are built into.
- The id is relative to the projects root, so it means the same asset in every workspace and branch.

`bmaya.asset.assetid` holds these rules. Code that splits or joins ids goes through it.

## Files

```
<RIGGING_PROJECT_DIR>\shooter\main\
  project.json                    asset types and file types
  characters\hero\
    asset.json                    type and skeleton only
    skeleton\hero_skeleton.ma     shared by every variant
    poses\  anims\
    variants\game\                a variant: a folder with a template.json
      template.json  shapes.json  postops.py
      model\hero_game_model.ma
      textures\  shaders\  weights\
      hero_game_rig.ma            the built rig
      publish\20261108T142012Z_bmorgan\
        publish.json              one folder per publish, never edited
```

| What | Changes when |
|---|---|
| `project.json` | Someone changes the project's asset types or file layout |
| `asset.json` | Someone changes the asset's type or skeleton |
| A variant | Added by adding its folder and `template.json` |
| A publish | Never: each publish adds a new folder |
| The registry | Never written: it lives in memory |
| Local versions | Never submitted: they live outside the workspace |

All JSON is written with sorted keys and one item per line, so it diffs and merges cleanly.

### project.json

```json
{
  "assetTypes": ["Prop", "Character", "Vehicle", "Head", "Weapon", "VFX", "Light", "Environment", "Skeleton", "Other"],
  "fileTypes": {
    "shapes": { "path": "variants/{variant}/shapes.json" },
    "weights": { "folder": true, "path": "variants/{variant}/weights" }
  },
  "formatVersion": 1
}
```

`Project.create(folder)` writes the full default, which has every file type above. A file type's `path` is relative to the asset folder. `{name}` is the asset's name. A path with `{variant}` is per variant, and every other path belongs to the whole asset. An asset belongs to the nearest `project.json` above it.

### asset.json

```json
{
  "assetType": "Character",
  "formatVersion": 1,
  "skeleton": "shooter|main|skeletons|biped"
}
```

| Key | Meaning |
|---|---|
| `assetType` | One of the project's `assetTypes` |
| `skeleton` | Optional. The id of the asset whose skeleton this one uses. Left out, the asset owns its skeleton |

The id is not stored, because it is the folder's path.

## Using it

```python
from bmaya.asset import Asset, Project, Registry, publishes

Project.create(r"D:\projects\shooter\main")                  # once per project
hero = Asset.create("shooter|main|characters|hero", "Character", skeleton="shooter|main|skeletons|biped")

hero = Asset("shooter|main|characters|hero")                  # an existing asset
hero.path("shapes", variant="game")                           # never touches the disk
hero.variants                                                 # ["cine", "game"]: folders with a template.json

registry = Registry.of(hero.project)                          # scanned on first use, once per session
registry.find(asset_type="Character")
registry.find(skeleton=hero.skeleton)                         # assets that can share hero's poses and anims
registry.latest_publish(hero.id, "game")                      # "20261108T142012Z_bmorgan" or None
registry.refresh()                                            # rescan after files change on disk
```

Reading a path never makes a folder. `Asset.create` makes the asset folder, and saving through a handler makes the file's folder.

## Registry

The registry indexes every asset in the project: type, skeleton (its own id unless `asset.json` names another), variants and each variant's latest publish. It is built by scanning the workspace and kept in memory, so nothing is ever written, checked out or merged. The scan stops at each asset folder and skips folders with their own `project.json`. `registry.errors` lists ids that differ only in case and unreadable `asset.json` files.

In `find`, a skeleton matches the asset that owns it and every asset that names it.

## Publishes

```python
folder = publishes.create(hero, "game", {"pluginVersion": "0.1", "rigVersion": 3})
# write the built rig and copies of its inputs into folder, then submit it
publishes.latest(hero, "game")
```

Each publish is a new folder named by its UTC time and user, so two people never collide and the latest is the last id. Store the id in the built rig root's `publishVersion`. The publish step that builds the rig isn't written yet.

## Local versions

Saving through `bmaya.asset.handlers.save` first copies the old file to the versions root, mirroring its place under the projects root: `...\characters\hero\variants\game\shapes.v007.json`. A folder such as `weights\` becomes `weights.v003\`. The next number is the highest existing number plus one.

The versions root is `%LOCALAPPDATA%\bmaya\versions`, private to the machine. Set `BMAYA_VERSIONS_DIR` to put it somewhere else, such as a synced drive. `bmaya.asset.versions.list_versions(path, root)` lists the copies.

## Source control

Saves call `bmaya.asset.sourcecontrol`: `checkout(path)` before overwriting an existing file, `add(path)` after writing a new one. The default does nothing, so everything works without source control. A Perforce adapter is a `SourceControl` subclass set with `sourcecontrol.set_current(adapter)`. None is written yet.

Ask the Perforce admin for `+l` (exclusive lock) on files that can't be merged, including `.ma`.

## Saving and loading

Where a file lives is kept apart from how it is read. `bmaya.asset.handlers` dispatches by file type to a registered `FileHandler`, whose `save` and `load` raise `NotImplementedError` until written. The Maya handlers are in `bmaya.maya.assethandlers`:

| File types | Handler |
|---|---|
| `skeleton`, `model`, `rig` | Save renames and saves the open scene. Load imports into the asset's namespace (or `namespace=`), merging into it if it exists. Never references |
| `shapes` | RigModules `saveRigControlShapes` / `loadRigControlShapes`. Pass `rig_root=` |
| `weights` | One RigModules weight file per skinned mesh in `namespace=`, named after the mesh (`box_geo.json`). Save fails on a skinned mesh without a `meshId`, and removes a file left from a mesh's old name. Load matches each file to a mesh by the `meshId` inside it, never by name, skips a file whose mesh isn't in the scene with a warning, and is one undo step |
| `template` | Save copies the template file passed as `source=`, and fails unless its `rigName` is the variant. Load returns the template's path |
| `anims` | One clip per `name=` in the asset's `anims` folder: `<name>.usd`, a UsdSkel file, written and read through `rigmodules.jointclip`, plus an optional `<name>.rigdata.json` sidecar beside it. Save takes `joint_clip=` (a RigModules JointClip file) or `rig_root=` with `start_frame=` and `end_frame=` (captures the rig's export joints), and `sidecar=` to copy a sidecar in. A save without `sidecar=` removes the sidecar the old clip had, because it described the old animation. Load returns an `AnimClip` (`name`, `usd`, `joint_clip`, `sidecar`): `joint_clip` is a temporary file for `cmds.animateRigFromJointClip(jointClip=...)`. Use `assethandlers.save_anim_clip(asset, name, ...)` to save: it versions only that clip's files, where `handlers.save` copies the whole `anims` folder |

```python
from bmaya.asset import Asset, handlers
from bmaya.maya import assethandlers

assethandlers.register()                                      # once per session
hero = Asset("shooter|main|characters|hero")
handlers.load(hero, "skeleton")
handlers.save(hero, "shapes", variant="game", rig_root="hero:rigRootModule1")
handlers.save(hero, "weights", variant="game", namespace="hero")
assethandlers.save_anim_clip(hero, "walk", rig_root="hero:rigRootModule1", start_frame=1, end_frame=48)
clip = handlers.load(hero, "anims", name="walk")
cmds.animateRigFromJointClip("hero:rigRootModule1", jointClip=clip.joint_clip, sidecar=clip.sidecar)
```

Textures, shaders, postops and poses have no handler yet. Poses are saved by `bmaya.maya.assettools.save_pose`.

## Tools

`bmaya.maya.assettools` does the common steps for a RigModules rig. It finds a built rig's asset id and variant through RigModules' `rigmodules.query`, never by reading node names.

```python
import bmaya.maya.assettools

bmaya.maya.assettools.new_variant("shooter|main|characters|hero", r"C:\rigs\Human.json")   # variant "Human"
bmaya.maya.assettools.save_skeleton("shooter|main|characters|hero")              # the open scene
bmaya.maya.assettools.save_model("shooter|main|characters|hero", "Human")        # the open scene, meshes only
rig_root = bmaya.maya.assettools.build_rig("shooter|main|characters|hero", "Human")
bmaya.maya.assettools.save_control_shapes(rig_root)                                # variants/Human/shapes.json
bmaya.maya.assettools.save_skin_weights(rig_root)                                  # variants/Human/weights/*.json
bmaya.maya.assettools.save_rig(rig_root)                                           # variants/Human/hero_Human.ma
```

- A variant is added by copying its template in. The template's `rigName` names it.
- `build_rig` imports the skeleton into the asset's namespace and builds there. Then it loads what the variant has: its shape file, its model (imported into the same namespace) and, with the model, its weights. A namespace that already holds a rig is refused, so build a second variant into a new scene or another namespace.
- Weights need each skinned mesh's `meshId`, which lives in the model file. Mark the meshes for skinning (`mark_meshes_for_skinning`, RigModules `setRigMeshId`) in the model scene, before `save_model`, so every build imports meshes that already carry their ids.
- The shape, weight and rig saves fall back to a file or folder dialog only while the rig's asset folder doesn't exist.
- The RigModules menu's clip tools (Capture Joint Clip, Capture Joint Pose, Pose From Joint Pose, Animate From Joint Clip) use USD clips. Capture asks for a clip name and saves it in the asset's `anims` folder (`save_joint_clip` for scripts), or asks for a `.usd` file while the asset folder doesn't exist. Pose and Animate open a file dialog in `anims` and pass the clip's `.rigdata.json` sidecar to the command when it has one. A clip with more than one pose can't be used by Pose From Joint Pose.

## Tests

`tests\asset\run.bat` runs the plain Python tests, then the Maya handler and tool tests in mayapy. The tool tests also need RigModules' `rigmodules` package on the path (`RigModules.mod`). Set `RIGMODULES_PLUGIN` to a RigModules `.mll` for the Maya tests, or they skip. Copy the `.mll` first if a Maya session has it loaded.
