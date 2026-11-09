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
        temp = tempfile.mkdtemp(prefix="bmaya_maya_asset_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.root = os.path.join(temp, "projects")
        os.environ["BMAYA_VERSIONS_DIR"] = os.path.join(temp, "local_versions")
        self.addCleanup(os.environ.pop, "BMAYA_VERSIONS_DIR", None)
        Project.create(os.path.join(self.root, "shooter", "main"))
        self.hero = Asset.create(HERO, "Character", root=self.root)

        assethandlers.register()
        for file_type in assethandlers.MAYA_FILE_TYPES + ("shapes",):
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


if __name__ == "__main__":
    unittest.main()
