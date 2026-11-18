# Assets

`bmaya.core.asset`: where assets sit on disk and how tools find, save, load and version their files. The design and its reasons are in RigModules' `design/asset-model.md` (D29) and `design/rigs-and-looks.md` (D54): an asset holds **skeletons**, **rigs** and **looks**.

`bmaya.core.asset` is plain Python with no Maya import. It runs in Maya, mayapy, batch jobs and tools outside Maya. The Maya handlers that read and write the files are in `bmaya.maya.assethandlers`, and the menu tools that call them are in `bmaya.maya.assettools` ([`tools.md`](tools.md)).

It is built for Perforce without shared files: a routine save never touches a file someone else needs. Files in the depot change only when someone deliberately changes that asset.

## Asset ids

An asset id is the asset folder's path below `RIGGING_PROJECT_DIR`, with `\` between folders, at any depth:

```
shooter\main\characters\hero   ->   <RIGGING_PROJECT_DIR>\shooter\main\characters\hero
```

- Each folder name is lowercase letters, digits and `_` (`[a-z0-9_]+`).
- Ids are lowercase only: uppercase is rejected, not converted, so two ids never differ only in case and they compare with `==` (RigModules D54).
- A folder is an asset when it holds an `asset.json`. Assets never nest.
- The last token (`hero`) is the asset's **name**. A rig is built into `{name}_{rig}` (`hero_game`) by default: a namespace holds one rig (RigModules D54).
- The id is relative to the projects root, so it means the same asset in every workspace and branch.
- The same rules are in RigModules' `core/AssetId`, which validates the `assetId` of a built rig.

`bmaya.core.asset.assetid` holds the rules, and code that splits or joins an id goes through it, so a later change of separator is a change in one place.

| Function | Returns |
|---|---|
| `is_valid(id)`, `is_valid_token(token)` | Whether the id, or one folder name, follows the rules. Skeleton, rig and look names follow the token rule |
| `check(id)` | The id, or raises `AssetIdError` |
| `tokens(id)`, `name(id)` | The folder names, or the last one |
| `to_relative_path(id)`, `from_relative_path(path)` | The id as a relative folder path and back. `from_relative_path` raises on `..` or an empty path |

## Files

```
<RIGGING_PROJECT_DIR>\shooter\main\
  project.json                    asset types and file types
  characters\hero\
    asset.json                    the asset's type only
    skeletons\default\
      skeleton.json               the skeleton: its only stored form, no scene file
      exports\                    animation FBX clips and the skeleton export, shared by every rig of the skeleton
    rigs\game\                    a rig: a template built on one skeleton
      rig.json                    the skeleton it is built on, the rig it was copied from, the rig it attaches to
      template.json  shapes.json  postops.py  hero_game_rig.ma
      controlposes\  controlanims\   the rig's library (control markup is unique per rig)
      publish\20261108T142012Z_bmorgan\
        publish.json              one folder per publish, never edited
    looks\default\                a look: meshes and skin weights a rig of its skeleton wears
      look.json                   the skeletons its meshes bind to
      model\hero_default_model.ma  meshes only: no skinning, no history, no joints
      textures\  shaders\  weights\  publish\
    sources\
```

| What | Changes when |
|---|---|
| `project.json` | Someone changes the project's asset types or file layout |
| `asset.json` | Someone changes the asset's type |
| A skeleton, rig or look | Added by adding its folder and its `skeleton.json`, `rig.json` or `look.json` |
| A publish | Never: each publish adds a new folder |
| The registry | Never written: it lives in memory |
| Local versions | Never submitted: they live outside the workspace |

All JSON is written with sorted keys and one item per line, so it diffs and merges cleanly. A write goes through `<file>.tmp` and `os.replace`, so a failed write never leaves half a file.

### project.json

```json
{
  "assetTypes": ["Prop", "Character", "Vehicle", "Head", "Weapon", "VFX", "Light", "Environment", "Skeleton", "Other"],
  "fileTypes": {
    "shapes": { "path": "rigs/{rig}/shapes.json" },
    "weights": { "folder": true, "path": "looks/{look}/weights" }
  },
  "rig": { "regions": ["lowerBody", "upperBody", "head", "hands"] },
  "library": { "statuses": ["scratch", "review", "final"] },
  "formatVersion": 3
}
```

