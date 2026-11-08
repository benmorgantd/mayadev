# Asset Layout

How assets sit on disk and how tools find their files with `bmaya.asset`. The design and its reasons are in RigModules' `design/asset-model.md` (decision D29).

`bmaya.asset` is plain Python, with no Maya import. It runs in Maya, mayapy, batch jobs and tools outside Maya. The legacy `bmaya.maya.asset` package belongs to the legacy rig builder and is not used by it.

## Asset ids

An asset id is the asset folder's path below `RIGGING_PROJECT_DIR`, with `|` between folders, at any depth:

```
shooter|main|characters|hero   ->   <RIGGING_PROJECT_DIR>\shooter\main\characters\hero
```

- Each folder name is letters, digits and `_`.
- Ids compare without case and are stored as written.
- A folder is an asset when it holds an `asset.json`. Assets never nest.
- The last token (`hero`) is the asset's name, and the default namespace its rigs are built into.

`bmaya.asset.assetid` holds these rules. Code that splits or joins ids goes through it.

## Files

```
<RIGGING_PROJECT_DIR>\shooter\main\
  project.json                    asset types and file types
  registry.json                   cache of every asset.json below, rebuilt on demand
  characters\hero\
    asset.json
    skeleton\hero_skeleton.ma     shared by every variant
    poses\  anims\
    variants\game\
      model\hero_game_model.ma
      textures\  shaders\  weights\
      template.json  shapes.json  postops.py
      hero_game.ma                the built rig
      versions\shapes.v001.json   local version copies
```

### project.json

```json
{
  "formatVersion": 1,
  "assetTypes": ["Prop", "Character", "Vehicle", "Head", "Weapon", "VFX", "Light", "Environment", "Skeleton", "Other"],
  "fileTypes": {
    "shapes": { "path": "variants/{variant}/shapes.json" },
    "weights": { "path": "variants/{variant}/weights", "folder": true }
  }
}
```

`Project.create(folder)` writes the full default, which has every file type above. A file type's `path` is relative to the asset folder. `{name}` is the asset's name. A path with `{variant}` is per variant, and every other path belongs to the whole asset. An asset belongs to the nearest `project.json` above it.

### asset.json

```json
{
  "formatVersion": 1,
  "assetType": "Character",
  "skeleton": "shooter|main|skeletons|biped",
  "rigs": ["game", "cine"],
  "publishes": { "game": 12 }
}
```

| Key | Meaning |
|---|---|
| `assetType` | One of the project's `assetTypes` |
| `skeleton` | Optional. The id of the asset whose skeleton this one uses. Left out, the asset owns its skeleton |
| `rigs` | Rig variant names. Each matches a RigModules template's `rigName` |
| `publishes` | Optional. The latest publish number per variant |

The id is not stored, because it is the folder's path.

## Using it

```python
from bmaya.asset import Asset, Project, Registry

Project.create(r"D:\projects\shooter\main")                  # once per project
hero = Asset.create("shooter|main|characters|hero", "Character",
                    skeleton="shooter|main|skeletons|biped", rigs=["game"])

hero = Asset("shooter|main|characters|hero")                  # an existing asset
hero.path("shapes", variant="game")                           # never touches the disk
hero.file_exists("skeleton")
hero.add_rig("cine")

registry = Registry(hero.project)
registry.find(asset_type="Character")
registry.find(skeleton=hero.skeleton)                         # assets that can share hero's poses and anims
registry.latest_publish(hero.id, "game")
```

In `Registry.find`, a skeleton matches the asset that owns it and every asset that names it.

Reading a path never makes a folder. `Asset.create` makes the asset folder, and saving through a handler makes the file's folder.

## Registry

`registry.json` caches every `asset.json` in the project: type, resolved skeleton, variants, publishes and the files that exist. `asset.json` stays the source of truth. Every write through `Asset` updates its entry. A missing registry is rebuilt on first use, and `Registry(project).rebuild()` rebuilds it by hand. `registry.errors` lists what the last rebuild skipped: nested assets, ids that differ only in case, and unreadable `asset.json` files.

## Local versions

Saving through `bmaya.asset.handlers.save` first copies the old file to `versions\` beside it: `shapes.json` becomes `versions\shapes.v007.json`, and a folder such as `weights\` becomes `versions\weights.v003\`. The next number is the highest existing number plus one. `bmaya.asset.versions.list_versions(path)` lists the copies.

## Saving and loading

Where a file lives is kept apart from how it is read. `bmaya.asset.handlers` dispatches by file type to a registered `FileHandler`, whose `save` and `load` raise `NotImplementedError` until written. The Maya handlers are in `bmaya.maya.assethandlers`:

| File types | Handler |
|---|---|
| `skeleton`, `model`, `rig` | Save renames and saves the open scene. Load imports into the asset's namespace (or `namespace=`), merging into it if it exists. Never references |
| `shapes` | RigModules `saveRigControlShapes` / `loadRigControlShapes`. Pass `rig_root=` |

```python
from bmaya.asset import Asset, handlers
from bmaya.maya import assethandlers

assethandlers.register()                                      # once per session
hero = Asset("shooter|main|characters|hero")
handlers.load(hero, "skeleton")
handlers.save(hero, "shapes", variant="game", rig_root="hero:rigRootModule1")
```

Weights, textures, shaders, postops, poses and anims have no handler yet.

## Tests

`tests\asset\run.bat` runs the plain Python tests, then the Maya handler tests in mayapy. Set `RIGMODULES_PLUGIN` to a RigModules `.mll` for the Maya tests, or they skip. Copy the `.mll` first if a Maya session has it loaded.
