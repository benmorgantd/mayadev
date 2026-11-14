"""The RigModules menu: toolsets/rigmodules_menu.json and its tools in master_tool_registry.json.

The layout tests need only Python. The tool tests run each registry tool the way ToolMenu does (run_tool),
in mayapy against RIGMODULES_PLUGIN, the path of a RigModules.mll (copy it first if a Maya session
has the build loaded, because a loaded plugin locks the file). They skip without it. The call checks import
every tool module, so they need mayapy but not the plugin. Run with run.bat.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "py", "scripts"))

from bmaya.core import tool_registry  # noqa: E402

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


def _registry():
    return tool_registry.read_registry(os.path.join(TOOLS, "master_tool_registry.json"))


def _layout(name="rigmodules_menu.json"):
    return tool_registry.read_layout(os.path.join(TOOLS, name), _registry().tools)


def _menu_tools():
    """The registry's tools that the RigModules menu lists, by name, in menu order."""
    registry = _registry()
    return {registry.tools[item.tool].name: registry.tools[item.tool] for item in _layout().tool_items()}


class MenuLayout(unittest.TestCase):

    def test_every_menu_tool_is_in_the_registry(self):
        # read_layout refuses a layout that names a tool the registry doesn't have
        self.assertTrue(list(_layout().tool_items()))

    def test_top_level_is_submenus_in_order(self):
        items = _layout().items
        self.assertEqual([type(i) for i in items], [tool_registry.Submenu] * len(items))
        self.assertEqual([i.label for i in items], ["panels", "asset", "mesh", "joints", "weights", "shapes", "control", "pose", "clip"])

    def test_every_tool_is_in_the_menu_once(self):
        ids = [item.tool for item in _layout().tool_items()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 39)

    def test_the_dev_tools_are_in_the_bmaya_menu(self):
        ids = [item.tool for item in _layout("bmaya_menu.json").tool_items()]
        for tool_id in ("bmaya.dev.reload_rigmodules", "bmaya.dev.unload_rigmodules", "bmaya.dev.reload_menu"):
            self.assertIn(tool_id, ids)


