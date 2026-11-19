"""bmaya.maya.rigpanel and the pose functions and tracker event behind it, in mayapy (RigModules D50).

Needs RIGMODULES_PLUGIN, the path of a RigModules.mll (copy it first if a Maya session has the build loaded),
and the rigmodules package on the path (RigModules.mod puts it there). Skipped without them.
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
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "RigPanelTest",
    "rigName": "game",
    "rigAuthor": "tests",
    "rigModules": [
        {"moduleType": "FkChain", "name": "spine", "shapeType": "Box",
         "moduleArgs": {"joints": [["Center", "spine1"], ["Center", "spine2"]]}},
        {"moduleType": "FkChain", "name": "arm_l", "side": "Left", "shapeType": "Circle", "mirror": True,
         "moduleArgs": {"joints": [["Left", "arm"]]}, "parentStructure": {"start": "spine.end"}},
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


class RigPanelBase(unittest.TestCase):

    def setUp(self):
        from maya import cmds
        import bmaya.maya.activerig
        import bmaya.maya.posetools
        import bmaya.maya.rigpanel
        import rigmodules.query

        self.cmds = cmds
        self.activerig = bmaya.maya.activerig
        self.posetools = bmaya.maya.posetools
        self.rigpanel = bmaya.maya.rigpanel
        self.query = rigmodules.query
        temp = tempfile.mkdtemp(prefix="bmaya_rig_panel_")
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
        """Builds the template on a new skeleton with a spine and a left and right arm. Returns the rig root."""
        cmds = self.cmds
        name = asset_id.split("\\")[-1]
        cmds.namespace(add=f"skel_{name}")
        cmds.select(clear=True)
        spine1 = cmds.joint(name=f":skel_{name}:spine1_jnt", position=(0, 10, 0))
        cmds.rigJointMarkup(spine1, usage="spine1", side="Center", export=True, skin=True)
        spine2 = cmds.joint(name=f":skel_{name}:spine2_jnt", position=(0, 12, 0))
        cmds.rigJointMarkup(spine2, usage="spine2", side="Center", export=True, skin=True)
        joints = [spine1, spine2]
        for side, x in (("Left", 2), ("Right", -2)):
            cmds.select(spine2, replace=True)
            joint = cmds.joint(name=f":skel_{name}:arm_{side[0].lower()}_jnt", position=(x, 12, 0))
            cmds.rigJointMarkup(joint, usage="arm", side=side, export=True, skin=True)
            joints.append(joint)
        cmds.createRigFromTemplate(*joints, template=self.template, asset=asset_id, namespace=name)
        cmds.select(clear=True)
        return self.query.get_rigs(name)[0].rig_root


class TrackerEvent(RigPanelBase):

    def record(self):
        calls = []
        self.activerig.ActiveRigTracker.changed.connect(calls.append)
        self.addCleanup(self.activerig.ActiveRigTracker.changed.disconnect, calls.append)
        return calls

    def test_emits_the_rig_root_when_the_active_rig_changes(self):
        hero = self.build("shooter\\hero")
        villain = self.build("shooter\\villain")
        tracker = self.activerig.ActiveRigTracker()
        tracker.set_rig_root(hero)
        calls = self.record()
        tracker.set_rig_root(villain)
        self.assertEqual(calls, [villain])

    def test_set_rig_root_to_the_same_rig_emits_nothing(self):
        hero = self.build("shooter\\hero")
        tracker = self.activerig.ActiveRigTracker()
        tracker.set_rig_root(hero)
        calls = self.record()
        tracker.set_rig_root(hero)
        self.assertEqual(calls, [])

    def test_refresh_emits_once_even_when_the_active_rig_stays(self):
        hero = self.build("shooter\\hero")
        tracker = self.activerig.ActiveRigTracker()
        self.assertEqual(tracker.rig_root, hero)
        calls = self.record()
        tracker.refresh()
        self.assertEqual(calls, [hero])

    def test_a_selection_in_another_rig_emits(self):
        hero = self.build("shooter\\hero")
        villain = self.build("shooter\\villain")
        self.activerig.ActiveRigTracker().set_rig_root(hero)
        calls = self.record()
        self.cmds.select("villain:spine1_ctrl_c", replace=True)
        self.assertEqual(calls, [villain])
        self.cmds.select(self.cmds.polyCube()[0], replace=True)   # not a rig node: no change, no emit
        self.assertEqual(calls, [villain])

    def test_listeners_survive_stop_and_a_new_tracker(self):
        hero = self.build("shooter\\hero")
        self.activerig.ActiveRigTracker().stop()
        calls = self.record()
        self.activerig.ActiveRigTracker()
        self.assertEqual(calls, [hero])


class PoseFunctions(RigPanelBase):

    def setUp(self):
        super().setUp()
        self.root = self.build("shooter\\hero")
        self.left = self.cmds.getRigControls(self.root, side="Left")[0]
        self.right = self.cmds.getRigControls(self.root, side="Right")[0]

    def test_zero_pose_acts_on_the_controls_it_is_given(self):
        self.cmds.setAttr(self.left + ".rotateY", 20)
        self.cmds.setAttr(self.right + ".rotateY", 20)
        self.assertEqual(self.posetools.zero_pose([self.left]), 1)
        self.assertEqual(self.cmds.getAttr(self.left + ".rotateY"), 0)
        self.assertEqual(self.cmds.getAttr(self.right + ".rotateY"), 20)

    def test_mirror_pose_with_a_direction(self):
        self.cmds.setAttr(self.left + ".rotateY", 20)
        self.posetools.mirror_pose([self.root], left_to_right=True)
        self.assertEqual(self.cmds.getAttr(self.right + ".rotateY"), 20)

    def test_flip_pose_swaps_the_sides(self):
        self.cmds.setAttr(self.left + ".rotateY", 20)
        self.cmds.setAttr(self.right + ".rotateY", 3)
        self.posetools.flip_pose([self.root])
        self.assertAlmostEqual(self.cmds.getAttr(self.left + ".rotateY"), 3)
        self.assertAlmostEqual(self.cmds.getAttr(self.right + ".rotateY"), 20)


class Session(RigPanelBase):

    def setUp(self):
        super().setUp()
        self.hero = self.build("shooter\\hero")
        self.session = self.rigpanel.RigPanelSession()
        self.changes = []
        self.session.changed.connect(lambda: self.changes.append(self.session.rig and self.session.rig.rig_root))

    def test_groups_are_one_per_module_and_side(self):
        """The template has a spine of two joints and a mirrored arm. The build adds the layout module's group."""
        groups = {(g.module, g.module_type, g.side): len(g.controls) for g in self.session.groups}
        self.assertEqual(len(groups), len(self.session.groups))   # no (module, side) twice
        self.assertEqual(groups["hero:spine", "FkChain", "Center"], 2)
        self.assertEqual(groups["hero:arm_l", "FkChain", "Left"], 1)
        self.assertEqual(groups["hero:arm_r", "FkChain", "Right"], 1)
        self.assertEqual({module for module, _, _ in groups},
                         {"hero:layout", "hero:spine", "hero:arm_l", "hero:arm_r"})

    def test_groups_hold_every_control_once(self):
        grouped = [control for group in self.session.groups for control in group.controls]
        self.assertEqual(grouped, [c.node for c in self.query.get_rig_controls(self.hero)])

    def test_the_session_follows_the_active_rig(self):
        villain = self.build("shooter\\villain")
        self.session.refresh()
        self.assertEqual([rig.rig_root for rig in self.session.rigs], [self.hero, villain])
        self.session.set_active(villain)
        self.assertEqual(self.session.rig.rig_root, villain)
        self.assertTrue(all(c.startswith("villain:") for g in self.session.groups for c in g.controls))
        self.assertEqual(self.changes[-1], villain)

    def test_set_active_refuses_a_rig_that_is_not_in_the_scene(self):
        with self.assertRaisesRegex(RuntimeError, "not a rig in the scene"):
            self.session.set_active("nowhere:rigRootModule1")

    def test_a_selection_in_another_rig_changes_the_session(self):
        villain = self.build("shooter\\villain")
        self.cmds.select("villain:spine1_ctrl_c", replace=True)
        self.assertEqual(self.session.rig.rig_root, villain)

    def test_a_new_scene_shows_no_rig(self):
        self.cmds.file(new=True, force=True)
        self.assertIsNone(self.session.rig)
        self.assertEqual((self.session.rigs, self.session.groups), ([], []))

    def test_a_deleted_rig_shows_no_rig_after_refresh(self):
        self.cmds.delete(self.hero)
        self.activerig.ActiveRigTracker.current().refresh()
        self.assertIsNone(self.session.rig)

    def test_a_broken_rig_is_logged_and_does_not_raise(self):
        with mock.patch.object(self.query, "get_rig_controls", side_effect=RuntimeError("broken rig")), \
                mock.patch.object(self.rigpanel.bmaya.core.log, "error") as error:
            self.session.refresh()
        error.assert_called_once()
        self.assertIn("broken rig", error.call_args.args[0])
        self.assertEqual((self.session.rigs, self.session.rig, self.session.groups), ([], None, []))
        self.assertEqual(len(self.changes), 1)   # the view is told, so it can show the empty state

    def test_select_group_replaces_or_adds(self):
        left = next(g for g in self.session.groups if g.side == "Left")
        right = next(g for g in self.session.groups if g.side == "Right")
        self.session.select_group(left)
        self.session.select_group(right, add=True)
        self.assertEqual(sorted(self.cmds.ls(selection=True)), sorted(left.controls + right.controls))
        self.session.select_group(left)
        self.assertEqual(self.cmds.ls(selection=True), list(left.controls))

    def test_select_all_and_select_mirrors(self):
        self.session.select_all()
        self.assertEqual(sorted(self.cmds.ls(selection=True)), sorted(self.cmds.getRigControls(self.hero)))
        left = next(g for g in self.session.groups if g.side == "Left")
        self.session.select_group(left)
        self.session.select_mirrors()
        right = next(g for g in self.session.groups if g.side == "Right")
        self.assertEqual(self.cmds.ls(selection=True), list(right.controls))

    def test_pose_commands_act_on_the_selection_else_the_rig(self):
        left = self.cmds.getRigControls(self.hero, side="Left")[0]
        right = self.cmds.getRigControls(self.hero, side="Right")[0]
        self.cmds.setAttr(left + ".rotateY", 20)
        self.cmds.setAttr(right + ".rotateY", 5)
        self.cmds.select(left, replace=True)
        self.session.zero()
        self.assertEqual(self.cmds.getAttr(left + ".rotateY"), 0)
        self.assertEqual(self.cmds.getAttr(right + ".rotateY"), 5)
        self.cmds.select(clear=True)
        self.session.mirror(left_to_right=False)
        self.assertEqual(self.cmds.getAttr(left + ".rotateY"), 5)
        self.session.flip()
        self.assertEqual(self.cmds.getAttr(left + ".rotateY"), 5)   # both sides hold 5: a flip changes nothing

    def test_key_commands(self):
        left = self.cmds.getRigControls(self.hero, side="Left")[0]
        self.session.key_rig()
        self.assertTrue(self.cmds.keyframe(left, query=True, keyframeCount=True))
        self.cmds.cutKey(left)
        self.cmds.select(left, replace=True)
        self.session.key_modules()
        self.assertTrue(self.cmds.keyframe(left, query=True, keyframeCount=True))

    def test_a_closed_session_stops_following_the_tracker(self):
        """A destroyed panel closes its session. A session left listening would refresh on every active rig change."""
        villain = self.build("shooter\\villain")
        self.session.close()
        self.session.close()   # closing twice is harmless
        self.activerig.ActiveRigTracker.current().set_rig_root(villain)
        self.assertEqual(self.session.rig.rig_root, self.hero)   # not refreshed
        self.assertEqual(self.changes, [])

    def test_a_dropped_session_is_not_called(self):
        calls = []
        session = self.rigpanel.RigPanelSession()
        session.refresh = lambda: calls.append(1)
        del session
        import gc
        gc.collect()
        self.activerig.ActiveRigTracker.current().refresh()
        self.assertEqual(calls, [])


