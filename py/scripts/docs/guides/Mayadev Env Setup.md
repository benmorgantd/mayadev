!!! warning "Deprecated"
    This page is no longer maintained and may be out of date. Its content moved to the hand-written
    documentation in the repo's top-level `docs/` folder: `docs/setup.md` (environment, startup) and `docs/tools.md` (menus). Fix those pages, not this one.

### Mayadev Environment Setup

## Environment variables
Set these as user environment variables, or in `documents\maya\2026\Maya.env`. Maya.env only fills in a variable the system doesn't already set, so set each one in one place.
- `RIGGING_PROJECT_DIR` : The root of every game's projects, and the root asset ids are relative to (see `docs/assets.md`)
- `MAYADEV_ROOT` : This is where your mayadev repo is installed
- `RIGMODULES_PLUGIN` (optional) : The `RigModules.mll` that startup loads. Defaults to the plugin name `RigModules`, which only works once the plugin is on `MAYA_PLUG_IN_PATH`. Point it at a copy of the build, not `cpp\x64\Release\RigModules.mll` itself: a loaded plugin locks the file, so the next build would fail.

Example:
```
RIGGING_PROJECT_DIR=C:\Users\morga\Documents\Art\Maya\rigs
MAYADEV_ROOT=C:\Users\morga\Documents\mayadev
RIGMODULES_PLUGIN=C:\Users\morga\Documents\maya\plug-ins\RigModules.mll
```

## Module files
Maya reads `.mod` files from `documents\maya\modules`.
- `mayadev.mod` puts `py\scripts` on the Python path, so `bmaya` and `userSetup.py` are found.
- `RigModules.mod` puts RigModules' `python` folder on the Python path, so `rigmodules` is found. The asset tools need it. Copy it from the RigModules repo root and replace its `.` with the repo's full path (see RigModules' `docs/python.md`).

## RigModules menu
When startup loads RigModules, it adds a **RigModules** menu built from `toolsets/rigmodules_menu.json`. If the plugin doesn't load, startup logs a warning and skips the menu. The tools ask with small dialogs and report errors in the Script Editor. The menu is a set of submenus: asset, mesh, joints, weights, shapes, control and dev. A new tool goes in the submenu for its topic, and only a tool animators use constantly goes at the top level.

The rig tools act on the **active rig**, so there is no need to select a rig root. Selecting any control, joint, module or rig root of a rig makes it active, and it stays active while you select other things. The Script Editor logs `Active rig: ...` when it changes. A new or opened scene makes its first rig active. Startup starts the tracker (`bmaya.maya.activerig`) once the plugin loads.

| Tool | Select | Does |
|---|---|---|
| Print Joint Markup | joints | Prints each joint's markup JSON |
| Remove Joint Markup | joints | Removes their markup |
| Select All Controls | active rig | Selects every control in the rig |
| Select Mirror Controls | controls | Selects the controls on the other side instead |
| Mirror Shapes Left to Right / Right to Left | active rig | Mirrors control shapes from one side to the other |
| Save Control Shapes... / Load Control Shapes... | active rig | Saves or loads the variant's `shapes.json` in the rig's asset. Before the asset folder exists, uses a file dialog |
| Mark Meshes for Skinning | meshes | Gives each selected mesh a `meshId` (RigModules `setRigMeshId`), the id its weight files are matched by. A mesh keeps the id it has, and the log says how many were new and how many kept theirs |
| Mark Meshes with New Ids | meshes | The same, but replaces their ids. Use it on a duplicated mesh, which copied its source's id. The log reads "N mesh(es) given new ids" |
| Save Skin Weights... / Load Skin Weights... | active rig | Saves every skinned mesh in the rig's namespace to the variant's `weights` folder, one file per mesh, or loads the folder onto the meshes, matched by `meshId`, as one undo step. Before the asset folder exists, uses a folder dialog |
| New Project... | nothing | Writes a `project.json` into a folder you pick |
| New Asset... | nothing | Asks for an asset id and one of the project's asset types, then writes the asset's `asset.json` |
| New Variant... | nothing | Copies a template you pick into the asset as the variant named by its `rigName` |
| Save Skeleton... | nothing | Saves the open scene as the asset's skeleton file |
| Save Model... | nothing | Saves the open scene as a variant's model file, the meshes it skins. Mark the meshes for skinning first: it warns about meshes without a `meshId` |
| Build Rig from Asset... | nothing | Imports the asset's skeleton into its namespace, builds a variant's template on it, then loads the variant's shapes, imports its model into the same namespace and loads its skin weights, each when the asset has it |
| Save Rig | active rig | Saves the open scene as the variant's rig file. Before the asset folder exists, uses a file dialog |

The tools that ask for an asset id fill it in with the active rig's asset id. A rig can be built anywhere before its asset exists. Once the asset folder exists, the shape, weight and rig tools always use the asset's paths. The asset tools are in `bmaya.maya.assettools`, and their functions take arguments, so scripts can call them without the dialogs.

The scripts live in `toolsets/master_tool_registry.json`. Their tests are in `tests/rigging/rigmodules_menu`, `tests/asset/test_maya_asset_tools.py` and `tests/asset/test_maya_active_rig.py`.
