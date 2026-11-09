"""bmaya.maya.assettools in mayapy, against the RigModules plugin and its rigmodules package (RigModules D30).

Needs RIGMODULES_PLUGIN, the path of a RigModules.mll (copy it first if a Maya session has the build
loaded), and the rigmodules package on the path (RigModules.mod puts it there). Skipped without them.
Run with tests/asset/run.bat.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

try:
    import maya.standalone
except ImportError:
    maya = None

PLUGIN = os.environ.get("RIGMODULES_PLUGIN", "")
HERO = "shooter|main|characters|hero"
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "AssetToolsTest",
    "rigName": "game",
    "rigAuthor": "tests",
    "rigModules": [
        {"moduleType": "FkChain", "name": "spine", "shapeType": "Box",
         "moduleArgs": {"joints": [["Center", "spine1"], ["Center", "spine2"]]}},
    ],
}


def setUpModule():
    if maya is None:
        raise unittest.SkipTest("needs mayapy")
    if not os.path.isfile(PLUGIN):
        raise unittest.SkipTest("set RIGMODULES_PLUGIN to a RigModules.mll")
    maya.standalone.initialize(name="python")
    from maya import cmds
    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)
    try:
        import rigmodules.query  # noqa: F401
    except ImportError:
        raise unittest.SkipTest("put RigModules' python folder on the path (RigModules.mod)")


class AssetTools(unittest.TestCase):

    def setUp(self):
        from maya import cmds
        import bmaya.asset
        import bmaya.asset.handlers
        import bmaya.maya.assethandlers
        import bmaya.maya.assettools

        self.cmds = cmds
        self.tools = bmaya.maya.assettools
        temp = tempfile.mkdtemp(prefix="bmaya_asset_tools_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.temp = temp
        self.root = os.path.join(temp, "projects")
        environ = {"RIGGING_PROJECT_DIR": self.root, "BMAYA_VERSIONS_DIR": os.path.join(temp, "local_versions")}
        patcher = mock.patch.dict(os.environ, environ)
        patcher.start()
        self.addCleanup(patcher.stop)

        bmaya.asset.Project.create(os.path.join(self.root, "shooter", "main"))
        self.hero = bmaya.asset.Asset.create(HERO, "Character")
        self.template = self.write_template(TEMPLATE)
        for file_type in bmaya.maya.assethandlers.MAYA_FILE_TYPES + ("shapes", "template"):
            self.addCleanup(bmaya.asset.handlers.unregister, file_type)
        cmds.file(new=True, force=True)

    def write_template(self, data, name="template.json"):
        path = os.path.join(self.temp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        return path

    def make_skeleton(self):
        cmds = self.cmds
        joints = []
        for i, usage in enumerate(("spine1", "spine2")):
            if joints:
                cmds.select(joints[-1], replace=True)
            else:
                cmds.select(clear=True)
            joint = cmds.joint(name=f"{usage}_jnt", position=(0, i * 2, 0))
            cmds.rigJointMarkup(joint, usage=usage, side="Center", export=True, skin=True)
            joints.append(joint)
        return joints

    def make_buildable_asset(self):
        """A hero with variant game and a saved skeleton, in a new empty scene."""
        self.tools.new_variant(HERO, self.template)
        self.make_skeleton()
        self.tools.save_skeleton(HERO)
        self.cmds.file(new=True, force=True)

    def build_outside_the_asset(self, asset_id):
        """A rig built from a template anywhere, the way a rigger iterates before the asset exists."""
        self.cmds.createRigFromTemplate(*self.make_skeleton(), template=self.template.replace("\\", "/"), asset=asset_id)
        import rigmodules.query
        return rigmodules.query.get_rigs()[0].rig_root

    # ---- variants and skeleton ----

    def test_new_variant_copies_the_template_named_by_its_rig_name(self):
        self.assertEqual(self.tools.new_variant(HERO, self.template), "game")
        self.assertEqual(self.hero.variants, ["game"])
        with open(self.hero.path("template", "game"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), TEMPLATE)

    def test_new_variant_twice_fails(self):
        self.tools.new_variant(HERO, self.template)
        with self.assertRaisesRegex(RuntimeError, "already has variant 'game'"):
            self.tools.new_variant(HERO, self.template)

    def test_new_variant_needs_the_asset(self):
        with self.assertRaisesRegex(RuntimeError, "Create it with New Asset first"):
            self.tools.new_variant("shooter|main|characters|nobody", self.template)

    def test_new_variant_needs_a_rig_name(self):
        path = self.write_template({"rigVersion": 1}, "no_rig_name.json")
        with self.assertRaisesRegex(ValueError, "has no rigName"):
            self.tools.new_variant(HERO, path)
        self.assertEqual(self.hero.variants, [])

    def test_save_skeleton_saves_the_open_scene(self):
        self.make_skeleton()
        path = self.tools.save_skeleton(HERO)
        self.assertEqual(path, self.hero.path("skeleton"))
        self.assertTrue(os.path.isfile(path))

    def test_save_skeleton_of_an_asset_that_shares_another_skeleton_fails(self):
        import bmaya.asset
        bmaya.asset.Asset.create("shooter|main|characters|villain", "Character", skeleton=HERO)
        with self.assertRaisesRegex(RuntimeError, "uses the skeleton of " + HERO.replace("|", r"\|")):
            self.tools.save_skeleton("shooter|main|characters|villain")

    # ---- building from the asset ----

    def test_build_rig_imports_the_skeleton_and_builds_the_variant(self):
        import rigmodules.query
        self.make_buildable_asset()
        rig_root = self.tools.build_rig(HERO, "game")
        info = rigmodules.query.get_rig_info(rig_root)
        self.assertEqual((info.asset_id, info.variant, info.namespace), (HERO, "game", "hero"))
        self.assertTrue(self.cmds.objExists("hero:spine1_ctrl_c"))

    def test_build_rig_loads_the_variant_shape_file(self):
        cmds = self.cmds
        self.make_buildable_asset()
        rig_root = self.tools.build_rig(HERO, "game")
        cmds.setAttr("hero:spine1_ctrl_c.shapeType", 1)  # Sphere
        self.tools.save_control_shapes(rig_root)

        cmds.file(new=True, force=True)
        self.tools.build_rig(HERO, "game")
        self.assertEqual(cmds.getAttr("hero:spine1_ctrl_c.shapeType", asString=True), "Sphere")

    def test_build_rig_into_a_namespace_that_holds_a_rig_fails(self):
        self.make_buildable_asset()
        self.tools.build_rig(HERO, "game")
        with self.assertRaisesRegex(RuntimeError, "already holds a rig"):
            self.tools.build_rig(HERO, "game")
        self.tools.build_rig(HERO, "game", namespace="hero2")
        self.assertTrue(self.cmds.objExists("hero2:spine1_ctrl_c"))

    def test_build_rig_needs_the_variant_and_the_skeleton(self):
        with self.assertRaises(FileNotFoundError):
            self.tools.build_rig(HERO, "game")
        self.tools.new_variant(HERO, self.template)
        with self.assertRaises(FileNotFoundError):
            self.tools.build_rig(HERO, "game")

    # ---- saving a rig and its shapes ----

    def test_shapes_go_to_the_asset_once_its_folder_exists(self):
        cmds = self.cmds
        rig_root = self.build_outside_the_asset(HERO)
        with mock.patch.object(cmds, "fileDialog2") as dialog:
            path = self.tools.save_control_shapes("hero:spine1_ctrl_c")
            self.assertEqual(path, self.hero.path("shapes", "game"))
            cmds.setAttr("hero:spine1_ctrl_c.shapeType", 1)
            self.tools.load_control_shapes(rig_root)
        dialog.assert_not_called()
        self.assertEqual(cmds.getAttr("hero:spine1_ctrl_c.shapeType", asString=True), "Box")

    def test_load_shapes_without_a_saved_file_fails(self):
        self.build_outside_the_asset(HERO)
        with self.assertRaises(FileNotFoundError):
            self.tools.load_control_shapes("hero:spine1_ctrl_c")

    def test_shapes_use_a_file_dialog_before_the_asset_exists(self):
        cmds = self.cmds
        self.build_outside_the_asset("shooter|main|characters|nobody")
        path = os.path.join(self.temp, "chosen_shapes.json").replace("\\", "/")
        with mock.patch.object(cmds, "fileDialog2", return_value=[path]):
            self.assertEqual(self.tools.save_control_shapes("nobody:spine1_ctrl_c"), path)
        self.assertTrue(os.path.isfile(path))
        self.assertFalse(os.path.exists(os.path.join(self.root, "shooter", "main", "characters", "nobody")))

    def test_save_rig_writes_the_variant_rig_file(self):
        self.tools.new_variant(HERO, self.template)
        self.build_outside_the_asset(HERO)
        path = self.tools.save_rig("hero:spine1_ctrl_c")
        self.assertEqual(path, self.hero.path("rig", "game"))
        self.assertTrue(os.path.isfile(path))

    def test_save_rig_needs_the_variant(self):
        self.build_outside_the_asset(HERO)
        with self.assertRaisesRegex(RuntimeError, "Add its template with New Variant first"):
            self.tools.save_rig("hero:spine1_ctrl_c")

    def test_save_rig_uses_a_file_dialog_before_the_asset_exists(self):
        self.build_outside_the_asset("shooter|main|characters|nobody")
        path = os.path.join(self.temp, "chosen_rig.ma").replace("\\", "/")
        with mock.patch.object(self.cmds, "fileDialog2", return_value=[path]):
            self.assertEqual(self.tools.save_rig("nobody:spine1_ctrl_c"), path)
        self.assertTrue(os.path.isfile(path))

    def test_rig_tools_need_a_rig_node(self):
        self.make_skeleton()
        with self.assertRaises(RuntimeError):
            self.tools.save_control_shapes("spine1_jnt")

    # ---- menu entry points ----

    def test_new_asset_ui_creates_the_asset_with_the_chosen_type(self):
        with mock.patch.object(self.tools, "_ask_text", return_value="shooter|main|props|crate"), \
                mock.patch.object(self.tools, "_choose", return_value="Prop") as choose:
            self.tools.new_asset_ui()
        import bmaya.asset
        self.assertEqual(bmaya.asset.Asset("shooter|main|props|crate").asset_type, "Prop")
        self.assertIn("Prop", choose.call_args.args[2])

    def test_new_asset_ui_without_a_project_fails(self):
        import bmaya.asset
        with mock.patch.object(self.tools, "_ask_text", return_value="elsewhere|props|crate"):
            with self.assertRaises(bmaya.asset.ProjectError):
                self.tools.new_asset_ui()

    def test_new_project_ui_writes_a_project_json(self):
        folder = os.path.join(self.root, "other", "main")
        with mock.patch.object(self.cmds, "fileDialog2", return_value=[folder]):
            self.tools.new_project_ui()
        self.assertTrue(os.path.isfile(os.path.join(folder, "project.json")))

    def test_asset_id_dialog_starts_with_the_active_rig_asset(self):
        self.build_outside_the_asset(HERO)
        self.cmds.select(clear=True)
        with mock.patch.object(self.tools, "_ask_file", return_value=self.template), \
                mock.patch.object(self.tools, "_ask_text", return_value=HERO) as ask_text:
            self.tools.new_variant_ui()
        self.assertEqual(ask_text.call_args.args[2], HERO)
        self.assertEqual(self.hero.variants, ["game"])

    def test_asset_id_dialog_starts_empty_without_a_rig(self):
        with mock.patch.object(self.tools, "_ask_text", return_value=None) as ask_text:
            self.tools.save_skeleton_ui()
        self.assertEqual(ask_text.call_args.args[2], "")

    def test_shape_menu_tool_uses_the_active_rig(self):
        self.build_outside_the_asset(HERO)
        self.cmds.select(clear=True)
        self.tools.save_control_shapes_ui()
        self.assertTrue(self.hero.file_exists("shapes", "game"))

    def test_build_rig_ui_selects_the_new_rig_root(self):
        self.make_buildable_asset()
        with mock.patch.object(self.tools, "_ask_text", return_value=HERO):
            self.tools.build_rig_ui()
        import rigmodules.query
        self.assertEqual(self.cmds.ls(selection=True), [rigmodules.query.get_rigs("hero")[0].rig_root])


if __name__ == "__main__":
    unittest.main()
