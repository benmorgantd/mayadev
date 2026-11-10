"""The RigModules menu: toolsets/rigmodules_menu.json and its scripts in master_tool_registry.json.

The layout tests need only Python. The script tests exec each registry script the way ToolMenu does,
in mayapy against RIGMODULES_PLUGIN, the path of a RigModules.mll (copy it first if a Maya session
has the build loaded, because a loaded plugin locks the file). They skip without it. Run with run.bat.
"""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

try:
    import maya.standalone
except ImportError:
    maya = None

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "toolsets")
PLUGIN = os.environ.get("RIGMODULES_PLUGIN", "")
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "MenuTest",
    "rigName": "game",
    "rigAuthor": "tests",
    "rigModules": [
        {"moduleType": "FkChain", "name": "spine", "shapeType": "Box",
         "moduleArgs": {"joints": [["Center", "spine1"]]}},
        {"moduleType": "FkChain", "name": "arm_l", "side": "Left", "shapeType": "Circle", "mirror": True,
         "moduleArgs": {"joints": [["Left", "arm"]]}, "parentStructure": {"start": "spine.end"}},
    ],
}


def _load(name):
    with open(os.path.join(TOOLS, name), encoding="utf-8") as handle:
        return json.load(handle)


def _walk(items):
    """Every menu item, depth first, descending into submenus."""
    for item in items:
        yield item
        if item["type"] == "submenu":
            yield from _walk(item["items"])


def _menu_tools():
    """The registry entries the menu lists, by name, in menu order."""
    registry = {tool["guid"]: tool for tool in _load("master_tool_registry.json")["tools"]}
    items = _walk(_load("rigmodules_menu.json")["items"])
    return {registry[item["guid"]]["name"]: registry[item["guid"]] for item in items if item["type"] == "tool"}


class MenuLayout(unittest.TestCase):

    def test_every_menu_tool_is_in_the_registry(self):
        registry = {tool["guid"] for tool in _load("master_tool_registry.json")["tools"]}
        for item in _walk(_load("rigmodules_menu.json")["items"]):
            self.assertIn(item["type"], ("tool", "separator", "submenu"))
            if item["type"] == "tool":
                self.assertIn(item["guid"], registry)

    def test_top_level_is_submenus_in_order(self):
        items = _load("rigmodules_menu.json")["items"]
        self.assertEqual([i["type"] for i in items], ["submenu"] * len(items))
        self.assertEqual([i["label"] for i in items], ["asset", "mesh", "joints", "weights", "shapes", "control", "dev"])

    def test_every_registry_tool_is_in_the_menu_once(self):
        guids = [i["guid"] for i in _walk(_load("rigmodules_menu.json")["items"]) if i["type"] == "tool"]
        self.assertEqual(len(guids), len(set(guids)))
        self.assertEqual(len(guids), 21)

    def test_every_script_compiles(self):
        for name, tool in _menu_tools().items():
            with self.subTest(name):
                compile(tool["script"], name, "exec")


