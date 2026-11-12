"""bmaya.maya.assethandlers in mayapy, against the RigModules plugin.

Needs RIGMODULES_PLUGIN, the path of a RigModules.mll (copy it first if a Maya session has the build
loaded, because a loaded plugin locks the file). Skipped without it. Run with tests/asset/run.bat, or:
    mayapy -m unittest discover -s tests/asset -p "test_maya_*.py"
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

try:
    import maya.standalone
except ImportError:
    maya = None

PLUGIN = os.environ.get("RIGMODULES_PLUGIN", "")
HERO = "shooter|main|characters|hero"
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "HandlerTest",
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


class MayaHandlers(unittest.TestCase):

    def setUp(self):
        from maya import cmds
        from bmaya.asset import Asset, Project, handlers
        from bmaya.maya import assethandlers

        self.cmds = cmds
        self.handlers = handlers
        self.assethandlers = assethandlers
        temp = tempfile.mkdtemp(prefix="bmaya_maya_asset_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.root = os.path.join(temp, "projects")
        os.environ["BMAYA_VERSIONS_DIR"] = os.path.join(temp, "local_versions")
        self.addCleanup(os.environ.pop, "BMAYA_VERSIONS_DIR", None)
        Project.create(os.path.join(self.root, "shooter", "main"))
        self.hero = Asset.create(HERO, "Character", root=self.root)

        assethandlers.register()
        for file_type in assethandlers.MAYA_FILE_TYPES + ("shapes", "anims"):
            self.addCleanup(handlers.unregister, file_type)
        cmds.file(new=True, force=True)

    def make_skeleton(self):
        cmds = self.cmds
        cmds.namespace(add=":skel")
        joints = []
        for i, usage in enumerate(("spine1", "spine2")):
            if joints:
                cmds.select(joints[-1], replace=True)
            else:
                cmds.select(clear=True)
            joint = cmds.joint(name=f":skel:{usage}_jnt", position=(0, i * 2, 0))
            cmds.rigJointMarkup(joint, usage=usage, side="Center", export=True, skin=True)
            joints.append(joint)
        return joints

    def build_rig(self):
        path = os.path.join(self.root, "template.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(TEMPLATE, handle)
        self.cmds.createRigFromTemplate(*self.make_skeleton(), template=path.replace("\\", "/"), asset=HERO)
        return "hero:rigRootModule1"

    def test_shapes_save_and_load_through_rigmodules(self):
        cmds = self.cmds
        rig_root = self.build_rig()
        control = "hero:spine1_ctrl_c"
        self.assertEqual(cmds.getAttr(control + ".shapeType", asString=True), "Box")

        path = self.handlers.save(self.hero, "shapes", variant="game", rig_root=rig_root)
        self.assertEqual(path, self.hero.path("shapes", "game"))
        self.assertTrue(os.path.isfile(path))

        cmds.setAttr(control + ".shapeType", 1)  # Sphere
        loaded = self.handlers.load(self.hero, "shapes", variant="game", rig_root=rig_root)
        self.assertIn(control, [c.lstrip(":") for c in loaded])
        self.assertEqual(cmds.getAttr(control + ".shapeType", asString=True), "Box")

        self.handlers.save(self.hero, "shapes", variant="game", rig_root=rig_root)
        from bmaya.asset import versions
        self.assertEqual(len(versions.list_versions(path, self.root)), 1, "the second save keeps the first as a version")

    def test_shapes_need_a_rig_root(self):
        self.build_rig()
        with self.assertRaises(ValueError):
            self.handlers.save(self.hero, "shapes", variant="game")

    def test_scene_saves_and_imports_into_the_asset_namespace(self):
        cmds = self.cmds
        self.make_skeleton()
        path = self.handlers.save(self.hero, "skeleton")
        self.assertTrue(os.path.isfile(path))

        cmds.file(new=True, force=True)
        nodes = self.handlers.load(self.hero, "skeleton")
        self.assertIn("|hero:skel:spine1_jnt", nodes)
        self.assertTrue(cmds.objExists("hero:skel:spine2_jnt"))

        # A second load merges into the namespace the asset owns instead of making hero1.
        self.handlers.load(self.hero, "skeleton")
        self.assertFalse(cmds.namespace(exists=":hero1"))

        self.handlers.load(self.hero, "skeleton", namespace="hero2")
        self.assertTrue(cmds.objExists("hero2:skel:spine1_jnt"))

    # ---- animation clips ---------------------------------------------------------------------

    def write_joint_clip(self, name="source.json", poses=2):
        """A hand-written JointClip: a hips joint that rises 1 cm per frame, and an unmarked child."""
        identity = {"translate": [0, 0, 0], "rotate": [0, 0, 0, 1], "scale": [1, 1, 1]}
        markup = '{"markupVersion":1,"usage":"hips","side":"Center","export":true,"skin":true}'
        clip = {
            "formatVersion": 1,
            "frameRate": 30.0,
            "startFrame": 1,
            "joints": [
                {"path": "hips", "markup": markup, "rest": dict(identity, translate=[0, 100, 0])},
                {"path": "hips/tip", "markup": "", "rest": dict(identity, translate=[0, 10, 0])},
            ],
            "poses": [
                [dict(identity, translate=[0, 100 + frame, 0]), dict(identity, translate=[0, 10, 0])]
                for frame in range(poses)
            ],
        }
        path = os.path.join(self.root, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(clip, handle)
        return path

    def read_json(self, path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_a_clip_saves_as_usd_in_the_anims_folder_and_loads_back(self):
        path = self.handlers.save(self.hero, "anims", name="walk", joint_clip=self.write_joint_clip())
        self.assertEqual(path, self.hero.path("anims"))
        usd = os.path.join(path, "walk.usd")
        self.assertTrue(os.path.isfile(usd))

        clip = self.handlers.load(self.hero, "anims", name="walk")
        self.assertEqual((clip.name, clip.usd, clip.sidecar), ("walk", usd, None))
        data = self.read_json(clip.joint_clip)
        self.assertEqual(len(data["poses"]), 2)
        self.assertEqual([joint["path"] for joint in data["joints"]], ["hips", "hips/tip"])
        self.assertAlmostEqual(data["poses"][1][0]["translate"][1], 101, places=4)

    def test_a_clip_can_be_captured_from_a_rig(self):
        cmds = self.cmds
        rig_root = self.build_rig()
        cmds.setKeyframe("hero:spine1_ctrl_c.translateY", time=1, value=0)
        cmds.setKeyframe("hero:spine1_ctrl_c.translateY", time=3, value=4)
        usd = self.assethandlers.save_anim_clip(self.hero, "rise", rig_root=rig_root, start_frame=1, end_frame=3)
        self.assertEqual(usd, os.path.join(self.hero.path("anims"), "rise.usd"))

        data = self.read_json(self.handlers.load(self.hero, "anims", name="rise").joint_clip)
        self.assertEqual(len(data["poses"]), 3)
        self.assertEqual({joint["path"] for joint in data["joints"]}, {"spine1_jnt", "spine1_jnt/spine2_jnt"})
        self.assertEqual([name for name in os.listdir(tempfile.gettempdir()) if name.endswith(".jointclip.json")], [])

    def test_a_sidecar_is_copied_beside_the_usd_and_loaded_with_it(self):
        sidecar = os.path.join(self.root, "source.rigdata.json")
        with open(sidecar, "w", encoding="utf-8") as handle:
            json.dump({"formatVersion": 1, "frameRate": 30, "frames": {}}, handle)
        self.handlers.save(self.hero, "anims", name="walk", joint_clip=self.write_joint_clip(), sidecar=sidecar)
        folder = self.hero.path("anims")
        self.assertEqual(sorted(os.listdir(folder)), ["walk.rigdata.json", "walk.usd"])
        self.assertEqual(self.handlers.load(self.hero, "anims", name="walk").sidecar,
                         os.path.join(folder, "walk.rigdata.json"))

    def test_saving_a_clip_without_a_sidecar_removes_the_old_ones(self):
        sidecar = os.path.join(self.root, "source.rigdata.json")
        with open(sidecar, "w", encoding="utf-8") as handle:
            json.dump({"formatVersion": 1, "frameRate": 30, "frames": {}}, handle)
        self.handlers.save(self.hero, "anims", name="walk", joint_clip=self.write_joint_clip(), sidecar=sidecar)
        self.handlers.save(self.hero, "anims", name="walk", joint_clip=self.write_joint_clip())
        self.assertEqual(os.listdir(self.hero.path("anims")), ["walk.usd"])

    def test_save_anim_clip_versions_only_that_clips_files(self):
        from bmaya.asset import versions
        module = self.assethandlers
        source = self.write_joint_clip()
        module.save_anim_clip(self.hero, "walk", joint_clip=source)
        module.save_anim_clip(self.hero, "run", joint_clip=source)
        usd = os.path.join(self.hero.path("anims"), "walk.usd")
        self.assertEqual(versions.list_versions(usd, self.root), [], "a first save has nothing to version")

        module.save_anim_clip(self.hero, "walk", joint_clip=self.write_joint_clip(poses=3))
        self.assertEqual(len(versions.list_versions(usd, self.root)), 1)
        self.assertEqual(versions.list_versions(os.path.join(self.hero.path("anims"), "run.usd"), self.root), [])
        self.assertEqual(len(self.read_json(self.handlers.load(self.hero, "anims", name="walk").joint_clip)["poses"]), 3)
        self.assertEqual(module.AnimClipHandler.names(self.hero.path("anims")), ["run", "walk"])

    def test_clip_arguments_are_checked_before_anything_is_written(self):
        source = self.write_joint_clip()
        for kwargs in (
            {"name": None, "joint_clip": source},
            {"name": "../walk", "joint_clip": source},
            {"name": "walk"},
            {"name": "walk", "joint_clip": source, "rig_root": "hero:rigRootModule1"},
            {"name": "walk", "rig_root": "hero:rigRootModule1"},
            {"name": "walk", "joint_clip": source, "sidecar": os.path.join(self.root, "missing.json")},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, FileNotFoundError)):
                self.handlers.save(self.hero, "anims", **kwargs)
        self.assertFalse(os.path.exists(os.path.join(self.hero.path("anims"), "walk.usd")))

    def test_loading_a_clip_that_is_not_there_names_the_clips_that_are(self):
        self.handlers.save(self.hero, "anims", name="walk", joint_clip=self.write_joint_clip())
        with self.assertRaisesRegex(FileNotFoundError, "no clip 'run'.*walk"):
            self.handlers.load(self.hero, "anims", name="run")


if __name__ == "__main__":
    unittest.main()
