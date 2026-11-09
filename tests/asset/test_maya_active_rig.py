"""bmaya.maya.activerig in mayapy: the rig the RigModules menu tools act on (RigModules D30).

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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

try:
    import maya.standalone
except ImportError:
    maya = None

PLUGIN = os.environ.get("RIGMODULES_PLUGIN", "")
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "ActiveRigTest",
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


class ActiveRig(unittest.TestCase):

    def setUp(self):
        from maya import cmds
        import bmaya.maya.activerig

        self.cmds = cmds
        self.activerig = bmaya.maya.activerig
        temp = tempfile.mkdtemp(prefix="bmaya_active_rig_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.template = os.path.join(temp, "template.json").replace("\\", "/")
        with open(self.template, "w", encoding="utf-8") as handle:
            json.dump(TEMPLATE, handle)
        cmds.file(new=True, force=True)

    def tearDown(self):
        tracker = self.activerig.ActiveRigTracker.current()
        if tracker is not None:
            tracker.stop()

    def build(self, asset_id):
        """Builds the template on a new two-joint skeleton. Returns the rig root and the joints."""
        cmds = self.cmds
        cmds.select(clear=True)
        name = asset_id.split("|")[-1]
        joints = []
        for i, usage in enumerate(("spine1", "spine2")):
            joint = cmds.joint(name=f"{usage}_jnt", position=(0, i * 2, 0))
            cmds.rigJointMarkup(joint, usage=usage, side="Center", export=True, skin=True)
            joints.append(joint)
        cmds.createRigFromTemplate(*joints, template=self.template, asset=asset_id)
        import rigmodules.query
        rig_root = rigmodules.query.get_rigs(name)[0].rig_root
        return rig_root, [f"{name}:{joint}" for joint in joints]

    def test_selected_control_joint_or_root_finds_the_rig(self):
        rig_root, joints = self.build("shooter|hero")
        for node in ("hero:spine1_ctrl_c", joints[1], rig_root):
            with self.subTest(node=node):
                self.cmds.select(node, replace=True)
                self.assertEqual(self.activerig.rig_from_selection().rig_root, rig_root)

    def test_last_selected_rig_node_wins(self):
        hero, _ = self.build("shooter|hero")
        villain, _ = self.build("shooter|villain")
        self.cmds.select(["hero:spine1_ctrl_c", "villain:spine1_ctrl_c"], replace=True)
        self.assertEqual(self.activerig.rig_from_selection().rig_root, villain)
        cube = self.cmds.polyCube()[0]
        self.cmds.select(["hero:spine1_ctrl_c", cube], replace=True)
        self.assertEqual(self.activerig.rig_from_selection().rig_root, hero)

    def test_components_and_other_nodes_find_no_rig(self):
        cube = self.cmds.polyCube()[0]
        self.cmds.select(cube + ".vtx[0]", replace=True)
        self.assertIsNone(self.activerig.rig_from_selection())

    def test_without_a_tracker_falls_back_to_the_first_rig(self):
        hero, _ = self.build("shooter|hero")
        self.build("shooter|villain")
        self.cmds.select(clear=True)
        self.assertEqual(self.activerig.get_active_rig().rig_root, hero)

    def test_no_rig_in_the_scene_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "no RigModules rig"):
            self.activerig.get_active_rig()

    def test_tracker_keeps_the_last_selected_rig(self):
        """Drives the real SelectionChanged callback, which mayapy fires on cmds.select."""
        hero, _ = self.build("shooter|hero")
        villain, _ = self.build("shooter|villain")
        tracker = self.activerig.ActiveRigTracker()
        self.cmds.select("villain:spine1_ctrl_c", replace=True)
        self.cmds.select(self.cmds.polyCube()[0], replace=True)
        self.assertEqual(tracker.rig_root, villain)
        self.cmds.select("hero:spine2_ctrl_c", replace=True)
        self.assertEqual(tracker.rig_root, hero)

    def test_tracker_resets_on_a_new_scene(self):
        self.build("shooter|hero")
        tracker = self.activerig.ActiveRigTracker()
        self.cmds.file(new=True, force=True)
        self.assertIsNone(tracker.rig_root)

    def test_deleted_active_rig_falls_back(self):
        hero, _ = self.build("shooter|hero")
        villain, _ = self.build("shooter|villain")
        tracker = self.activerig.ActiveRigTracker()
        tracker.set_rig_root(villain)
        self.cmds.delete(villain)
        self.cmds.select(clear=True)
        self.assertEqual(self.activerig.get_active_rig().rig_root, hero)
        self.assertEqual(tracker.rig_root, hero)

    def test_tracker_registers_and_stops_its_callbacks(self):
        import bmaya.maya.eventsregistry
        registry = bmaya.maya.eventsregistry.EventsRegistry()
        tracker = self.activerig.ActiveRigTracker()
        self.assertIs(self.activerig.ActiveRigTracker(), tracker)
        keys = {self.activerig.SELECTION_CALLBACK, self.activerig.SCENE_NEW_CALLBACK, self.activerig.SCENE_OPEN_CALLBACK}
        self.assertTrue(keys <= set(registry.active_callbacks))
        tracker.stop()
        self.assertFalse(keys & set(registry.active_callbacks))
        self.assertIsNone(self.activerig.ActiveRigTracker.current())


if __name__ == "__main__":
    unittest.main()
