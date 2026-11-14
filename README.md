# mayadev

The pipeline and tooling repo for a Maya rigging and animation workflow. Its Python package is `bmaya`, under `py/scripts/bmaya`. It runs on Maya 2026 (Python 3, PySide6) and sits on top of [RigModules](https://github.com/benmorgantd/cpp-rigmodules), the C++ rig module plugin.

mayadev owns everything around the rigs: where an asset's files live and how they are saved and versioned, the menus that run the tools, the active rig tracker, skinning and joint tools, the Qt framework, logging and batch jobs. RigModules owns the rig itself: the module nodes, the template, controls, poses, animation data and weights files. mayadev depends on RigModules and never the reverse (D24).

## What it does

| Area | What you get | Page |
|---|---|---|
| Assets | An asset id is a folder path. Projects, assets and rig variants are found on disk. A registry answers "which assets share this skeleton". Saves keep a local version copy and tell source control | [docs/assets.md](docs/assets.md) |
| Rig build | Build Rig from Asset imports the skeleton, builds the variant's template, then loads its shapes, model and skin weights | [docs/tools.md](docs/tools.md) |
| Pose and animation | Save and load poses and animations as asset files, mirror, flip, zero and key a whole rig or a selection | [docs/tools.md](docs/tools.md) |
| Clips | Capture a rig's joints to an FBX clip, restore a rig from an FBX clip, check a clip against the skeleton export, edit the engine's clip properties | [docs/clips.md](docs/clips.md) |
| Menus | A tool is an id and one function call in JSON. A layout file arranges tools into a menu. Both are checked on every read and write, and both have editors | [docs/tools.md](docs/tools.md) |
| Framework | Logger, progress window, callback registry, mayapy batch runner, Qt base classes | [docs/framework.md](docs/framework.md) |
| Skinning and joints | Weight tools, joint authoring and a set of generic Maya utilities, most of them older code | [docs/status.md](docs/status.md) |

## Requirements

- Maya 2026 with `mayapy`. Windows is the only platform the batch files and paths are written for.
- The RigModules plugin (`RigModules.mll`) and its `python/rigmodules` package. Without the plugin, startup logs a warning and skips the RigModules menu. Without the package, `bmaya.maya.assettools`, `activerig`, `posetools` and `assethandlers` fail to import.
- `bmaya.asset` needs only Python 3.10 or newer. It has no Maya import, so it runs in plain Python, mayapy and batch jobs.

## Install

1. Clone the repo and set `MAYADEV_ROOT` to it and `RIGGING_PROJECT_DIR` to the folder that holds your projects.
2. Put `py/scripts` on Maya's Python path with a `mayadev.mod` file, and do the same for RigModules' `python` folder with its `RigModules.mod`.
3. Optionally set `RIGMODULES_PLUGIN` to a copy of the plugin build.
4. Start Maya. `userSetup.py` loads the plugin and builds the **bmaya tool menu** and the **RigModules** menu.

The steps in full, with an example `Maya.env`, are in [docs/setup.md](docs/setup.md).

## Quick start

Create a project, an asset and a variant from the RigModules menu (asset submenu: **New Project...**, **New Asset...**, **New Variant...**), or from Python:

```python
from bmaya.asset import Asset, Project

Project.create(r"D:\projects\shooter\main")
hero = Asset.create("shooter\\main\\characters\\hero", "Character")
```

Save the skeleton scene with **Save Skeleton...**, then **Build Rig from Asset...** builds a variant on it. From then on the pose, shape, weight and clip tools find the asset's files from the selected rig.

## Layout

```
py/scripts/
  userSetup.py          deferred startup: logger, plugin load, menus, active rig tracker
  Maya.env              Maya environment file
  bmaya/
    asset/              assets on disk: ids, projects, registry, versions. No Maya import
    core/               logger, progress manager, tool registry, batch base, file utils
    maya/               everything that imports maya: handlers, tools, active rig, events, utils, skinning
    maya_ui/            Qt: base classes, the two editors, the menu builder
  docs/, mkdocs.yml     deprecated mkdocs site: generated API pages and two old guides (batch/docgen)
  plug-ins/             Python API nodes, older code
py/plug-ins/            more Python API nodes, older code
toolsets/               master_tool_registry.json and the two menu layouts
batch/docgen/           the API doc generator (deprecated with the mkdocs site)
tests/                  unittest suites: asset, core (tool registry, editors), rigmodules_menu, startup
docs/                   these pages
```

## Documentation

| Page | Contents |
|---|---|
| [docs/README.md](docs/README.md) | How the docs are organized and kept current |
| [docs/setup.md](docs/setup.md) | Environment, `.mod` files, startup, dev reload |
| [docs/architecture.md](docs/architecture.md) | Layers, source map, handlers, recipes |
| [docs/assets.md](docs/assets.md) | Asset ids, files, registry, publishes, versions, handlers |
| [docs/clips.md](docs/clips.md) | FBX clips, bone maps, `animproperties` |
| [docs/tools.md](docs/tools.md) | Registry, menus, every menu tool, the active rig |
| [docs/rigmodules.md](docs/rigmodules.md) | What mayadev uses from RigModules |
| [docs/framework.md](docs/framework.md) | Logger, progress, events, batch, Qt, doc generator |
| [docs/status.md](docs/status.md) | Code status and known problems |
| [tests/README.md](tests/README.md) | Running and writing tests |

The design decisions behind the asset model, the boundary and the clip format are in RigModules' `design/` folder (`decisions.md` D24, D29, D30, D42; `asset-model.md`; `mayadev-integration.md`; `control-library.md`).