class RegistryCalls(unittest.TestCase):
    """Imports every tool module, so it needs mayapy and the rigmodules package, but not the plugin."""

    @classmethod
    def setUpClass(cls):
        if maya is None:
            raise unittest.SkipTest("needs mayapy")
        maya.standalone.initialize(name="python")

    def test_every_registry_call_resolves_and_binds_to_its_function(self):
        issues = tool_registry.check_calls(_registry())
        self.assertEqual([f"{i.where}: {i.message}" for i in issues], [])


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
        self.cmds.createRigFromTemplate(*self.make_skeleton(), template=path.replace("\\", "/"), asset="shooter\\hero")
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

    @contextlib.contextmanager
    def answers(self, *answers):
        """Answers the tools' questions in order for the block, through the session's prompter slot, as a GUI
        session's Qt prompter would. Every answer must be used."""
        import bmaya.core.prompts
        prompter = bmaya.core.prompts.ScriptedPrompter(answers)
        bmaya.core.prompts.register_prompter(prompter)
        try:
            yield prompter
        finally:
            bmaya.core.prompts.reset_prompter()
        self.assertEqual(prompter.remaining, 0, f"unused answers; asked: {prompter.asked}")

    def run_tool(self, name, selection):
        """Runs a registry tool as the menu does (run_tool), with the selection set first."""
        if selection:
            self.cmds.select(selection, replace=True)
        else:
            self.cmds.select(clear=True)
        tool_registry.run_tool(self.tools[name])

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
        with self.answers(path, path):
            self.run_tool("Save Control Shapes...", self.root)
            self.assertTrue(os.path.isfile(path))
            cmds.setAttr(self.left + ".shapeType", (before + 1) % 2)
            self.run_tool("Load Control Shapes...", self.root)
        self.assertEqual(cmds.getAttr(self.left + ".shapeType"), before)

    def test_mirror_pose_goes_from_the_selected_controls_side(self):
        cmds = self.cmds
        cmds.setAttr(self.left + ".rotateY", 20)
        cmds.setAttr(self.right + ".rotateY", -5)
        self.run_tool("Mirror Pose", [self.left])
        self.assertEqual(cmds.getAttr(self.right + ".rotateY"), 20)

        self.run_tool("Mirror Pose", [self.right])   # the Right control is now the source, and it holds 20 as well
        cmds.setAttr(self.right + ".rotateY", 7)
        self.run_tool("Mirror Pose", [self.right])
        self.assertEqual(cmds.getAttr(self.left + ".rotateY"), 7)

    def test_mirror_pose_both_directions_on_the_whole_rig(self):
        cmds = self.cmds
        cmds.setAttr(self.left + ".rotateY", 20)
        self.run_tool("Mirror Pose Left to Right", None)
        self.assertEqual(cmds.getAttr(self.right + ".rotateY"), 20)
        cmds.setAttr(self.right + ".rotateY", 9)
        self.run_tool("Mirror Pose Right to Left", None)
        self.assertEqual(cmds.getAttr(self.left + ".rotateY"), 9)

    def test_flip_pose_swaps_the_sides(self):
        cmds = self.cmds
        cmds.setAttr(self.left + ".rotateY", 20)
        cmds.setAttr(self.right + ".rotateY", 3)
        self.run_tool("Flip Pose", None)
        self.assertAlmostEqual(cmds.getAttr(self.left + ".rotateY"), 3)
        self.assertAlmostEqual(cmds.getAttr(self.right + ".rotateY"), 20)

    def test_zero_pose_acts_on_the_selection_only(self):
        cmds = self.cmds
        cmds.setAttr(self.left + ".rotateY", 20)
        cmds.setAttr(self.right + ".rotateY", 20)
        self.run_tool("Zero Pose", [self.left])
        self.assertEqual(cmds.getAttr(self.left + ".rotateY"), 0)
        self.assertEqual(cmds.getAttr(self.right + ".rotateY"), 20)

    def test_save_and_load_pose_through_the_file_dialog(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "pose.json").replace("\\", "/")
        cmds.setAttr(self.left + ".rotateY", 20)
        with self.answers(path, path):
            self.run_tool("Save Pose...", None)
            self.assertTrue(os.path.isfile(path))
            cmds.setAttr(self.left + ".rotateY", 0)
            self.run_tool("Load Pose...", None)
        self.assertEqual(cmds.getAttr(self.left + ".rotateY"), 20)

    def read_fbx(self, path):
        import rigmodules.jointclip
        out = os.path.join(self.temp, "read.json")
        rigmodules.jointclip.read_fbx(path, out)
        with open(out, encoding="utf-8") as handle:
            return json.load(handle)

    def test_capture_joint_clip_writes_an_fbx_of_the_export_joints_over_the_playback_range(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "walk.fbx").replace("\\", "/")
        cmds.playbackOptions(minTime=1, maxTime=4)
        with self.answers(path):
            self.run_tool("Capture Joint Clip...", None)
        clip = self.read_fbx(path)
        self.assertEqual(clip["startFrame"], 1)
        self.assertEqual(len(clip["poses"]), 4)
        self.assertEqual(sorted(joint["path"] for joint in clip["joints"]), ["spine1_jnt", "spine1_jnt/arm_l_jnt", "spine1_jnt/arm_r_jnt"])

    def test_capture_joint_pose_writes_an_fbx_with_one_frame(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "idle.fbx").replace("\\", "/")
        cmds.currentTime(7)
        with self.answers(path):
            self.run_tool("Capture Joint Pose...", None)
        clip = self.read_fbx(path)
        # a pose is a one-frame animation (RigModules D42), so it keeps the frame it was captured on
        self.assertEqual((clip["startFrame"], len(clip["poses"])), (7, 1))

    def test_a_captured_pose_restores_the_controls(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "idle.fbx").replace("\\", "/")
        cmds.setAttr(self.left + ".rotateY", 20)
        with self.answers(path, path):
            self.run_tool("Capture Joint Pose...", None)
            cmds.setAttr(self.left + ".rotateY", 0)
            self.run_tool("Pose From Joint Pose...", None)
        self.assertAlmostEqual(cmds.getAttr(self.left + ".rotateY"), 20, places=2)
        self.assertEqual(cmds.keyframe(self.left, query=True, keyframeCount=True), 0)

    def test_a_captured_clip_keys_the_controls(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "walk.fbx").replace("\\", "/")
        cmds.setKeyframe(self.left + ".rotateY", time=1, value=0, inTangentType="linear", outTangentType="linear")
        cmds.setKeyframe(self.left + ".rotateY", time=3, value=60, inTangentType="linear", outTangentType="linear")
        cmds.playbackOptions(minTime=1, maxTime=3)
        with self.answers(path, path):
            self.run_tool("Capture Joint Clip...", None)
            cmds.cutKey(self.left, attribute="rotateY", clear=True)
            cmds.setAttr(self.left + ".rotateY", 0)
            self.run_tool("Animate From Joint Clip...", None)
        self.assertAlmostEqual(cmds.getAttr(self.left + ".rotateY", time=2), 30, places=2)
        self.assertAlmostEqual(cmds.getAttr(self.left + ".rotateY", time=3), 60, places=2)

    def test_joint_clip_tools_reject_a_file_that_is_not_fbx(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "bad.fbx").replace("\\", "/")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{}")
        with self.answers(path, path):
            for name in ("Pose From Joint Pose...", "Animate From Joint Clip..."):
                with self.subTest(name):
                    with self.assertRaises(Exception):
                        self.run_tool(name, None)

    def test_save_and_load_animation_through_the_file_dialog(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "anim.json").replace("\\", "/")
        cmds.setKeyframe(self.left + ".rotateY", time=1, value=0)
        cmds.setKeyframe(self.left + ".rotateY", time=3, value=60)
        cmds.playbackOptions(minTime=1, maxTime=3)
        with self.answers(path, path):
            self.run_tool("Save Animation...", None)
            self.assertTrue(os.path.isfile(path))
            cmds.cutKey(self.left, attribute="rotateY", clear=True)
            self.run_tool("Load Animation...", None)
        self.assertEqual(cmds.keyframe(self.left + ".rotateY", query=True, timeChange=True), [1, 3])
        self.assertAlmostEqual(cmds.getAttr(self.left + ".rotateY", time=3), 60, places=3)
        self.assertEqual(cmds.keyframe(self.right + ".rotateY", query=True, keyframeCount=True), 0)

    def test_load_animation_mirrored_puts_the_left_keys_on_the_right(self):
        cmds = self.cmds
        path = os.path.join(self.temp, "anim.json").replace("\\", "/")
        cmds.setKeyframe(self.left + ".rotateY", time=1, value=20)
        cmds.playbackOptions(minTime=1, maxTime=1)
        with self.answers(path, path):
            self.run_tool("Save Animation...", None)
            cmds.cutKey(self.left, attribute="rotateY", clear=True)
            self.run_tool("Load Animation Mirrored...", None)
        self.assertEqual(cmds.keyframe(self.right + ".rotateY", query=True, keyframeCount=True), 1)
        self.assertEqual(cmds.keyframe(self.left + ".rotateY", query=True, keyframeCount=True), 0)

    def test_the_skeleton_and_clip_tools_need_the_assets_folder(self):
        import bmaya.core.asset
        import bmaya.maya.assettools
        cmds = self.cmds
        path = os.path.join(self.temp, "walk.fbx").replace("\\", "/")
        with mock.patch.object(bmaya.maya.assettools, "find_asset", return_value=None),                 mock.patch.object(bmaya.core.asset.Asset, "exists", return_value=False),                 self.answers(path):
            for name in ("Save Skeleton Export", "Check Clip Against Skeleton..."):
                with self.subTest(name):
                    with self.assertRaisesRegex(bmaya.core.asset.AssetError, "New Asset"):
                        self.run_tool(name, None)

    def test_edit_clip_properties_writes_the_file_beside_the_fbx(self):
        import bmaya.core.asset.animproperties as animproperties
        import bmaya.maya.assettools
        path = os.path.join(self.temp, "walk.fbx").replace("\\", "/")
        with self.answers(path, bmaya.maya.assettools.ClipSettings(loop=True, root_motion=False, additive="local")) as asked:
            self.run_tool("Edit Clip Properties...", None)
        self.assertEqual(asked.asked[1].default, bmaya.maya.assettools.ClipSettings(), "the form starts at the defaults")
        properties = animproperties.read(animproperties.get_path(path))
        self.assertEqual((properties.loop, properties.root_motion, properties.additive), (True, False, "local"))

    def test_cancelled_joint_pose_dialog_does_nothing(self):
        with self.answers(*[None] * 9):
            self.run_tool("Pose From Joint Pose...", None)
            self.run_tool("Animate From Joint Clip...", None)
            self.run_tool("Capture Joint Clip...", None)
            self.run_tool("Capture Joint Pose...", None)
            self.run_tool("Save Animation...", None)
            self.run_tool("Load Animation...", None)
            self.run_tool("Load Animation Mirrored...", None)
            self.run_tool("Check Clip Against Skeleton...", None)
            self.run_tool("Edit Clip Properties...", None)
        self.assertEqual(os.listdir(self.temp), ["template.json"])

    def test_cancelled_pose_dialog_does_nothing(self):
        with self.answers(None):
            self.run_tool("Save Pose...", None)
        self.assertEqual(os.listdir(self.temp), ["template.json"])

    def test_pose_tools_never_key(self):
        self.cmds.setAttr(self.left + ".rotateY", 20)
        for name in ("Mirror Pose", "Flip Pose", "Zero Pose"):
            self.run_tool(name, None)
        self.assertEqual(self.cmds.ls(type="animCurve"), [])

    def test_key_all_controls_keys_every_control_without_a_selection(self):
        self.run_tool("Key All Controls", None)
        for control in self.cmds.getRigControls(self.root):
            self.assertTrue(self.cmds.keyframe(control, query=True, name=True), control)

    def test_key_selected_modules_keys_the_module_of_a_selected_control(self):
        self.run_tool("Key Selected Modules", [self.left])
        self.assertTrue(self.cmds.keyframe(self.left, query=True, name=True))
        self.assertFalse(self.cmds.keyframe(self.right, query=True, name=True))

    def test_key_selected_modules_accepts_a_module_node(self):
        module = self.cmds.listConnections(self.left + ".rigModule", source=True, destination=False)[0]
        self.run_tool("Key Selected Modules", [module])
        self.assertTrue(self.cmds.keyframe(self.left, query=True, name=True))
        self.assertFalse(self.cmds.keyframe(self.right, query=True, name=True))

    def test_key_selected_modules_needs_a_selection(self):
        with self.assertRaisesRegex(RuntimeError, "Select modules"):
            self.run_tool("Key Selected Modules", None)

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
        with self.answers(folder, folder):
            self.run_tool("Save Skin Weights...", self.root)
            self.assertEqual(os.listdir(folder), ["box_geo.json"])
            cmds.delete(cluster)
            self.run_tool("Load Skin Weights...", self.root)
        self.assertTrue(cmds.ls(cmds.listHistory(box), type="skinCluster"))

    def run_bmaya_tool(self, tool_id, selection):
        """Runs a tool of the bmaya menu, with the selection set first."""
        self.cmds.select(selection, replace=True)
        tool_registry.run_tool(_registry().tools[tool_id])

    def test_zero_transforms_freezes_the_selection_without_moving_it(self):
        cmds = self.cmds
        cube = cmds.polyCube(constructionHistory=False)[0]
        cmds.move(1, 2, 3, cube)
        cmds.rotate(0, 30, 0, cube)
        self.run_bmaya_tool("bmaya.joints.zero_transforms", [cube])
        for channel in ("translate", "rotate"):
            self.assertEqual(cmds.getAttr(f"{cube}.{channel}")[0], (0, 0, 0))
        box = cmds.exactWorldBoundingBox(cube)
        self.assertAlmostEqual((box[0] + box[3]) / 2, 1, places=4)
        self.assertAlmostEqual((box[1] + box[4]) / 2, 2, places=4)

    def test_orient_to_world_clears_the_joints_world_rotation(self):
        cmds = self.cmds
        cmds.select(clear=True)
        joint = cmds.joint(name="orient_test_jnt", position=(0, 0, 0))
        cmds.setAttr(joint + ".jointOrient", 30, 40, 50)
        self.run_bmaya_tool("bmaya.joints.orient_to_world", [joint])
        rotation = cmds.xform(joint, query=True, worldSpace=True, rotation=True)
        for value in rotation:
            self.assertAlmostEqual(value, 0, places=3)

    def test_orient_to_mesh_passes_the_joints_and_the_last_selected_mesh(self):
        import bmaya.maya.rigging.joint
        cmds = self.cmds
        plane = cmds.polyPlane(constructionHistory=False)[0]
        cmds.select(clear=True)
        first = cmds.joint(name="orient_mesh_a_jnt")
        cmds.select(clear=True)
        second = cmds.joint(name="orient_mesh_b_jnt")
        with mock.patch.object(bmaya.maya.rigging.joint, "orient_to_mesh") as orient:
            self.run_bmaya_tool("bmaya.joints.orient_to_mesh", [first, second, plane])
        orient.assert_called_once_with([first, second], plane)

    def test_orient_to_mesh_needs_a_joint_and_a_mesh(self):
        cmds = self.cmds
        cmds.select(clear=True)
        joint = cmds.joint(name="orient_lone_jnt")
        with self.assertRaisesRegex(RuntimeError, "Select the joints, then the mesh"):
            self.run_bmaya_tool("bmaya.joints.orient_to_mesh", [joint])

    def test_the_dev_tools_resolve_to_the_devreload_and_menu_functions(self):
        import bmaya.maya.devreload
        import bmaya.maya_ui.menus
        registry = _registry()
        for tool_id, function in (("bmaya.dev.reload_rigmodules", bmaya.maya.devreload.reload_rigmodules),
                                  ("bmaya.dev.unload_rigmodules", bmaya.maya.devreload.unload_rigmodules),
                                  ("bmaya.dev.reload_menu", bmaya.maya_ui.menus.reload_menus)):
            self.assertIs(tool_registry.resolve_call(registry.tools[tool_id].call), function)

    def test_cancelled_file_dialog_does_nothing(self):
        with self.answers(None):
            self.run_tool("Save Control Shapes...", self.root)
        self.assertEqual(os.listdir(self.temp), ["template.json"])


if __name__ == "__main__":
    unittest.main()
