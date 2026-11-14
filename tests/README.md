# Tests

The mayadev tests use `unittest`. Most of them need nothing but Python, and the ones that need Maya run in `mayapy` against a RigModules plugin build. They were read for this page, not run: the environment that wrote it has no Maya.

## Running them

| Suite | Command | Needs |
|---|---|---|
| `bmaya.asset` model and `animproperties` | `python -m unittest discover -s tests/asset -p "test_asset_*.py"` | Python 3 |
| Handlers, tools and active rig | `tests\asset\run.bat` (after the line above) | mayapy, a RigModules `.mll` in `RIGMODULES_PLUGIN` |
| RigModules menu layout and scripts | `tests\rigging\rigmodules_menu\run.bat` | Layout checks: Python. Script checks: mayapy and `RIGMODULES_PLUGIN` |
| Startup smoke test | `tests\basic\startup_test\run.bat` | mayapy, `MAYADEV_ROOT` |

- `tests\asset\run.bat` runs the plain Python tests first and stops if they fail, then the Maya ones.
- The Maya tests **skip** without `RIGMODULES_PLUGIN`, or without `maya`, so a run with skips has not checked the boundary with RigModules ([`../docs/rigmodules.md`](../docs/rigmodules.md)). Read the skip count.
- Copy the `.mll` and point `RIGMODULES_PLUGIN` at the copy when a Maya session has the build loaded, because a loaded plugin locks the file.
- The Maya tests need RigModules' `rigmodules` package on `PYTHONPATH` (`RigModules.mod`).
- The batch files set `MAYA_SKIP_USERSETUP_PY=1` so Maya starts without `userSetup.py` and the tests see the plugin alone. They call `C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe`.
- The startup test runs through the batch framework, which writes a results folder under `~\Documents\maya\mayabatch_logs` ([`../docs/framework.md`](../docs/framework.md#batch-framework)).

## What each folder covers

| Path | Tests | Covers |
|---|---|---|
| `tests/asset/test_asset_model.py` | 44 | Ids, projects, assets, nesting, the registry, publishes, local versions, source control calls, handler dispatch. A temporary projects root, local versions in a temp folder, source control calls recorded |
| `tests/asset/test_asset_animproperties.py` | 16 | The `animproperties` file: defaults, validation messages, read and write |
| `tests/asset/test_maya_asset_handlers.py` | 21 | Each Maya handler on real scenes: shapes, scenes, clips (with ControlAnim, bone map and properties), control poses and animations, sources, the skeleton export, argument checks |
| `tests/asset/test_maya_asset_tools.py` | 51 | The `assettools` functions: variants, build, saves and loads, dialogs replaced by fakes |
| `tests/asset/test_maya_active_rig.py` | 9 | `get_active_rig` and the tracker |
| `tests/rigging/rigmodules_menu/test_maya_rigmodules_menu.py` | 37 | The layout (submenu order, 41 tools, every GUID in the registry, every script compiles), then each registry script run in Maya |
| `tests/basic/startup_test/main.py` | 1 | Maya starts through the batch framework and logs |

Not covered: `core/` (logger, progress manager, tool registry), the events registry, dev reload, the Qt classes, skinning, joint tools and the generic utilities ([`../docs/status.md`](../docs/status.md#test-coverage) lists proposed tests).

## Writing a test

- A test of anything in `bmaya.asset` is plain Python. Put it in `tests/asset/test_asset_*.py` and add `py/scripts` to `sys.path` as the existing files do. It must not import `maya`.
- A test that needs Maya goes in `test_maya_*.py` in the same folder. Initialize `maya.standalone` once for the class, load the plugin from `RIGMODULES_PLUGIN`, and `skipTest` when either is missing, as `test_maya_rigmodules_menu.py` does.
- File names matter: the batch files discover `test_asset_*.py` and `test_maya_*.py` separately, so a Maya test named `test_asset_*` runs in plain Python and fails.
- Use a temporary directory for every file a test writes, and remove it with `addCleanup`. Point `BMAYA_VERSIONS_DIR` and `RIGGING_PROJECT_DIR` at temporary folders so a test never touches real assets or the machine's version copies.
- Replace dialogs with fakes. The tools ask through `cmds.fileDialog2`, `cmds.confirmDialog` and small helper functions (`_ask_text` and its siblings), which the existing tests patch with `mock.patch.object`.
- Write expected values by hand, not by recording what the code produced.
- A new menu tool changes the tool count in the layout test.
