# Assets

`bmaya.asset`: where assets sit on disk and how tools find, save, load and version their files. The design and its reasons are in RigModules' `design/asset-model.md` (D29).

`bmaya.asset` is plain Python with no Maya import. It runs in Maya, mayapy, batch jobs and tools outside Maya. The Maya handlers that read and write the files are in `bmaya.maya.assethandlers`, and the menu tools that call them are in `bmaya.maya.assettools` ([`tools.md`](tools.md)).

It is built for Perforce without shared files: a routine save never touches a file someone else needs. Files in the depot change only when someone deliberately changes that asset.

## Asset ids

An asset id is the asset folder's path below `RIGGING_PROJECT_DIR`, with `\` between folders, at any depth:

```
shooter\main\characters\hero   ->   <RIGGING_PROJECT_DIR>\shooter\main\characters\hero
```

- Each folder name is letters, digits and `_` (`[A-Za-z0-9_]+`).
- Ids compare without case (`assetid.key`, `assetid.equals`) and are stored as written.
- A folder is an asset when it holds an `asset.json`. Assets never nest.
- The last token (`hero`) is the asset's **name**, and the default namespace its rigs are built into.
- The id is relative to the projects root, so it means the same asset in every workspace and branch.
- The same rules are in RigModules' `core/AssetId`, which validates the `assetId` of a built rig.

`bmaya.asset.assetid` holds the rules, and code that splits or joins an id goes through it, so a later change of separator is a change in one place.

| Function | Returns |
|---|---|
| `is_valid(id)`, `is_valid_token(token)` | Whether the id, or one folder name, follows the rules. Rig variant names follow the token rule |
| `check(id)` | The id, or raises `AssetIdError` |
| `tokens(id)`, `name(id)` | The folder names, or the last one |
| `key(id)`, `equals(a, b)` | The case-folded form ids are compared by, and the comparison |
| `to_relative_path(id)`, `from_relative_path(path)` | The id as a relative folder path and back. `from_relative_path` raises on `..` or an empty path |

## Files

```
<RIGGING_PROJECT_DIR>\shooter\main\
  project.json                    asset types and file types
  characters\hero\
    asset.json                    type and skeleton only
    skeleton\hero_skeleton.ma     shared by every variant
    controlposes\  controlanims\  exports\  sources\
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

All JSON is written with sorted keys and one item per line, so it diffs and merges cleanly. A write goes through `<file>.tmp` and `os.replace`, so a failed write never leaves half a file.

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

`Project.create(folder)` writes the full default (`DEFAULT_PROJECT`), which has every file type in the table below. An asset belongs to the nearest `project.json` above it, found by walking up from the asset folder, so a folder with its own `project.json` is a separate project.

A file type's `path` is relative to the asset folder. `{name}` is the asset's name and `{variant}` a rig variant. A path with `{variant}` is per variant, and every other path belongs to the whole asset. A per-variant path must have the form `<folder>/{variant}/...`, because the variants are found by listing that parent folder (`FileType.variant_parent`). Asking for a variant path without a variant, or an asset path with one, raises `ProjectError`.

| File type | Default path | Per variant | Folder | Handler |
|---|---|---|---|---|
| `skeleton` | `skeleton/{name}_skeleton.ma` | | | Maya scene |
| `model` | `variants/{variant}/model/{name}_{variant}_model.ma` | Yes | | Maya scene |
| `textures` | `variants/{variant}/textures` | Yes | Yes | None yet |
| `shaders` | `variants/{variant}/shaders` | Yes | Yes | None yet |
| `template` | `variants/{variant}/template.json` | Yes | | Template |
| `shapes` | `variants/{variant}/shapes.json` | Yes | | Shapes |
| `weights` | `variants/{variant}/weights` | Yes | Yes | Skin weights |
| `postops` | `variants/{variant}/postops.py` | Yes | | None yet |
| `rig` | `variants/{variant}/{name}_{variant}_rig.ma` | Yes | | Maya scene |
| `publish` | `variants/{variant}/publish` | Yes | Yes | None (see Publishes) |
| `controlposes` | `controlposes` | | Yes | Control pose |
| `controlanims` | `controlanims` | | Yes | Control anim |
| `exports` | `exports` | | Yes | Anim clip |
| `sources` | `sources` | | Yes | Source clip |

`controlposes`, `controlanims`, `exports` and `sources` belong to the asset, not a variant: control data binds to a rig's controls by markup, and a clip is skeleton data, so every variant on the asset's skeleton shares them ([`clips.md`](clips.md)).

An existing project keeps the `project.json` it was created with. A file type added to `DEFAULT_PROJECT` later is not in it until its file is edited.

### asset.json

```json
{
  "assetType": "Character",
  "formatVersion": 1,
  "skeleton": "shooter\\main\\skeletons\\biped"
}
```

| Key | Meaning |
|---|---|
| `assetType` | One of the project's `assetTypes` |
| `skeleton` | Optional. The id of the asset whose skeleton this one uses. Left out, the asset owns its skeleton |
| `formatVersion` | `1`. Any other value raises `AssetError` on read |

The id is not stored, because it is the folder's path: a copied or moved folder can't carry a stale id. `asset.json` holds only what a person decides and it changes rarely, so under Perforce it is rarely checked out. Variants and publishes are found on disk, not listed here.

## Using it

```python
from bmaya.asset import Asset, Project, Registry, publishes