`Project.create(folder)` writes the full default (`DEFAULT_PROJECT`), which has every file type in the table below. `rig.regions` and `library.statuses` are the vocabularies of the pose and animation library ([Library](#library)): `Project.rig_regions` and `Project.library_statuses` read them, and an absent key is an empty list. An asset belongs to the nearest `project.json` above it, found by walking up from the asset folder, so a folder with its own `project.json` is a separate project.

A file type's `path` is relative to the asset folder. `{name}` is the asset's name. A path names at most one **owner** as a field: `{skeleton}`, `{rig}` or `{look}`, and the file belongs to that skeleton, rig or look (`FileType.owner`). A path with none belongs to the asset. An owned path must have the form `<folder>/{owner}/...`, because owners are found by listing that parent folder (`FileType.owner_parent`). Asking for an owned path without an owner name, or an asset path with one, raises `ProjectError`, and so does a path with two owners, an unknown field, or the old `{variant}` (the error names the file type and its path, and the project fails to load).

| File type | Default path | Owner | Folder | Handler |
|---|---|---|---|---|
| `skeleton` | `skeletons/{skeleton}/skeleton.json` | skeleton | | Skeleton file |
| `exports` | `skeletons/{skeleton}/exports` | skeleton | Yes | Anim clip |
| `riginfo` | `rigs/{rig}/rig.json` | rig | | None (`Asset.rig`) |
| `template` | `rigs/{rig}/template.json` | rig | | Template |
| `shapes` | `rigs/{rig}/shapes.json` | rig | | Shapes |
| `postops` | `rigs/{rig}/postops.py` | rig | | None yet |
| `rig` | `rigs/{rig}/{name}_{rig}_rig.ma` | rig | | Maya scene |
| `rigpublish` | `rigs/{rig}/publish` | rig | Yes | None (see Publishes) |
| `controlposes` | `rigs/{rig}/controlposes` | rig | Yes | Control pose |
| `controlanims` | `rigs/{rig}/controlanims` | rig | Yes | Control anim |
| `lookinfo` | `looks/{look}/look.json` | look | | None (`Asset.look`) |
| `model` | `looks/{look}/model/{name}_{look}_model.ma` | look | | Model (meshes only) |
| `textures` | `looks/{look}/textures` | look | Yes | None yet |
| `shaders` | `looks/{look}/shaders` | look | Yes | None yet |
| `weights` | `looks/{look}/weights` | look | Yes | Skin weights |
| `lookpublish` | `looks/{look}/publish` | look | Yes | None (see Publishes) |
| `sources` | `sources` | | Yes | Source clip |

Control data binds to a rig's controls by markup, which is unique per rig, so poses and animations are a rig's. A clip is skeleton data, so every rig on a skeleton shares its `exports` ([`clips.md`](clips.md)).

An older `project.json` updates itself. `formatVersion` is 3. When a `Project` loads a file with an older version, it runs the steps in `PROJECT_UPDATES` in order, in memory, and then writes the file back at the current version (`update_project_data`). Version 1 to 2 adds the library file types and the `rig` and `library` vocabularies, only where they are missing. Version 2 to 3 (RigModules D54) moves every default path that was per variant under `rigs/{rig}` or `looks/{look}`, makes `skeleton` the `skeleton.json` and moves `exports`, `controlposes` and `controlanims` under their owner, splits `publish` into `rigpublish` and `lookpublish`, and adds `riginfo` and `lookinfo`. Only a path that still equals its version 2 default is replaced, so a studio's own edits stay. A path a studio edited that still uses `{variant}` is left alone and fails the load by name: where it should go is the studio's call. A file that can't be written back (read-only in source control) still loads, updated in memory, and is tried again on the next load. A `formatVersion` that is not a whole number from 1, or is newer than this mayadev reads, raises `ProjectError` naming the file.

To change the format, bump `FORMAT_VERSION`, add the step as `PROJECT_UPDATES[old_version]` and add the new keys to `DEFAULT_PROJECT`. A step spells out its values and never reads `DEFAULT_PROJECT`, and it is not edited after it ships.

### asset.json

```json
{
  "assetType": "Character",
  "formatVersion": 2
}
```

| Key | Meaning |
|---|---|
| `assetType` | One of the project's `assetTypes` |
| `formatVersion` | `2`. A version 1 file (which also named a `skeleton`) is updated in memory without it and written back. Any other value raises `AssetError` on read |

The id is not stored, because it is the folder's path: a copied or moved folder can't carry a stale id. `asset.json` holds only what a person decides and it changes rarely, so under Perforce it is rarely checked out. Skeletons, rigs, looks and publishes are found on disk, not listed here.

### rig.json and look.json

A template is shared between assets, so it can't say what skeleton it is built on. Each rig and each look has a small file of its own (`bmaya.core.asset.records`):

```json
// rigs/body/rig.json
{ "formatVersion": 1, "skeleton": "default" }
// rigs/body_cine/rig.json, a copy of the body rig on a skeleton of another asset
{ "formatVersion": 1, "skeleton": { "asset": "shooter\\main\\characters\\npc_male", "name": "default" }, "source": "body" }
// rigs/face/rig.json, an attachment: it follows the body rig (RigModules D55)
{ "formatVersion": 1, "skeleton": "face", "parent": "body" }
// looks/winter/look.json
{ "formatVersion": 1, "skeletons": ["default"] }
```

A skeleton or rig in the same asset is a plain name. One in another asset is an object with two fields, never a joined string. `source` is the rig this one was copied from: the library lists the source's poses and animations beside the copy's own, one level only. `parent` is the rig this one attaches to, a face or a prop that follows a body: `build_rig` builds the parent first and passes it to RigModules as `parentRig`. It is the same reference form as `source` (a plain name, or `asset` and `rig` for a rig of another asset), it is optional, and it needs no format version, so every older file reads as before. A rig can be both a copy and an attachment. The parent needn't exist when the rig is added, like a skeleton. A rig can't attach to itself, and following parents must end, across assets too. A look names every skeleton its meshes bind to, and a rig of any of them can wear it. `SkeletonRef(name, asset=None)` and `RigRef(rig, asset=None)` are the references, `RigRecord` and `LookRecord` the files. A look-only asset (crowd looks on a shared skeleton) holds `looks/` and nothing else.

## Using it

```python
from bmaya.core.asset import Asset, Project, Registry, RigRef, SkeletonRef, publishes

Project.create(r"D:\projects\shooter\main")                  # once per project
hero = Asset.create("shooter\\main\\characters\\hero", "Character")
hero.add_rig("game", SkeletonRef("default"))                  # rigs/game/rig.json
hero.add_look("default", [SkeletonRef("default")])            # looks/default/look.json

hero = Asset("shooter\\main\\characters\\hero")              # an existing asset
hero.path("shapes", "game")                                   # rigs/game/shapes.json. Never touches the disk
hero.path("weights", "default")                               # looks/default/weights
hero.skeletons, hero.rigs, hero.looks                         # ["default"], ["game"], ["default"]: folders with their file
hero.skeleton_of("game")                                      # (the asset that holds the rig's skeleton, "default")

registry = Registry.of(hero.project)                          # scanned on first use, once per session
registry.find(asset_type="Character")
registry.find(skeleton=(hero.id, "default"))                  # assets with a rig or look on hero's skeleton
registry.latest_publish(hero.id, "rig", "game")               # "20261108T142012Z_bmorgan" or None
registry.refresh()                                            # rescan after files change on disk
```

Reading a path never makes a folder. `Asset.create` makes the asset folder and its `asset.json`, `add_rig` and `add_look` make their folder and file, and saving through a handler makes the file's folder.

### Asset

| Member | Does |
|---|---|
| `Asset(id, root=None)` | An asset by id. `root` defaults to `RIGGING_PROJECT_DIR`. Compares and hashes by id and root |
| `id`, `name`, `folder`, `root`, `info_path` | The id, its last token, the folder, the projects root and the `asset.json` path |
| `exists()` | Whether `asset.json` exists |
| `info` | The parsed `asset.json`, read on every access so it never goes stale. Raises `AssetError` when missing or of another format version |
| `asset_type` | From `asset.json` |
| `project` | The nearest `Project` above the folder |
| `skeletons`, `rigs`, `looks` | The names of the folders that hold a `skeleton.json`, `rig.json` or `look.json`, sorted. Adding one adds files and edits nothing |
| `all_looks()` | Every look as `AssetLook(name, local)`, including looks that source control has but the workspace doesn't (`local` False, listed by name only). The local scan when source control can't list, with a warning. `looks` stays the local scan |
| `sync_look(name)` | Syncs a look that isn't local through source control. Raises `AssetError` when the sync fails or leaves no `look.json` |
| `path(file_type, owner=None)` | Where a file type lives. `owner` is the skeleton, rig or look name for a file type that belongs to one. Pure |
| `file_exists(file_type, owner=None)` | Whether that path exists |
| `rig(name)`, `look(name)` | The parsed `rig.json` or `look.json` (`RigRecord`, `LookRecord`). Raise `AssetError` naming what the asset has |
| `resolve_skeleton(ref)`, `resolve_rig(ref)` | The asset that holds a skeleton or rig this asset names, and its name. Pure |
| `skeleton_of(rig)` | The skeleton a rig is built on: the asset that holds it, and its name |
| `look_fits(look, rig)` | Whether the look names the rig's skeleton |
| `Asset.create(id, asset_type, root=None)` | Makes the folder and `asset.json`, and tells source control to add it. Raises when the asset exists, the type isn't in the project, or it would nest |
| `add_rig(name, skeleton, source=None, parent=None)`, `add_look(name, skeletons)` | Write a new `rig.json` or `look.json` and tell source control. Raise when it exists. The skeleton and the parent needn't exist yet. A parent that would make a loop raises `AssetError` and nothing is written |
| `parent_of(rig)`, `check_parent(name, parent)` | The `(Asset, rig name)` a rig attaches to, or `None`. `check_parent` raises when a rig called `name` can't attach to `parent` (it is its own ancestor), before anything is written |
| `Asset.from_path(path, root=None)` | The asset a file or folder belongs to: the nearest folder at or above it with an `asset.json` |

Nesting is checked where assets are made: an asset can't sit inside another asset, can't hold one, and can't be the project folder. That keeps the registry scan from having to walk into asset folders.

## Registry

The registry indexes every asset in a project: type, skeletons, each rig (its skeleton, its source, its latest publish) and each look (its skeletons, its latest publish). It answers questions about many assets without opening Maya: assets of a type, assets with a rig or look on one skeleton (which need a batch update when that skeleton changes), and the latest publish of each rig and look (for an out-of-date check on imported rigs).

It is built by scanning the workspace and kept in memory, so nothing is ever written, checked out or merged, and every workspace (every branch) indexes the files it actually has. The scan stops at each asset folder, so texture and weight folders are never walked, and it skips folders with their own `project.json`.

| Member | Does |
|---|---|
| `Registry.of(project, root=None)` | The session's shared index of a project, scanned on first use. Use this, not the constructor |
| `refresh()` | Rescans. Call it after files change on disk |
| `ids()`, `get(id)` | Every id sorted, and one asset's entry (`assetType`, `skeletons`, `rigs`, `looks`) or `None` |
| `find(asset_type=None, skeleton=None)` | Ids matching every filter given. `skeleton` is `(the id of the asset that holds it, its name)` and matches that asset and every asset with a rig or look on it |
| `latest_publish(id, kind, name)` | The latest publish id of a rig or look (`kind` is `"rig"` or `"look"`), or `None`. Raises `ProjectError` for an id not in the project |
| `errors` | Problems the last scan found: folders whose path is not a valid id, and unreadable `asset.json` files |

## Publishes

```python
folder = publishes.create(hero, "rig", "game", {"pluginVersion": "0.1", "rigVersion": 3})
# write the built rig and copies of its inputs into folder, then submit it
publishes.latest(hero, "rig", "game")
publishes.create(hero, "look", "winter")                      # a look is published separately
```

A rig and a look are published separately, each in a new folder under its own `publish` folder, named by its UTC time and user (`20261108T142012Z_bmorgan`), so two people never collide, ids sort in time order and the latest is the last id. Nothing shared changes on a publish. `publish.json` holds the data passed to `create` plus `formatVersion`, `id` and `user`. Store the id in the built rig root's `publishVersion`.

| Function | Does |
|---|---|
| `make_id(user=None, when=None)` | A new id. Characters outside letters, digits and `_` in the user become `_` |
| `create(asset, kind, name, data=None, user=None)` | Makes the folder and `publish.json`, tells source control to add the file, returns the folder. `kind` is `"rig"` or `"look"`, and the asset must have it. Raises `AssetError` if the id is taken |
| `list_ids(asset, kind, name)`, `latest(asset, kind, name)` | Publish ids oldest first, and the last |
| `info(asset, kind, name, id)` | The parsed `publish.json` |

Not built yet: the publish step that builds the rig and writes the folder's contents. Only the folder, its id and `publish.json` exist.

## Local versions

Saving through `bmaya.core.asset.handlers.save` first copies the old file to the versions root, mirroring its place under the projects root:

```
...\characters\hero\rigs\game\shapes.json  ->  <versions root>\...\characters\hero\rigs\game\shapes.v007.json
```

A folder such as `weights\` becomes `weights.v003\`. The next number is the highest existing number plus one, so deleting an old copy never reuses a number. This is the undo for a save between source control submits, and the only one without source control.

The versions root is `%LOCALAPPDATA%\bmaya\versions`, private to the machine and never submitted. Set `BMAYA_VERSIONS_DIR` to put it somewhere else, such as a synced drive. `bmaya.core.asset.versions.list_versions(path, root)` lists the copies as `(number, path)`.

`bmaya.core.util.fileUtils.version_file` is an older, separate scheme (a `<name>.Versions` folder beside the file) that the asset code does not use.

## Source control

Saves call `bmaya.core.asset.sourcecontrol`: `checkout(path)` before overwriting an existing file, `add(path)` after writing a new one. The default `SourceControl` does nothing, so everything works without source control. A Perforce adapter is a `SourceControl` subclass set with `sourcecontrol.set_current(adapter)`. None is written yet. For a folder file type the adapter handles everything under it (in Perforce terms, `<folder>/...`).

Two more calls serve looks that exist in the depot but not in the workspace (RigModules D54 phase 6). `list_folders(path)` returns the child folder names whether or not they are synced, and `None` for the default adapter, which means "scan the disk". `sync(path)` brings a folder into the workspace and raises when it can't. `Asset.all_looks()` uses the first (a failure falls back to the local scan with a warning, so a server that is down never empties the list) and `assettools.apply_look` the second: choosing a look that isn't local syncs it, checks that its `look.json` names the rig's skeleton, then swaps it in. A failed sync or a look that doesn't fit changes nothing in the scene.

Ask the Perforce admin for `+l` (exclusive lock) on files that can't be merged, including `.ma`.

## Saving and loading

`bmaya.core.asset.handlers` dispatches by file type key to a registered `FileHandler`. `save(asset, file_type, owner=None, **context)` keeps a local version of the old file, checks it out (or adds it after a write), makes the folders and calls the handler with the path. `load(asset, file_type, owner=None, **context)` raises `FileNotFoundError` for a missing path and returns whatever the handler returns. `owner` is the skeleton, rig or look the file belongs to, and the handler gets it as `owner=`. `context` is the handler's own keyword arguments. A file type with no handler raises `NotImplementedError`.

The Maya handlers are registered by `bmaya.maya.assethandlers.register()`:

| File types | Handler | Context | Behaviour |
|---|---|---|---|
| `skeleton` | `RigSkeletonHandler` | `joints=` (save), `namespace=` (load) | A skeleton is its `skeleton.json` and nothing else (RigModules D54). Save is `cmds.saveRigSkeleton` on `joints`. Load is `cmds.loadRigSkeleton`: it creates the joints at rest and marked in the namespace (the current one when left out) and returns them. It fails when a name is taken, where a scene import would merge |
| `rig` | `MayaSceneHandler` | `namespace=` (load) | Save renames the open scene to the path and saves it as Maya ASCII. Load imports into a namespace (`namespace=`, else the asset's name), merging into it if it exists, and returns the new nodes. Never references |
| `model` | `ModelHandler` | `meshes=` (save), `namespace=` (load) | A model file is only meshes: no joints, no skinCluster, no history. Save exports `meshes` (every visible mesh when left out), each from its undeformed shape under its own short name at the top level, with its `meshId` and a copy of its materials, and leaves the scene saved, renamed and posed as it was. It fails when two meshes share a short name. Load imports like a scene |
| `template` | `RigTemplateHandler` | `source=` (save) | Save writes the template file passed as `source=` into the rig's folder with its `rigName` set to the rig's name, because templates are shared between assets. It is written again as JSON: key order and indent are kept, other hand formatting is not. Load returns the template's path |
| `shapes` | `RigShapesHandler` | `rig_root=` | RigModules `saveRigControlShapes` and `loadRigControlShapes` |
| `weights` | `RigSkinWeightsHandler` | `namespace=` | One RigModules weight file per skinned mesh in the namespace, named after the mesh (`box_geo.json`). Save fails on a skinned mesh without a `meshId`, and removes a file left from a mesh's old name. Load matches each file to a mesh by the `meshId` inside it, never by name, skips a file whose mesh isn't in the scene with a warning, fails if two files name one `meshId`, and is one undo step |
| `controlposes` | `ControlPoseHandler` | `name=`, `scope=`, `meta=` (save), `mirror=` (load) | `<name>.controlpose.json` in the folder. `cmds.saveRigPose` and `loadRigPose`. A legacy `<name>.json` still loads |
| `controlanims` | `ControlAnimHandler` | `name=`, `scope=`, `start_frame=`, `end_frame=`, `meta=` (save), `offset=`, `mirror=` (load) | `<name>.controlanim.json` in the folder. `cmds.saveRigAnimation` and `loadRigAnimation`. A legacy `<name>.json` still loads |
| `exports` | `AnimClipHandler` | see [`clips.md`](clips.md) | One FBX clip per name, in a folder of its own |
| `sources` | `SourceClipHandler` | see [`clips.md`](clips.md) | FBX files from other tools. Load only: save raises |

`scope` is a rig root, or controls of one rig. A pose or animation name follows `library.NAME_RULE` (`CLIP_NAME` in `assethandlers`): it starts with a letter or digit and holds letters, digits, `_`, `-` and spaces, because it becomes a file name. `meta` is a dict for the file's `meta` block (`author`, `tags`, `description`, ...), and the rig fills the rest ([Library](#library)). `assethandlers.save_control_file(..., folder=)` saves to another folder than the asset's: it versions the old file there but never touches source control.

```python
import maya.cmds as cmds

from bmaya.core.asset import Asset, handlers
from bmaya.maya import assethandlers

assethandlers.register()                                      # once per session
hero = Asset("shooter\\main\\characters\\hero")
handlers.load(hero, "skeleton", "default", namespace="hero_game")
handlers.save(hero, "shapes", "game", rig_root="hero_game:rigRootModule1")
handlers.save(hero, "weights", "default", namespace="hero_game")
assethandlers.save_anim_clip(hero, "game", "walk", rig_root="hero_game:rigRootModule1", start_frame=1, end_frame=48)
clip = handlers.load(hero, "exports", "default", name="walk")
cmds.animateRigFromJointClip("hero_game:rigRootModule1", jointClip=clip.joint_clip)
```

A pose, an animation or a clip should be saved through `assethandlers.save_control_file` or `assethandlers.save_anim_clip`, not `handlers.save`. `handlers.save` versions the path it is given, which for a folder type is the whole folder. The two helpers version only the one file (or the one clip's FBX), and tell source control about it.

Textures, shaders and postops have no handler yet. The weight, shape and rig tools read and write through these handlers, and the tools that sit on top are in [`tools.md`](tools.md).

## Library

`bmaya.core.asset.library` is the pose and animation library on disk (RigModules D51, `design/library-browser.md`). It is plain Python: where the files live, how to find them, and what to do with them as files. What a file holds comes from a reader passed to `Index`, which in Maya is `rigmodules.library.get_data_file_info`.

Poses and animations belong to a **rig**: they are keyed by control markup, which is unique per rig, so every source is of one rig of one asset. A **source** is a folder pair, `controlposes` and `controlanims`, with a write rule:

| Source | Folder | Written by |
|---|---|---|
| `approved` | The rig's own `rigs\<rig>\controlposes` and `controlanims`, in source control | The art director, through source control. Read only here |
| `shared` | The folders of the rig this one was copied from (`rig.json`'s `source`), when it has one and it is on disk. One level | Whoever owns that rig. Read only here |
| `user` | `<projects root>\user\<login>\animlibrary\<asset id>\<rig>\controlposes` and `controlanims` | The animator, with no source control. **Where every save goes** |

`library.sources(asset, rig)` returns the ones that exist, in that order. A rig that is not on disk still has its `user` source. The login is the OS user. `user` at the top of the projects root is reserved: the registry does not scan it, and `assetid.check` refuses an id that starts with `user`. RigModules' `core/AssetId` does not check this yet, so an id of `user\x` passes `createRigFromTemplate` and fails in `Asset`.

Files are `<name>.controlpose.json` and `<name>.controlanim.json`. A `<name>.json` written before the suffixes is listed as `legacy` and loads. A rename gives it the new suffix.

```python
from bmaya.core.asset import Asset, library

hero = Asset("shooter\\main\\characters\\hero")
user = library.user_source(hero, "game")                # pure: no folder is made
files = library.list_files(user, library.POSE)           # LibraryFile(path, name, kind, source, writable, modified, legacy)
library.free_name(user, library.POSE)                    # "pose_001"

index = library.Index(reader)                            # reader(paths, context) -> one FileInfo per path
entries = index.entries(files, context=rig_root)        # only new or changed files are read, in one call
library.filter_entries(entries, library.parse_query("tag:fist hand"))
```

| Function | Does |
|---|---|
| `sources(asset, rig)`, `user_source(asset, rig)`, `user_root()` | The sources of a rig, and the signed-in user's folder |
| `list_files(source, kind)`, `find_file(folder, kind, name)`, `free_name(source, kind, prefix)` | List a folder, find a name (suffixed, else legacy), the next free `pose_001` |
| `rename_file(file, name)`, `delete_file(file, root)`, `copy_to_user(file, user)` | File operations. The first two work only in a writable source, take a thumbnail (`<name>.png`) with the file, and `delete_file` keeps a local version. `copy_to_user` never overwrites. They raise `LibraryError` |
| `Index(reader).entries(files, context)`, `forget(path)` | What each file holds, cached by path, modified time and context (the rig root, because which controls a file matches depends on the rig) |
| `parse_query(text)`, `matches`, `filter_entries`, `format_term` | The search box |
| `has_term(text, field, value)`, `toggle_term(text, field, value)` | Whether the search text has a term, and the text with it added or taken out. What the browser's Filter menu does to the box |
| `read_masks`, `write_masks`, `saved_masks(asset, rig)`, `save_mask(asset, rig, mask)`, `delete_mask(asset, rig, name)` | Named masks, saved as `masks.json` beside the library folders: the team's next to the Approved folders, the user's next to the User ones. A user mask replaces a team mask of the same name |

**Search.** Free words must all appear in the name, a tag or the description, ignoring case. A term is `field:value`, or `field:"two words"`. `tag`, `template`, `skeleton`, `by` (the author), `category` and `asset` match a part of the value. `source`, `kind`, `status` and `region` (the file's `rigRegions`) match the whole value. Every term must match, so two `tag:` terms narrow the result. A word before a colon that is not a field stays a free word.

**Masks.** A `Mask` is a name and `MaskItem`s of `module_type`, `side` and `usage`, each optional. A control is in the mask when any item matches it, by its markup and never its name, so a mask works on any rig of the template. `LibrarySession` builds masks from the rig with no authoring: one per module type present, one per side, and one per module.

## Building a rig from an asset

`bmaya.maya.assettools.build_rig(asset_id, rig, look=None, namespace=None, parent_rig_root=None)` is the one place the asset model and RigModules meet. It:

1. Loads the rig's template path through the `template` handler, and finds the skeleton the rig is built on (`Asset.skeleton_of`, which may be another asset). A missing skeleton file fails here: "Save it with Save Skeleton first".
2. Picks the look: `look`, else the asset's `default` look when it has one, else none. A look the asset doesn't have, or whose `look.json` doesn't name the rig's skeleton, fails now, before anything is created.
3. Picks the namespace, `namespace` or `{asset name}_{rig}` (`hero_game`), RigModules' own default, and refuses one that already holds a rig (`rigmodules.query.get_rigs`). A namespace holds one rig (RigModules D54), so this fails before the skeleton is created rather than in the build.
4. Finds the parent when the rig has one (below).
5. Creates the skeleton's joints from its `skeleton.json` in the namespace (`cmds.loadRigSkeleton`).
6. Builds: `cmds.createRigFromTemplate(*joints, template=..., asset=asset.id, namespace=..., parentRig=...)`, with `parentRig` only for an attachment.
7. Loads the rig's shape file when it has one. Then the look, through `apply_look` (below) when it has a model and weight files, which records it on the rig. A look with a model and no weights yet has its meshes imported bare, and the rig records no look.
8. Clears the selection and returns the rig root.

A built rig carries its own asset id and rig name (the rig root's `assetId` and `rigName`) and the look it wears (`RigInfo.look`, from its `lookRoot`), which the other tools read through `rigmodules.query`. Nothing parses node names. `save_skin_weights` and `load_skin_weights` use the look the rig wears, and `look` overrides it. For a rig that wears none they use the one look it can wear, and raise when there are several.

### Building an attachment

A rig whose `rig.json` has a `parent` follows that rig (RigModules D55, `docs/attachments.md` there). `build_rig` finds the parent's rig root before it creates anything:

- `parent_rig_root` given: it must be a rig of the parent's asset id and rig name (`RigInfo.asset_id`, `rig_name`), else an error says which rig it is. A rig that has no parent takes no `parent_rig_root`.
- Not given: the scene's rigs are searched for that asset id and rig name. One is used and left as it is. **None: the parent is built first**, with its own default look, by the same call (so a hat on a face on a body builds all three). Several is an error that names them and asks for `parent_rig_root`.
- Rigs that attach to each other in a loop fail before anything is created.

The attachment builds into `{asset name}_{rig}` as ever, with `parentRig` set. RigModules checks the template's `parent:` ids against the parent and lists every missing socket. A failed attachment build leaves the parent in the scene, since it is a valid rig on its own, and the error says so. The shapes, look and active rig run per rig, and the attachment's root is the one returned and made active.

### Putting a rig in a look

`bmaya.maya.assettools.apply_look(node, look)` swaps the look of the rig that `node` belongs to (RigModules D54 phase 5, `docs/looks.md` there). A look that isn't synced is synced first. It checks that the asset has the look, that its `look.json` names the rig's skeleton, and that it has a model and weight files. Then, as one undo step, it imports the model into the rig's namespace and calls `cmds.setRigLook` with the imported meshes and the weight files. RigModules matches each mesh to its file by `meshId`, fails the swap when a file's `skeletonHash` is not the rig's, deletes the previous look's meshes, names the new ones after their files and records the look on the rig. The new meshes then join the rig's mesh layer and group. A failed swap deletes the meshes it imported. The controls and the animation are not touched. Materials of the previous look stay in the scene.

**A look that spans a rig and its attachment.** `look.json` can name several skeletons, so one look (`default`) holds one model and one weights folder for a body and its face. Then `apply_look` gives each rig only what is its own: it keeps the weight files whose `skeletonHash` is the rig's (`RigInfo.skeleton_hash`, read with `rigmodules.skinweights.read_file_skeleton_hash`), imports the model, deletes the meshes with no kept file (by `meshId`) and passes the rest to `cmds.setRigLook`. A weight file with no hash can't be placed on such a look and is an error that names the file. A look with no file for the rig is an error that names the rig and its skeleton hash. The cost is one model import per rig, trimmed afterwards. A look that names one skeleton behaves as it always did: every file is passed, and a file for another skeleton fails in RigModules.

## Tests

`tests\asset\run.bat` runs the plain Python tests, then the Maya handler and tool tests in mayapy ([`../tests/README.md`](../tests/README.md)).