LIMB_TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "RigPanelLimbTest",
    "rigName": "game",
    "rigAuthor": "tests",
    "rigModules": [
        {"moduleType": "TwoBoneIk", "name": "arm_l", "shapeType": "Box", "side": "Left", "mirror": True,
         "moduleArgs": {"joints": [["Left", "upperArm"], ["Left", "lowerArm"], ["Left", "hand"]],
                        "controlName": "arm"},
         "parentStructure": {"start": "layout.end", "ik": "layout.end", "pole": "layout.end"}},
    ],
}
# The limb of RigModules' twoboneik_basic fixture: a bent arm, and its mirror. The IK handle, pole and settings
# controls have no joints (D57): they are derived from these three.
LIMB_JOINTS = (
    ("upperArm", (0, 0, 0), True), ("lowerArm", (1.8, 2.4, 0), True), ("hand", (5, 0, 0), True),
)
LIMB_CONTROL_USAGES = ("upperArm", "lowerArm", "hand", "armIK", "armPole", "armSettings")


class LimbPanel(RigPanelBase):
    """The IK/FK limb in the panel (D52 phase 8): the limb the selection names, the switch with and without keys,
    and the pole's module-owned space and the pose commands on a limb."""

    def setUp(self):
        super().setUp()
        with open(self.template, "w", encoding="utf-8") as handle:
            json.dump(LIMB_TEMPLATE, handle)
        cmds = self.cmds
        cmds.namespace(add="skel_hero")
        self.joints = {}
        for side, sign in (("Left", 1), ("Right", -1)):
            for usage, (x, y, z), export in LIMB_JOINTS:
                cmds.select(clear=True)
                joint = cmds.joint(name=f":skel_hero:{usage}_{side[0].lower()}_jnt", position=(x * sign, y, z))
                cmds.rigJointMarkup(joint, usage=usage, side=side, export=export, skin=export)
                self.joints[side, usage] = joint
        cmds.createRigFromTemplate(*self.joints.values(), template=self.template, asset="shooter\\hero", namespace="hero")
        cmds.select(clear=True)
        self.root = self.query.get_rigs("hero")[0].rig_root
        self.left = {usage: self.query.get_rig_controls(self.root, side="Left", usage=usage)[0].node
                     for usage in LIMB_CONTROL_USAGES}
        self.right_settings = self.query.get_rig_controls(self.root, side="Right", usage="armSettings")[0].node
        self.limb_controls = tuple(self.left.values())
        self.settings = self.left["armSettings"]
        self.session = self.rigpanel.RigPanelSession()
        self.addCleanup(self.session.close)
        self.seen = []
        self.session.limb_changed.connect(lambda: self.seen.append(self.session.limb))

    def select(self, *controls):
        self.cmds.select(list(controls), replace=True)
        self.session.refresh_limb()

    def blend(self, node=None):
        return self.cmds.getAttr((node or self.settings) + ".ikFkBlend")

    def elbow(self):
        # The build moves the skeleton into the rig's namespace.
        return self.cmds.xform("hero:lowerArm_l_jnt", query=True, worldSpace=True, translation=True)

    def test_any_control_of_a_limb_gives_the_limb_in_ik_by_default(self):
        for control in self.limb_controls:
            with self.subTest(control=control):
                self.select(control)
                limb = self.session.limb
                self.assertEqual(set(limb.controls), set(self.limb_controls))
                self.assertEqual(len(limb.controls), 6)
                self.assertEqual(limb.settings, self.settings)
                self.assertEqual((limb.blend, limb.mode), (1.0, "IK"))

    def test_the_whole_limb_selected_gives_the_limb_and_anything_else_gives_none(self):
        self.select(*self.limb_controls)
        self.assertIsNotNone(self.session.limb)
        self.select(self.left["hand"], self.right_settings)
        self.assertIsNone(self.session.limb)
        self.select(self.left["hand"], self.cmds.getRigControls(self.root, moduleType="Layout")[0])
        self.assertIsNone(self.session.limb)
        self.cmds.select(clear=True)
        self.session.refresh_limb()
        self.assertIsNone(self.session.limb)

    def test_a_selection_over_six_controls_is_not_read(self):
        self.cmds.select(self.cmds.getRigControls(self.root), replace=True)
        with mock.patch("rigmodules.query.find_ik_fk_limb") as find:
            self.session.refresh_limb()
        find.assert_not_called()
        self.assertIsNone(self.session.limb)

    def test_limb_changed_emits_only_when_the_limb_changes(self):
        self.select(self.left["hand"])
        self.select(self.left["hand"])
        self.select(self.left["armPole"])
        self.assertEqual(len(self.seen), 1)
        self.cmds.setAttr(self.settings + ".ikFkBlend", 0)
        self.session.refresh_limb()
        self.assertEqual(len(self.seen), 2)
        self.assertEqual(self.seen[-1].mode, "FK")

    def test_a_blend_between_is_reported_as_a_blend(self):
        self.cmds.setAttr(self.settings + ".ikFkBlend", 0.5)
        self.select(self.left["armIK"])
        self.assertEqual((self.session.limb.blend, self.session.limb.mode), (0.5, "Blend"))

    def test_the_selection_callback_follows_the_selection_while_watching(self):
        self.session.watch_selection(True)
        self.cmds.select(self.left["armIK"], replace=True)
        self.assertEqual(self.session.limb.settings, self.settings)
        self.cmds.select(clear=True)
        self.assertIsNone(self.session.limb)

    def test_switching_to_fk_keeps_the_joints_and_keys_nothing(self):
        self.cmds.setAttr(self.left["armIK"] + ".translateY", -1)
        before = self.elbow()
        self.select(self.left["armIK"])
        self.session.set_ik_fk("FK")
        self.assertEqual(self.blend(), 0)
        self.assertEqual(self.session.limb.mode, "FK")
        for was, now in zip(before, self.elbow()):
            self.assertAlmostEqual(was, now, places=3)
        self.assertFalse(self.cmds.keyframe(self.limb_controls, query=True, keyframeCount=True))
        self.session.set_ik_fk("IK")
        self.assertEqual(self.blend(), 1)
        for was, now in zip(before, self.elbow()):
            self.assertAlmostEqual(was, now, places=3)

    def test_switching_to_the_current_mode_does_nothing(self):
        self.select(self.left["armIK"])
        self.cmds.undoInfo(state=True, infinity=True)
        self.cmds.flushUndo()
        self.session.set_ik_fk("IK")
        self.assertEqual(self.cmds.undoInfo(query=True, undoName=True) or "", "")

    def test_key_keys_all_six_controls_either_side_of_the_cut_in_one_undo(self):
        self.cmds.undoInfo(state=True, infinity=True)
        self.cmds.currentTime(10)
        self.select(*self.limb_controls)
        self.session.set_ik_fk("FK", key=True)
        self.assertEqual(self.cmds.keyframe(self.settings + ".ikFkBlend", query=True, timeChange=True), [9.0, 10.0])
        self.assertEqual(self.cmds.keyframe(self.settings + ".ikFkBlend", query=True, valueChange=True), [1.0, 0.0])
        for control in (self.left["upperArm"], self.left["armIK"], self.left["armPole"]):
            self.assertEqual(self.cmds.keyframe(control, query=True, timeChange=True)[:1], [9.0])
        self.cmds.undo()
        self.assertEqual(self.blend(), 1)
        self.assertFalse(self.cmds.keyframe(self.limb_controls, query=True, keyframeCount=True))

    def test_a_bad_mode_or_no_limb_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "Select the controls of one two-bone IK limb"):
            self.session.set_ik_fk("FK")
        self.select(self.left["hand"])
        with self.assertRaisesRegex(RuntimeError, "must be one of IK, FK"):
            self.session.set_ik_fk("Blend")

    def test_the_group_button_selects_the_hidden_controls_too(self):
        # At blend 1 the FK lower and end controls are hidden, at blend 0 the IK handle and pole are.
        self.session.refresh()
        (group,) = [group for group in self.session.groups if group.module_type == "TwoBoneIk" and group.side == "Left"]
        self.assertEqual(len(group.controls), 6)
        for blend in (1, 0):
            with self.subTest(blend=blend):
                self.cmds.setAttr(self.settings + ".ikFkBlend", blend)
                self.session.select_group(group)
                selected = self.cmds.ls(selection=True, long=True)
                self.assertEqual(set(selected), set(self.cmds.ls(self.limb_controls, long=True)))

    def test_the_pole_has_a_parent_and_an_ik_space_and_the_switch_keeps_it_in_place(self):
        pole = self.left["armPole"]
        self.cmds.setAttr(self.left["armIK"] + ".translateX", -1)
        self.cmds.select(pole, replace=True)
        self.session.refresh_space()
        space = self.session.space
        self.assertEqual((space.constraint, space.labels, space.current), ("", ("Parent", "Ik"), 0))
        before = self.cmds.xform(pole, query=True, worldSpace=True, matrix=True)
        self.session.set_space("Ik")
        self.assertEqual(self.session.space.current, 1)
        for was, now in zip(before, self.cmds.xform(pole, query=True, worldSpace=True, matrix=True)):
            self.assertAlmostEqual(was, now, places=3)
        self.assertFalse(self.cmds.keyframe(pole, query=True, keyframeCount=True))

    def test_the_pole_space_switch_keys_and_one_undo_reverts_it(self):
        pole = self.left["armPole"]
        self.cmds.undoInfo(state=True, infinity=True)
        self.cmds.currentTime(10)
        self.cmds.select(pole, replace=True)
        self.session.refresh_space()
        self.session.set_space("Ik", key=True)
        self.assertEqual(self.cmds.keyframe(pole + ".space", query=True, valueChange=True), [0.0, 1.0])
        self.cmds.undo()
        self.assertEqual(self.cmds.getAttr(pole + ".space"), 0)
        self.assertFalse(self.cmds.keyframe(pole, query=True, keyframeCount=True))

    def test_the_selection_callback_reads_the_pole_space(self):
        self.session.watch_selection(True)
        self.cmds.select(self.left["armPole"], replace=True)
        self.assertEqual(self.session.space.labels, ("Parent", "Ik"))
        self.cmds.select(self.left["hand"], replace=True)
        self.assertIsNone(self.session.space)

    def test_zero_puts_the_limb_in_ik_because_ik_is_the_rest(self):
        self.cmds.setAttr(self.settings + ".ikFkBlend", 0)
        self.cmds.setAttr(self.left["upperArm"] + ".rotateZ", 20)
        self.select(*self.limb_controls)
        self.session.zero()
        self.assertEqual(self.blend(), 1)
        self.assertEqual(self.cmds.getAttr(self.left["upperArm"] + ".rotateZ"), 0)

    def test_mirror_copies_the_blend_and_flip_swaps_it(self):
        self.cmds.setAttr(self.settings + ".ikFkBlend", 0)
        self.cmds.setAttr(self.left["upperArm"] + ".rotateZ", 20)
        self.cmds.select(clear=True)
        self.session.mirror(True)
        self.assertEqual(self.blend(self.right_settings), 0)
        right_upper = self.query.get_rig_controls(self.root, side="Right", usage="upperArm")[0].node
        self.assertAlmostEqual(abs(self.cmds.getAttr(right_upper + ".rotateZ")), 20, places=3)
        self.cmds.setAttr(self.right_settings + ".ikFkBlend", 1)
        self.session.flip()
        self.assertEqual(self.blend(), 1)
        self.assertEqual(self.blend(self.right_settings), 0)

    def test_key_rig_and_key_modules_key_the_limb_including_the_blend(self):
        self.session.key_rig()
        for control in self.limb_controls[:3] + (self.settings,):
            self.assertTrue(self.cmds.keyframe(control, query=True, keyframeCount=True), control)
        self.assertTrue(self.cmds.keyframe(self.settings + ".ikFkBlend", query=True, keyframeCount=True))
        self.cmds.cutKey(self.limb_controls)
        self.select(self.left["armIK"])
        self.session.key_modules()
        self.assertTrue(self.cmds.keyframe(self.settings + ".ikFkBlend", query=True, keyframeCount=True))
        self.assertTrue(self.cmds.keyframe(self.left["upperArm"], query=True, keyframeCount=True))