Project.create(r"D:\projects\shooter\main")                  # once per project
hero = Asset.create("shooter\\main\\characters\\hero", "Character", skeleton="shooter\\main\\skeletons\\biped")

hero = Asset("shooter\\main\\characters\\hero")                  # an existing asset
hero.path("shapes", variant="game")                           # never touches the disk
hero.variants                                                 # ["cine", "game"]: folders with a template.json

registry = Registry.of(hero.project)                          # scanned on first use, once per session
registry.find(asset_type="Character")
registry.find(skeleton=hero.skeleton)                         # assets that can share hero's poses and animations
registry.latest_publish(hero.id, "game")                      # "20261108T142012Z_bmorgan" or None
registry.refresh()                                            # rescan after files change on disk
```

Reading a path never makes a folder. `Asset.create` makes the asset folder and its `asset.json`, and saving through a handler makes the file's folder.

### Asset

| Member | Does |
|---|---|
| `Asset(id, root=None)` | An asset by id. `root` defaults to `RIGGING_PROJECT_DIR`. Compares and hashes by case-folded id and root |
| `id`, `name`, `folder`, `root`, `info_path` | The id, its last token, the folder, the projects root and the `asset.json` path |
| `exists()` | Whether `asset.json` exists |
| `info` | The parsed `asset.json`, read on every access so it never goes stale. Raises `AssetError` when missing or of another format version |
| `asset_type`, `skeleton` | From `asset.json`. `skeleton` is the asset's own id unless the file names another |
| `project` | The nearest `Project` above the folder |
| `variants` | The folders under the variant parent that hold a template, sorted without case. Adding a variant adds files and edits nothing |
| `path(file_type, variant=None)` | Where a file type lives. Pure |
| `file_exists(file_type, variant=None)` | Whether that path exists |
| `Asset.create(id, asset_type, skeleton=None, root=None)` | Makes the folder and `asset.json`, and tells source control to add it. Raises when the asset exists, the type isn't in the project, or it would nest |
| `Asset.from_path(path, root=None)` | The asset a file or folder belongs to: the nearest folder at or above it with an `asset.json` |

Nesting is checked where assets are made: an asset can't sit inside another asset, can't hold one, and can't be the project folder. That keeps the registry scan from having to walk into asset folders.

## Registry

The registry indexes every asset in a project: type, skeleton (its own id unless `asset.json` names another), variants and each variant's latest publish. It answers questions about many assets without opening Maya: assets of a type, assets sharing a skeleton (whose poses and animations can be shared, and which need a batch update when that skeleton changes), and the latest publish of each variant (for an out-of-date check on imported rigs).

It is built by scanning the workspace and kept in memory, so nothing is ever written, checked out or merged, and every workspace (every branch) indexes the files it actually has. The scan stops at each asset folder, so texture and weight folders are never walked, and it skips folders with their own `project.json`.

| Member | Does |
|---|---|
| `Registry.of(project, root=None)` | The session's shared index of a project, scanned on first use. Use this, not the constructor |
| `refresh()` | Rescans. Call it after files change on disk |
| `ids()`, `get(id)` | Every id sorted, and one asset's entry (`assetType`, `skeleton`, `variants`, `latestPublish`) or `None` |
| `find(asset_type=None, skeleton=None)` | Ids matching every filter given. A skeleton matches the asset that owns it and every asset that names it |
| `latest_publish(id, variant)` | The latest publish id, or `None`. Raises `ProjectError` for an id not in the project |
| `errors` | Problems the last scan found: ids that differ only in case, and unreadable `asset.json` files |

## Publishes

```python
folder = publishes.create(hero, "game", {"pluginVersion": "0.1", "rigVersion": 3})
# write the built rig and copies of its inputs into folder, then submit it
publishes.latest(hero, "game")
```

Each publish is a new folder under the variant's `publish` folder, named by its UTC time and user (`20261108T142012Z_bmorgan`), so two people never collide, ids sort in time order and the latest is the last id. Nothing shared changes on a publish. `publish.json` holds the data passed to `create` plus `formatVersion`, `id` and `user`. Store the id in the built rig root's `publishVersion`.

| Function | Does |
|---|---|
| `make_id(user=None, when=None)` | A new id. Characters outside letters, digits and `_` in the user become `_` |
| `create(asset, variant, data=None, user=None)` | Makes the folder and `publish.json`, tells source control to add the file, returns the folder. The variant must exist. Raises `AssetError` if the id is taken |
| `list_ids(asset, variant)`, `latest(asset, variant)` | Publish ids oldest first, and the last |
| `info(asset, variant, id)` | The parsed `publish.json` |

Not built yet: the publish step that builds the rig and writes the folder's contents. Only the folder, its id and `publish.json` exist.

## Local versions

Saving through `bmaya.asset.handlers.save` first copies the old file to the versions root, mirroring its place under the projects root:

```
...\characters\hero\variants\game\shapes.json  ->  <versions root>\...\characters\hero\variants\game\shapes.v007.json
```

A folder such as `weights\` becomes `weights.v003\`. The next number is the highest existing number plus one, so deleting an old copy never reuses a number. This is the undo for a save between source control submits, and the only one without source control.

The versions root is `%LOCALAPPDATA%\bmaya\versions`, private to the machine and never submitted. Set `BMAYA_VERSIONS_DIR` to put it somewhere else, such as a synced drive. `bmaya.asset.versions.list_versions(path, root)` lists the copies as `(number, path)`.

`bmaya.core.util.fileUtils.version_file` is an older, separate scheme (a `<name>.Versions` folder beside the file) that the asset code does not use.

## Source control

Saves call `bmaya.asset.sourcecontrol`: `checkout(path)` before overwriting an existing file, `add(path)` after writing a new one. The default `SourceControl` does nothing, so everything works without source control. A Perforce adapter is a `SourceControl` subclass set with `sourcecontrol.set_current(adapter)`. None is written yet. For a folder file type the adapter handles everything under it (in Perforce terms, `<folder>/...`).

Ask the Perforce admin for `+l` (exclusive lock) on files that can't be merged, including `.ma`.

## Saving and loading

`bmaya.asset.handlers` dispatches by file type key to a registered `FileHandler`. `save(asset, file_type, variant=None, **context)` keeps a local version of the old file, checks it out (or adds it after a write), makes the folders and calls the handler with the path. `load(asset, file_type, variant=None, **context)` raises `FileNotFoundError` for a missing path and returns whatever the handler returns. `context` is the handler's own keyword arguments. A file type with no handler raises `NotImplementedError`.

The Maya handlers are registered by `bmaya.maya.assethandlers.register()`:

| File types | Handler | Context | Behaviour |
|---|---|---|---|
| `skeleton`, `model`, `rig` | `MayaSceneHandler` | `namespace=` (load) | Save renames the open scene to the path and saves it as Maya ASCII. Load imports into the asset's namespace (its name, or `namespace=`), merging into it if it exists, and returns the new nodes. Never references |
| `template` | `RigTemplateHandler` | `source=` (save) | Save copies the template file passed as `source=`, and fails unless its `rigName` is the variant. Load returns the template's path |
| `shapes` | `RigShapesHandler` | `rig_root=` | RigModules `saveRigControlShapes` and `loadRigControlShapes` |
| `weights` | `RigSkinWeightsHandler` | `namespace=` | One RigModules weight file per skinned mesh in the namespace, named after the mesh (`box_geo.json`). Save fails on a skinned mesh without a `meshId`, and removes a file left from a mesh's old name. Load matches each file to a mesh by the `meshId` inside it, never by name, skips a file whose mesh isn't in the scene with a warning, fails if two files name one `meshId`, and is one undo step |
| `controlposes` | `ControlPoseHandler` | `name=`, `scope=` | `<name>.json` in the folder. `cmds.saveRigPose` and `loadRigPose` |
| `controlanims` | `ControlAnimHandler` | `name=`, `scope=`, `start_frame=`, `end_frame=` (save), `offset=`, `mirror=` (load) | `<name>.json` in the folder. `cmds.saveRigAnimation` and `loadRigAnimation` |
| `exports` | `AnimClipHandler` | see [`clips.md`](clips.md) | One FBX clip per name, in a folder of its own |
| `sources` | `SourceClipHandler` | see [`clips.md`](clips.md) | FBX files from other tools. Load only: save raises |

`scope` is a rig root, or controls of one rig. A pose or animation name follows `CLIP_NAME`: it starts with a letter or digit and holds letters, digits, `_`, `-` and spaces, because it becomes a file name.

```python
import maya.cmds as cmds