class MenuScripts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if maya is None:
            raise unittest.SkipTest("needs mayapy")
        if not os.path.isfile(PLUGIN):
            raise unittest.SkipTest("set RIGMODULES_PLUGIN to a RigModules.mll")
        maya.standalone.initialize(name="python")
        from maya import cmds
        if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
            cmds.loadPlugin(PLUGIN)
        cls.cmds = cmds
        cls.tools = _menu_tools()

    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix="bmaya_rigmodules_menu_")
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.cmds.file(new=True, force=True)
        path = os.path.join(self.temp, "template.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(TEMPLATE, handle)
        self.cmds.createRigFromTemplate(*self.make_skeleton(), template=path.replace("\\", "/"), asset="shooter|hero")
        # The build moves the joints into the asset's namespace, so look them up afterwards.
        self.joints = self.cmds.ls(type="joint")
        self.root = "hero:rigRootModule1"
        self.left = self.cmds.getRigControls(self.root, side="Left")[0]
        self.right = self.cmds.getRigControls(self.root, side="Right")[0]

    def make_skeleton(self):
        cmds = self.cmds
        cmds.namespace(add=":skel")
        cmds.select(clear=True)
        spine = cmds.joint(name=":skel:spine1_jnt", position=(0, 10, 0))
        cmds.rigJointMarkup(spine, usage="spine1", side="Center", export=True, skin=True)
        joints = [spine]
        for side, x in (("Left", 2), ("Right", -2)):
            cmds.select(spine, replace=True)
            joint = cmds.joint(name=f":skel:arm_{side[0].lower()}_jnt", position=(x, 10, 0))
            cmds.rigJointMarkup(joint, usage="arm", side=side, export=True, skin=True)
            joints.append(joint)
        return joints

    def run_tool(self, name, selection):
        """Runs a registry script as the menu does: exec, with the selection set first."""
        if selection:
            self.cmds.select(selection, replace=True)
        else:
            self.cmds.select(clear=True)
        exec(self.tools[name]["script"], {})

    def selected(self):
        return [node.lstrip(":") for node in self.cmds.ls(sl=True)]

    def test_print_joint_markup_prints_each_joint(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.run_tool("Print Joint Markup", self.joints)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), len(self.joints))
        self.assertIn('hero:spine1_jnt: {"export":true,"markupVersion":1,"side":"Center","skin":true,"usage":"spine1"}', lines)

    def test_remove_joint_markup(self):
        self.run_tool("Remove Joint Markup", self.joints[:1])
        self.assertEqual(self.cmds.rigJointMarkup(self.joints[0], query=True, usage=True), [""])

    def test_joint_tools_need_joints(self):
        with self.assertRaises(RuntimeError):
            self.run_tool("Print Joint Markup", self.root)

    def test_select_all_controls(self):
        self.run_tool("Select All Controls", self.root)
        expected = [c.lstrip(":") for c in self.cmds.getRigControls(self.root)]
        self.assertEqual(sorted(self.selected()), sorted(expected))

    def test_rig_tools_act_on_the_active_rig_without_selecting_its_root(self):
        expected = sorted(c.lstrip(":") for c in self.cmds.getRigControls(self.root))
        for selection in ([self.left], [self.joints[0]], []):
            with self.subTest(selection=selection):
                self.run_tool("Select All Controls", selection or None)
                self.assertEqual(sorted(self.selected()), expected)

    def test_rig_tools_need_a_rig_in_the_scene(self):
        self.cmds.file(new=True, force=True)
        with self.assertRaisesRegex(RuntimeError, "no RigModules rig"):
            self.run_tool("Select All Controls", None)

    def test_select_mirror_controls(self):
        self.run_tool("Select Mirror Controls", [self.left])
        self.assertEqual(self.selected(), [self.right.lstrip(":")])

    def test_mirror_shapes_both_directions(self):
        cmds = self.cmds
        cmds.setAttr(self.left + ".shapeType", 1)  # Sphere
        self.run_tool("Mirror Shapes Left to Right", self.root)
        self.assertEqual(cmds.getAttr(self.right + ".shapeType"), 1)

        cmds.setAttr(self.right + ".shapeType", 0)
        self.run_tool("Mirror Shapes Right to Left", self.root)
        self.assertEqual(cmds.getAttr(self.left + ".shapeType"), 0)

    def test_save_and_load_shapes_through_the_file_dialog(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "shapes.json").replace("\\", "/")
        before = cmds.getAttr(self.left + ".shapeType")
        with mock.patch.object(cmds, "fileDialog2", return_value=[path]):
            self.run_tool("Save Control Shapes...", self.root)
            self.assertTrue(os.path.isfile(path))
            cmds.setAttr(self.left + ".shapeType", (before + 1) % 2)
            self.run_tool("Load Control Shapes...", self.root)
        self.assertEqual(cmds.getAttr(self.left + ".shapeType"), before)

    def make_skinned_box(self):
        cmds = self.cmds
        box = cmds.polyCube(name=":hero:box_geo", constructionHistory=False)[0]
        cluster = cmds.skinCluster("hero:spine1_jnt", "hero:arm_l_jnt", box, toSelectedBones=True)[0]
        return box, cluster

    def test_mark_meshes_for_skinning_and_new_ids(self):
        box, _ = self.make_skinned_box()
        self.run_tool("Mark Meshes for Skinning", [box, self.joints[0]])
        first = self.cmds.getAttr(box + ".meshId")
        self.assertTrue(first)
        self.run_tool("Mark Meshes with New Ids", [box])
        self.assertNotEqual(self.cmds.getAttr(box + ".meshId"), first)

    def test_save_and_load_skin_weights_through_the_folder_dialog(self):
        cmds = self.cmds
        box, cluster = self.make_skinned_box()
        self.run_tool("Mark Meshes for Skinning", [box])
        folder = os.path.join(self.temp, "weights")
        with mock.patch.object(cmds, "fileDialog2", return_value=[folder]):
            self.run_tool("Save Skin Weights...", self.root)
            self.assertEqual(os.listdir(folder), ["box_geo.json"])
            cmds.delete(cluster)
            self.run_tool("Load Skin Weights...", self.root)
        self.assertTrue(cmds.ls(cmds.listHistory(box), type="skinCluster"))

    def test_cancelled_file_dialog_does_nothing(self):
        with mock.patch.object(self.cmds, "fileDialog2", return_value=None):
            self.run_tool("Save Control Shapes...", self.root)
        self.assertEqual(os.listdir(self.temp), ["template.json"])


if __name__ == "__main__":
    unittest.main()