class SpaceSwitch(RigPanelBase):
    """The selected control's space switch, and switching it (D50). The left arm gets World and Chest drivers."""

    def setUp(self):
        super().setUp()
        self.root = self.build("shooter\\hero")
        self.arm = self.cmds.getRigControls(self.root, side="Left")[0]
        self.spine = self.cmds.getRigControls(self.root, side="Center", usage="spine1")[0]
        self.constraint = self.cmds.createRigConstraint(
            self.arm, driver=["layout.end", "spine.end"], label=["World", "Chest"])
        self.session = self.rigpanel.RigPanelSession()
        self.addCleanup(self.session.close)
        self.seen = []
        self.session.spaces_changed.connect(lambda: self.seen.append(self.session.space))

    def test_one_selected_control_with_a_space_switch_gives_its_state(self):
        self.cmds.select(self.arm, replace=True)
        self.session.refresh_space()
        self.assertEqual(self.session.space, self.rigpanel.SpaceState(
            self.arm, self.constraint.lstrip(":"), ("World", "Chest"), 0))

    def test_no_selection_a_control_without_a_switch_or_several_controls_give_none(self):
        for selection in ([], [self.spine], [self.arm, self.spine]):
            with self.subTest(selection=selection):
                self.cmds.select(selection, replace=True) if selection else self.cmds.select(clear=True)
                self.session.refresh_space()
                self.assertIsNone(self.session.space)

    def test_spaces_changed_emits_only_when_the_space_changes(self):
        self.cmds.select(self.arm, replace=True)
        self.session.refresh_space()
        self.session.refresh_space()
        self.assertEqual(len(self.seen), 1)
        self.cmds.select(clear=True)
        self.session.refresh_space()
        self.assertEqual(self.seen[-1], None)
        self.assertEqual(len(self.seen), 2)

    def test_switching_keeps_the_control_where_it_was_and_keys_nothing(self):
        self.cmds.select(self.arm, replace=True)
        self.session.refresh_space()
        before = self.cmds.xform(self.arm, query=True, worldSpace=True, matrix=True)
        self.session.set_space("Chest")
        self.assertEqual(self.cmds.getAttr(self.arm + ".space"), 1)
        self.assertEqual(self.session.space.current, 1)
        for matrix_before, matrix_after in zip(before, self.cmds.xform(self.arm, query=True, worldSpace=True, matrix=True)):
            self.assertAlmostEqual(matrix_before, matrix_after, places=4)
        self.assertFalse(self.cmds.keyframe(self.arm, query=True, keyframeCount=True))

    def test_switching_to_the_current_space_does_nothing(self):
        self.cmds.select(self.arm, replace=True)
        self.session.refresh_space()
        self.session.set_space("World")
        self.assertEqual(self.cmds.undoInfo(query=True, undoName=True) or "", "")

    def test_key_holds_the_old_space_on_the_previous_frame_and_keys_the_new_one_here(self):
        self.cmds.currentTime(10)
        self.cmds.select(self.arm, replace=True)
        self.session.refresh_space()
        self.session.set_space("Chest", key=True)
        self.assertEqual(self.cmds.keyframe(self.arm + ".space", query=True, timeChange=True), [9.0, 10.0])
        self.assertEqual(self.cmds.keyframe(self.arm + ".space", query=True, valueChange=True), [0.0, 1.0])
        self.assertEqual(self.cmds.keyframe(self.arm + ".translateX", query=True, timeChange=True), [9.0, 10.0])

    def test_one_undo_reverts_the_switch_and_its_keys(self):
        self.cmds.undoInfo(state=True, infinity=True)
        self.cmds.currentTime(10)
        self.cmds.select(self.arm, replace=True)
        self.session.refresh_space()
        self.session.set_space("Chest", key=True)
        self.cmds.undo()
        self.assertEqual(self.cmds.getAttr(self.arm + ".space"), 0)
        self.assertFalse(self.cmds.keyframe(self.arm, query=True, keyframeCount=True))

    def test_an_unknown_label_or_no_space_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "Select one control"):
            self.session.set_space("World")
        self.cmds.select(self.arm, replace=True)
        self.session.refresh_space()
        with self.assertRaisesRegex(RuntimeError, "no space labelled 'Head'.*World, Chest"):
            self.session.set_space("Head")

    def test_the_selection_callback_follows_the_selection_while_watching(self):
        self.session.watch_selection(True)
        self.session.watch_selection(True)   # twice is harmless
        self.cmds.select(self.arm, replace=True)
        self.assertEqual(self.session.space.labels, ("World", "Chest"))
        self.cmds.select(self.spine, replace=True)
        self.assertIsNone(self.session.space)

    def test_it_stops_following_when_not_watching_and_on_close(self):
        self.session.watch_selection(True)
        self.session.watch_selection(False)
        self.cmds.select(self.arm, replace=True)
        self.assertIsNone(self.session.space)
        self.session.watch_selection(True)
        self.assertIsNotNone(self.session.space)   # watching again reads the selection at once
        self.session.close()
        self.cmds.select(self.spine, replace=True)
        self.assertIsNotNone(self.session.space)   # closed: not updated

    def test_a_rig_change_reads_the_selected_control_again(self):
        self.build("shooter\\villain")
        self.cmds.select(self.arm, replace=True)
        self.session.refresh()
        self.assertEqual(self.session.space.control, self.arm)


class GroupControls(unittest.TestCase):
    """The grouping alone, on plain data."""

    def test_groups_by_module_and_side_in_first_seen_order(self):
        import bmaya.maya.rigpanel
        try:
            import rigmodules.query
        except ImportError:
            self.skipTest("rigmodules is not on the path")

        def control(node, module, side):
            return rigmodules.query.RigControl(node, module, "FkChain", side, node, None)

        groups = bmaya.maya.rigpanel.group_controls([
            control("a", "m1", "Left"), control("b", "m2", "Center"), control("c", "m1", "Left"),
            control("d", "m1", "Right")])
        self.assertEqual([(g.module, g.side, g.controls) for g in groups],
                         [("m1", "Left", ("a", "c")), ("m2", "Center", ("b",)), ("m1", "Right", ("d",))])


if __name__ == "__main__":
    unittest.main()