from bmaya.asset import Asset, handlers
from bmaya.maya import assethandlers

assethandlers.register()                                      # once per session
hero = Asset("shooter\\main\\characters\\hero")
handlers.load(hero, "skeleton")
handlers.save(hero, "shapes", variant="game", rig_root="hero:rigRootModule1")
handlers.save(hero, "weights", variant="game", namespace="hero")
assethandlers.save_anim_clip(hero, "walk", rig_root="hero:rigRootModule1", start_frame=1, end_frame=48)
clip = handlers.load(hero, "exports", name="walk")
cmds.animateRigFromJointClip("hero:rigRootModule1", jointClip=clip.joint_clip)
```

A pose, an animation or a clip should be saved through `assethandlers.save_control_file` or `assethandlers.save_anim_clip`, not `handlers.save`. `handlers.save` versions the path it is given, which for a folder type is the whole folder. The two helpers version only the one file (or the one clip's FBX), and tell source control about it.

Textures, shaders and postops have no handler yet. The weight, shape and rig tools read and write through these handlers, and the tools that sit on top are in [`tools.md`](tools.md).

## Building a rig from an asset

`bmaya.maya.assettools.build_rig(asset_id, variant, namespace=None)` is the one place the asset model and RigModules meet. It:

1. Loads the variant's template path through the `template` handler.
2. Refuses a namespace that already holds a rig (`rigmodules.query.get_rigs`). Each build gets a namespace of its own, because variants share one skeleton and a second variant in the namespace would need the joints already there.
3. Imports the **skeleton asset's** skeleton (`asset.skeleton`, which may be another asset) into the namespace, and collects its joints.
4. Builds: `cmds.createRigFromTemplate(*joints, template=..., asset=asset.id, namespace=...)`.
5. Loads the variant's files that exist: the shape file, then the model (imported into the same namespace, added to the rig's display layers with `rigmodules.displaylayers.add_meshes` and parented under its mesh group with `rigmodules.groups.parent_meshes`), then, with a model, the skin weights.
6. Clears the selection and returns the rig root.

A built rig carries its own asset id and variant (the rig root's `assetId` and `rigName`), which the other tools read through `rigmodules.query`. Nothing parses node names.

## Tests

`tests\asset\run.bat` runs the plain Python tests, then the Maya handler and tool tests in mayapy ([`../tests/README.md`](../tests/README.md)).
