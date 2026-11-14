# Code status

What each area of the code is worth keeping, who uses it, and the problems found reading it. It starts from the verdicts in RigModules' `design/mayadev-integration.md` and records where the code is now. "Nothing imports it" means a search of `py/scripts`, `toolsets` and `tests` found no importer, so it is a library, a script run by hand, or dead.

Verdicts: **Keep** (current, in use), **Deprecated** (replaced, kept for now), **Adapt** (the idea stays, the code is to be reworked to sit on RigModules), **Reference** (read it for requirements, don't extend it), **Unused** (nothing calls it).

## By area

| Area | Path under `py/scripts/bmaya` | Verdict | State |
|---|---|---|---|
| Asset model | `asset/` | Keep | Current, Maya-free, tested in plain Python ([`assets.md`](assets.md)) |
| Maya asset handlers and tools | `maya/assethandlers.py`, `assettools.py` | Keep | Current. The only code that crosses into RigModules besides `activerig` and `posetools` ([`rigmodules.md`](rigmodules.md)) |
| Active rig, pose tools | `maya/activerig.py`, `posetools.py` | Keep | Current, tested |
| Dev reload | `maya/devreload.py` | Keep | Current, no tests |
| Startup | `userSetup.py` | Keep | Current ([`setup.md`](setup.md)) |
| Core utilities | `core/log.py`, `progressmanager.py`, `decorators.py`, `util/` | Keep | In use. `core/log.py` imports Maya (below) |
| Tool registry, menus, editors | `core/tool_registry.py`, `maya_ui/tool_views/`, `maya_ui/tool_registry_editor.py` | Keep | In use ([`tools.md`](tools.md)) |
| Batch framework | `core/batch/`, `maya/batch/` | Keep | Used by one smoke test and the doc generator |
| mkdocs site and doc generator | `py/scripts/docs`, `py/scripts/mkdocs.yml`, `batch/docgen/` | Deprecated | Replaced by the top-level `docs/` ([`README.md`](README.md#the-old-mkdocs-site-deprecated)). Kept only for the generated API pages |
| Events registry | `maya/eventsregistry.py` | Keep | Used by the active rig tracker |
| Qt base | `maya_ui/qtbase.py` | Keep | In use |
| Joint authoring | `maya/rigging/joint.py` | Keep the tools | Two menu entries are broken, one function is hard-coded (below). `label_joints` is replaced by `cmds.rigJointMarkup` |
| Skinning | `maya/rigging/weights/` | Adapt | Not in any menu. Nothing imports `weightio` or `weightutils`. Three files are Python 2 (below). Weight files for rigs are RigModules' (`saveRigSkinWeights`), so these are the editing tools, not the file format |
| Generic Maya utils | `maya/util/` | Keep the generic ones | Nothing imports them except `nameUtils`, by `joint.py`. Libraries for scripts run by hand |
| `matrixConstraint.py` | `maya/util/` | Unused | A Python matrix parent constraint. `rigConstraint` inside RigModules rigs replaces it. Nothing imports it |
| Modeling | `maya/modeling/blendBoundary.py` | Keep | Normal blending between meshes. Nothing imports it |
| Naming tool | `maya_ui/namingTool/` | Reference | Window for the older `name_side_type` convention. Nothing opens it |
| Naming constants | `core/constants.py` | Reference | The older rig builder's names (`L`/`R`/`M`, `JNT`, `ctrl`, `ROOT_JOINT`, layout controls). Used by `nameUtils`, `joint.py` and the naming tool. `ASSET_TYPES` has no user: the asset types are in `project.json` |
| Python API plug-ins | `py/plug-ins/`, `py/scripts/plug-ins/` | Reference | Older nodes: aim constraint, quatExtract, softIK, coneReader, rayIntersect, wheel, trig, collision, spring, prune and extrude weights. quatExtract (twist), softIK and coneReader are candidates for C++ when a RigModules module needs one |

The older rig builder, its modules, shape IO, the rig manager UI and the legacy asset layer are deleted. The tag `legacy-rig-builder` keeps them, for reading as a list of animator-facing requirements when a RigModules module goes through its gate. Nothing built with them needs migrating (D30).

## Known problems

Found reading the code and compiling it. None were fixed by the documentation change.

**Broken today**

- **Orient to World and Orient to Mesh** (bmaya tool menu): both registry scripts import `bmaya.maya.rigging.joints`, and the module is `bmaya.maya.rigging.joint`. They raise `ModuleNotFoundError`.
- **Three files don't compile under Python 3**, so Maya 2026 can't import them and the doc generator can't document them: `maya/rigging/weights/skin/averageVertexSkinWeightCmd.py`, `bm_softCluster.py` and `cvshapeinverter.py` (`except Exception, e`, `print x` and `raise X, 'text'`). So does `py/plug-ins/cv_nodeTemplate.py`. The files beside them (`averageVertexSkinWeightBrush.py`, `cvshapeinverter_plugin.py`) don't import them, so those compile.
- **`weightutils.py`** imports `maya.api.OpenMaya` as `om` and then calls API 1 names on it, such as `om.MScriptUtil`, which API 2 doesn't have. `get_skin_cluster_weights` is one that does, so it should fail as written. This was read, not run: it needs a Maya session to confirm.
- **`joint.add_twist_joints`** hard-codes `skel:shoulder_00_L_JNT` and `skel:elbow_00_L_JNT`, so it works on one named skeleton only.

**Inconsistent**

- **`py/plug-ins/` and `py/scripts/plug-ins/`** hold different copies of the same plug-ins (`bmPruneWeights.py`, `bm_coneReader.py`, `bm_quatExtract.py`, `bm_rayIntersect.py`), and each has files the other lacks. Which is current is unknown.
- **`core/log.py`** imports `maya.api.OpenMaya` and an unused `bmaya.maya.constants`, so the logger, and with it every module that logs, needs Maya and `MAYADEV_ROOT`. A `TODO` there says to move the handler to a Maya-level module. `bmaya.core` is the layer that is meant to be Maya-free.
- **`userSetup.py` calls `init_logger()` without `is_batch`**, so a batch session gets the Maya handler, not the stdout one the batch framework captures.
- **`mayadev.mod` is not in the repo**, though the setup guide and RigModules' integration plan describe it. A fresh clone has to write it by hand ([`setup.md`](setup.md#module-files)).
- **Two install routes**: `py/easyInstall.py` writes a different `bm.mod`.
- **`ControlAnim` file name**: RigModules' `docs/library.md` and `design/control-library.md` say `controlanims/<name>.anim.json`, and `ControlAnimHandler` writes `controlanims/<name>.json` ([`clips.md`](clips.md)). The `.anim.json` name is used only for the ControlAnim beside an exported clip. Undecided which side moves.
- **Animation properties JSON** is written unsorted with `indent=4`, where every other asset file is sorted with `indent=2`.

**Stale documentation**

The two guides under `py/scripts/docs/guides/` predate this folder:

- `Mayadev Env Setup.md` lists the RigModules submenus as asset, mesh, joints, weights, shapes, control and dev. The menu also has **pose** and **clip**, and the layout test pins nine submenus.
- `Asset Layout.md` shows the rig file as `variants/Human/hero_Human.ma`. The default `rig` file type is `variants/{variant}/{name}_{variant}_rig.ma` (`hero_Human_rig.ma`).
- Both are deprecated and superseded by [`setup.md`](setup.md), [`tools.md`](tools.md) and [`assets.md`](assets.md) ([`README.md`](README.md#the-old-mkdocs-site-deprecated)). They carry a banner saying so, and these two details are left as they were.

## Test coverage

| Area | Tests |
|---|---|
| `bmaya.asset` | `tests/asset/test_asset_model.py` (44 tests) and `test_asset_animproperties.py` (16): plain Python |
| Handlers, tools, active rig | `tests/asset/test_maya_*.py` (21, 51 and 9 tests): mayapy with a plugin build, or skipped |
| Menu layout and scripts | `tests/rigging/rigmodules_menu` (37 tests): the layout checks run in plain Python, the script checks need the plugin |
| Startup | `tests/basic/startup_test`: one smoke test that Maya starts and logs |
| Nothing | `core/` (logger, progress manager, tool registry), `eventsregistry`, `devreload`, `qtbase`, the editors, `rigging/`, `modeling/`, `util/`, `batch/` |

## Proposed tests

For the author to accept. None are written.

| Check | Tier | Why |
|---|---|---|
| The tool registry loads and saves a file unchanged (`ToolRegistry.load_registry` then `save_registry`) | Plain Python | The registry is the source of every menu and has no test |
| Every registry script's `cmds.*Rig*` calls name a command RigModules registers | mayapy with the plugin | `test_every_script_compiles` doesn't catch a renamed command ([`rigmodules.md`](rigmodules.md#when-a-rigmodules-name-changes)) |
| Every registry script's imports resolve to a module in the package | Plain Python (`importlib.util.find_spec` on the dotted path) | Would have caught the `joints` against `joint` typo |
| Every `.py` file under `py/scripts/bmaya` compiles under Python 3 (`py_compile`) | Plain Python | Pins the three Python 2 files as a known list, and fails on a new one |
| The asset examples in [`assets.md`](assets.md) run against a temporary projects root | Plain Python | Docs examples as tests, like RigModules' README quick start |
| The `animproperties` example in [`clips.md`](clips.md) round-trips through `read` and `write` | Plain Python | The same |
| `bmaya.core` and `bmaya.asset` import nothing from `maya` (an import hook or an AST check), with `core/log.py` listed as the known exception | Plain Python | The layer rule in [`architecture.md`](architecture.md) is checked by nothing |
