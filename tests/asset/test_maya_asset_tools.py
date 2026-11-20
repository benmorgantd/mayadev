"""bmaya.maya.assettools in mayapy, against the RigModules plugin and its rigmodules package (RigModules D30): the
tools that add and build an asset's skeletons, rigs and looks (RigModules D54), and the rest of the asset tools.

Needs RIGMODULES_PLUGIN, the path of a RigModules.mll (copy it first if a Maya session has the build
loaded), and the rigmodules package on the path (RigModules.mod puts it there). Skipped without them.
Run with tests/asset/run.bat.
"""

import dataclasses
import json
import os
import re
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
HERO = "shooter\\main\\characters\\hero"
VILLAIN = "shooter\\main\\characters\\villain"
# The hero's rig is "game" and its skeleton and look are "default" (RigModules D54).
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "AssetToolsTest",
    "rigName": "game",
    "rigAuthor": "tests",
    "rigModules": [
        {"moduleType": "FkChain", "name": "spine_00_M_MOD", "shapeType": "Box",
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
        import bmaya.core.asset
        import bmaya.core.asset.handlers
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

        bmaya.core.asset.Project.create(os.path.join(self.root, "shooter", "main"))
        self.hero = bmaya.core.asset.Asset.create(HERO, "Character")
        self.template = self.write_template(TEMPLATE)
        for file_type in ("skeleton", "model", "rig", "shapes", "template", "weights"):
            self.addCleanup(bmaya.core.asset.handlers.unregister, file_type)
        cmds.file(new=True, force=True)

    def answers(self, *answers):
        """A prompter that answers the tool's questions in order. With no prompter, a question raises (the session
        default), which is how a test asserts that a tool asks nothing."""
        import bmaya.core.prompts
        return bmaya.core.prompts.ScriptedPrompter(answers)

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
            joint = cmds.joint(name=f"{usage}_00_M_JNT", position=(0, i * 2, 0))
            cmds.rigJointMarkup(joint, usage=usage, side="Center", export=True, skin=True)
            joints.append(joint)
        return joints

    def make_buildable_asset(self):
        """A hero with the rig game and its skeleton saved as "default", in a new empty scene."""
        self.tools.new_rig(HERO, self.template)
        self.tools.save_skeleton(HERO, joints=self.make_skeleton())
        self.cmds.file(new=True, force=True)

    def read_json(self, path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def build_outside_the_asset(self, asset_id):
        """A rig built from a template anywhere, the way a rigger iterates before the asset exists."""
        self.cmds.createRigFromTemplate(*self.make_skeleton(), template=self.template.replace("\\", "/"), asset=asset_id,
                                       namespace=asset_id.split("\\")[-1])
        import rigmodules.query
        return rigmodules.query.get_rigs()[0].rig_root

    # ---- rigs, looks and skeletons ----

    def test_new_rig_copies_the_template_and_writes_rig_json(self):
        self.assertEqual(self.tools.new_rig(HERO, self.template), "game")
        self.assertEqual(self.hero.rigs, ["game"])
        self.assertEqual(self.read_json(self.hero.path("template", "game")), TEMPLATE)
        self.assertEqual(self.read_json(os.path.join(self.hero.folder, "rigs", "game", "rig.json")),
                         {"formatVersion": 1, "skeleton": "default"})

    def test_new_rig_under_another_name_writes_it_as_the_templates_rig_name(self):
        # Templates are shared between assets, so the copy takes the rig's name. The rest of the file is the same.
        self.assertEqual(self.tools.new_rig(HERO, self.template, "body", skeleton="biped"), "body")
        self.assertEqual(self.read_json(self.hero.path("template", "body")), dict(TEMPLATE, rigName="body"))
        self.assertEqual(list(self.read_json(self.hero.path("template", "body"))), list(TEMPLATE), "the keys keep their order")
        self.assertEqual(self.read_json(self.hero.path("riginfo", "body")), {"formatVersion": 1, "skeleton": "biped"})
        self.assertEqual(self.read_json(self.template), TEMPLATE, "the source template is not edited")

    def test_new_rig_can_name_another_assets_skeleton_and_the_rig_it_copies(self):
        import bmaya.core.asset
        self.tools.new_rig(HERO, self.template)
        self.tools.new_rig(HERO, self.template, "game_cine", skeleton="default", skeleton_asset=VILLAIN,
                           source=bmaya.core.asset.RigRef("game"))
        self.assertEqual(self.read_json(self.hero.path("riginfo", "game_cine")),
                         {"formatVersion": 1, "skeleton": {"asset": VILLAIN, "name": "default"}, "source": "game"})

    def test_new_rig_twice_fails(self):
        self.tools.new_rig(HERO, self.template)
        with self.assertRaisesRegex(RuntimeError, "already has a rig 'game'"):
            self.tools.new_rig(HERO, self.template)

    def test_new_rig_refuses_an_uppercase_name_and_writes_nothing(self):
        import bmaya.core.asset
        with self.assertRaises((bmaya.core.asset.RecordError, bmaya.core.asset.ProjectError)):
            self.tools.new_rig(HERO, self.template, "Body")
        self.assertFalse(os.path.exists(os.path.join(self.hero.folder, "rigs")))

    def test_new_rig_needs_the_asset(self):
        with self.assertRaisesRegex(RuntimeError, "Create it with New Asset first"):
            self.tools.new_rig("shooter\\main\\characters\\nobody", self.template)

    def test_new_rig_needs_a_rig_name(self):
        path = self.write_template({"rigVersion": 1}, "no_rig_name.json")
        with self.assertRaisesRegex(ValueError, "has no rigName"):
            self.tools.new_rig(HERO, path)
        self.assertEqual(self.hero.rigs, [])

    def test_new_look_writes_look_json(self):
        self.assertEqual(self.tools.new_look(HERO), "default")
        self.assertEqual(self.tools.new_look(HERO, "winter", skeleton="default", skeleton_asset=VILLAIN), "winter")
        self.assertEqual(self.hero.looks, ["default", "winter"])
        self.assertEqual(self.read_json(os.path.join(self.hero.folder, "looks", "default", "look.json")),
                         {"formatVersion": 1, "skeletons": ["default"]})
        self.assertEqual(self.read_json(self.hero.path("lookinfo", "winter")),
                         {"formatVersion": 1, "skeletons": [{"asset": VILLAIN, "name": "default"}]})
        with self.assertRaisesRegex(RuntimeError, "already has a look 'default'"):
            self.tools.new_look(HERO)

    def test_save_skeleton_writes_the_skeleton_file_and_leaves_the_scene_alone(self):
        cmds = self.cmds
        self.make_skeleton()
        scene = cmds.file(query=True, sceneName=True)
        path = self.tools.save_skeleton(HERO)
        self.assertEqual(path, os.path.join(self.hero.folder, "skeletons", "default", "skeleton.json"))
        self.assertEqual(os.listdir(os.path.dirname(path)), ["skeleton.json"], "a skeleton is its skeleton.json: no scene file")
        self.assertEqual(self.hero.skeletons, ["default"])
        self.assertEqual(cmds.file(query=True, sceneName=True), scene, "the scene is a workspace, not the skeleton")
        data = self.read_json(path)
        self.assertEqual([joint["name"] for joint in data["joints"]], ["spine1_00_M_JNT", "spine2_00_M_JNT"])
        self.assertEqual(data["joints"][1]["parent"], ["Center", "spine1"])

    def test_save_skeleton_under_a_name_and_of_named_joints(self):
        joints = self.make_skeleton()
        path = self.tools.save_skeleton(HERO, "face", joints=joints[:1])
        self.assertEqual(path, self.hero.path("skeleton", "face"))
        self.assertEqual([joint["name"] for joint in self.read_json(path)["joints"]], ["spine1_00_M_JNT"])

    def test_save_skeleton_with_an_unmarked_joint_fails_and_writes_nothing(self):
        cmds = self.cmds
        self.make_skeleton()
        cmds.select(clear=True)
        cmds.joint(name="helper_00_M_JNT")
        with self.assertRaisesRegex(RuntimeError, "helper_00_M_JNT"):
            self.tools.save_skeleton(HERO)
        self.assertFalse(os.path.exists(os.path.join(self.hero.folder, "skeletons")), "not even the folder")

    def test_a_failed_save_keeps_the_skeleton_that_was_saved(self):
        cmds = self.cmds
        self.make_skeleton()
        path = self.tools.save_skeleton(HERO)
        with open(path, encoding="utf-8") as handle:
            before = handle.read()
        cmds.select(clear=True)
        cmds.joint(name="helper_00_M_JNT")
        with self.assertRaises(RuntimeError):
            self.tools.save_skeleton(HERO)
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), before)
        from bmaya.core.asset import versions
        self.assertEqual(versions.list_versions(path, self.root), [], "nothing was versioned for a save that failed")

    def test_save_skeleton_refuses_joints_a_rig_drives(self):
        self.build_outside_the_asset(HERO)
        with self.assertRaisesRegex(RuntimeError, "driven by a rig"):
            self.tools.save_skeleton(HERO)
        self.assertEqual(self.hero.skeletons, [])

    def test_save_skeleton_without_joints_fails(self):
        with self.assertRaisesRegex(RuntimeError, "no joints"):
            self.tools.save_skeleton(HERO)

    def test_load_skeleton_creates_the_saved_joints(self):
        cmds = self.cmds
        self.make_skeleton()
        path = self.tools.save_skeleton(HERO)
        with open(path, encoding="utf-8") as handle:
            saved = handle.read()
        cmds.file(new=True, force=True)
        joints = self.tools.load_skeleton(HERO, namespace="edit")
        self.assertEqual(joints, ["edit:spine1_00_M_JNT", "edit:spine2_00_M_JNT"])
        self.assertEqual(cmds.xform("edit:spine2_00_M_JNT", query=True, worldSpace=True, translation=True), [0.0, 2.0, 0.0])
        self.assertEqual(cmds.rigJointMarkup("edit:spine2_00_M_JNT", query=True, usage=True), ["spine2"])
        # Saved again from the loaded joints, the file is the same: the skeleton file is the skeleton.
        self.tools.save_skeleton(HERO, joints=joints)
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), saved)

    def test_load_skeleton_into_the_current_namespace_and_of_a_missing_skeleton(self):
        self.make_skeleton()
        self.tools.save_skeleton(HERO)
        self.cmds.file(new=True, force=True)
        self.assertEqual(self.tools.load_skeleton(HERO), ["spine1_00_M_JNT", "spine2_00_M_JNT"])
        with self.assertRaises(FileNotFoundError):
            self.tools.load_skeleton(HERO, "face")

    # ---- building from the asset ----

    def test_build_rig_creates_the_skeleton_and_builds_the_rig(self):
        import rigmodules.query
        self.make_buildable_asset()
        rig_root = self.tools.build_rig(HERO, "game")
        info = rigmodules.query.get_rig_info(rig_root)
        # RigModules' default namespace, "{asset name}_{rigName}" (D54).
        self.assertEqual((info.asset_id, info.rig_name, info.namespace), (HERO, "game", "hero_game"))
        self.assertTrue(self.cmds.objExists("hero_game:spine1_00_M_CTRL"))
        self.assertEqual(self.cmds.ls("hero_game:*", type="joint"), ["hero_game:spine1_00_M_JNT", "hero_game:spine2_00_M_JNT"])
        # The rig is stamped with the hash of the skeleton file it was built on.
        self.assertEqual(info.skeleton_hash, self.read_json(self.hero.path("skeleton", "default"))["skeletonHash"])

    def test_build_rig_on_another_assets_skeleton(self):
        # NPCs share one skeleton with no copied file: the villain's rig names the hero's skeleton.
        import bmaya.core.asset
        import rigmodules.query
        self.tools.save_skeleton(HERO, joints=self.make_skeleton())
        self.cmds.file(new=True, force=True)
        villain = bmaya.core.asset.Asset.create(VILLAIN, "Character")
        self.tools.new_rig(VILLAIN, self.template, skeleton="default", skeleton_asset=HERO)
        info = rigmodules.query.get_rig_info(self.tools.build_rig(VILLAIN, "game"))
        self.assertEqual((info.asset_id, info.namespace), (VILLAIN, "villain_game"))
        self.assertEqual(villain.skeletons, [], "the villain holds no skeleton of its own")
        self.assertEqual(info.skeleton_hash, self.read_json(self.hero.path("skeleton", "default"))["skeletonHash"])

    def test_build_rig_leaves_nothing_selected(self):
        self.make_buildable_asset()
        self.tools.build_rig(HERO, "game")
        self.assertEqual([], self.cmds.ls(selection=True))

    def test_build_rig_loads_the_rigs_shape_file(self):
        cmds = self.cmds
        self.make_buildable_asset()
        rig_root = self.tools.build_rig(HERO, "game")
        cmds.setAttr("hero_game:spine1_00_M_CTRL.shapeType", 1)  # Sphere
        self.tools.save_control_shapes(rig_root)

        cmds.file(new=True, force=True)
        self.tools.build_rig(HERO, "game")
        self.assertEqual(cmds.getAttr("hero_game:spine1_00_M_CTRL.shapeType", asString=True), "Sphere")

    def test_build_rig_into_a_namespace_that_holds_a_rig_fails(self):
        self.make_buildable_asset()
        self.tools.build_rig(HERO, "game")
        with self.assertRaisesRegex(RuntimeError, "already holds a rig"):
            self.tools.build_rig(HERO, "game")
        self.tools.build_rig(HERO, "game", namespace="hero2")
        self.assertTrue(self.cmds.objExists("hero2:spine1_00_M_CTRL"))

    def test_build_rig_needs_the_rig_and_the_skeleton(self):
        with self.assertRaises(FileNotFoundError):
            self.tools.build_rig(HERO, "game")
        self.tools.new_rig(HERO, self.template)
        with self.assertRaisesRegex(RuntimeError, "has no skeleton file. Save it with Save Skeleton first"):
            self.tools.build_rig(HERO, "game")
        self.assertEqual(self.cmds.ls(type="joint"), [])

    # ---- saving a rig and its shapes ----

    def test_shapes_go_to_the_asset_once_its_folder_exists(self):
        cmds = self.cmds
        rig_root = self.build_outside_the_asset(HERO)
        path = self.tools.save_control_shapes("hero:spine1_00_M_CTRL")   # no prompter: a question would raise
        self.assertEqual(path, self.hero.path("shapes", "game"))
        cmds.setAttr("hero:spine1_00_M_CTRL.shapeType", 1)
        self.tools.load_control_shapes(rig_root)
        self.assertEqual(cmds.getAttr("hero:spine1_00_M_CTRL.shapeType", asString=True), "Box")

    def test_load_shapes_without_a_saved_file_fails(self):
        self.build_outside_the_asset(HERO)
        with self.assertRaises(FileNotFoundError):
            self.tools.load_control_shapes("hero:spine1_00_M_CTRL")

    def test_shapes_ask_for_a_file_before_the_asset_exists(self):
        cmds = self.cmds
        self.build_outside_the_asset("shooter\\main\\characters\\nobody")
        path = os.path.join(self.temp, "chosen_shapes.json").replace("\\", "/")
        self.assertEqual(self.tools.save_control_shapes("nobody:spine1_00_M_CTRL", prompter=self.answers(path)), path)
        self.assertTrue(os.path.isfile(path))
        self.assertFalse(os.path.exists(os.path.join(self.root, "shooter", "main", "characters", "nobody")))

    def user_folder(self, kind):
        import bmaya.core.asset.library
        return bmaya.core.asset.library.user_source(self.hero, "game").folders[kind]

    def test_save_pose_names_a_file_in_the_users_own_library_of_the_rig(self):
        cmds = self.cmds
        self.tools.new_rig(HERO, self.template)
        self.build_outside_the_asset(HERO)
        cmds.select(clear=True)
        cmds.setAttr("hero:spine1_00_M_CTRL.translateY", 2)
        answers = self.answers("idle")
        path = self.tools.save_pose_interactive(prompter=answers)
        self.assertEqual([q.kind for q in answers.asked], ["ask_text"], "a name, not a file")
        self.assertEqual(answers.asked[0].default, "pose_001", "a free name is offered")
        import getpass
        library = os.path.join(self.root, "user", getpass.getuser(), "animlibrary", "shooter", "main", "characters", "hero", "game")
        self.assertEqual(path, os.path.join(library, "controlposes", "idle.controlpose.json"))
        self.assertTrue(os.path.isfile(path))
        self.assertFalse(os.path.exists(self.hero.path("controlposes", "game")), "nothing goes to the Approved folder")
        meta = self.read_json(path)["meta"]
        self.assertEqual((meta["assetId"], meta["rigName"], meta["author"], meta["template"], meta["skeleton"]),
                         (HERO, "game", getpass.getuser(), "game", "default"))

    def test_a_pose_of_a_rig_the_asset_does_not_hold_names_no_skeleton(self):
        # A rig built from a template before New Rig: the asset can't say what skeleton it is on.
        self.build_outside_the_asset(HERO)
        self.cmds.select(clear=True)
        meta = self.read_json(self.tools.save_pose_interactive(prompter=self.answers("idle")))["meta"]
        self.assertNotIn("skeleton", meta)
        self.assertEqual(len(meta["skeletonHash"]), 16, "the rig stamps the hash either way")

    def test_save_pose_replace_keeps_a_version_and_cancel_keeps_the_file(self):
        cmds = self.cmds
        self.build_outside_the_asset(HERO)
        cmds.select(clear=True)
        path = self.tools.save_pose_interactive(prompter=self.answers("idle"))
        cmds.setAttr("hero:spine1_00_M_CTRL.translateY", 5)
        cancel = self.answers("idle", False)
        self.assertIsNone(self.tools.save_pose_interactive(prompter=cancel))
        self.assertEqual(cancel.asked[1].options, ("Replace",))
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["controls"]["Center"]["spine1"]["translateY"], 0)
        self.tools.save_pose_interactive(prompter=self.answers("idle", True))
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["controls"]["Center"]["spine1"]["translateY"], 5)

    def test_save_pose_rejects_a_name_that_is_not_a_file_name(self):
        self.build_outside_the_asset(HERO)
        with self.assertRaisesRegex(ValueError, "not a pose name"):
            self.tools.save_pose(HERO, "a/b", ["hero:spine1_00_M_CTRL"])

    def test_capture_joint_clip_names_an_fbx_in_the_exports_folder_of_the_rigs_skeleton(self):
        cmds = self.cmds
        self.tools.new_rig(HERO, self.template)
        rig_root = self.build_outside_the_asset(HERO)
        cmds.playbackOptions(minTime=1, maxTime=3)
        with self.active_rig(rig_root):
            path = self.tools.capture_joint_clip_interactive(prompter=self.answers("walk"))
        self.assertEqual(path, os.path.join(self.hero.folder, "skeletons", "default", "exports", "walk", "walk.fbx"))
        self.assertTrue(os.path.isfile(path))

    def test_a_clip_of_a_rig_on_another_assets_skeleton_goes_to_that_skeleton(self):
        # An animation FBX is skeleton data, so every rig of one skeleton shares one exports folder.
        import bmaya.core.asset
        bmaya.core.asset.Asset.create(VILLAIN, "Character")
        self.tools.new_rig(VILLAIN, self.template, skeleton="default", skeleton_asset=HERO)
        self.cmds.createRigFromTemplate(*self.make_skeleton(), template=self.template.replace("\\", "/"), asset=VILLAIN,
                                       namespace="villain")
        import rigmodules.query
        rig_root = rigmodules.query.get_rigs()[0].rig_root
        path = self.tools.save_joint_clip(VILLAIN, "walk", rig_root, 1, 2)
        self.assertEqual(path, os.path.join(self.hero.folder, "skeletons", "default", "exports", "walk", "walk.fbx"))

    def test_a_clip_of_a_rig_the_asset_does_not_hold_fails(self):
        rig_root = self.build_outside_the_asset(HERO)
        with self.assertRaisesRegex(RuntimeError, "has no rig 'game'"):
            self.tools.save_joint_clip(HERO, "walk", rig_root, 1, 2)

    def test_load_pose_dialog_opens_in_the_users_own_library(self):
        cmds = self.cmds
        self.build_outside_the_asset(HERO)
        cmds.select(clear=True)
        path = self.tools.save_pose_interactive(prompter=self.answers("idle"))
        cmds.setAttr("hero:spine1_00_M_CTRL.translateY", 5)
        answers = self.answers(path)
        self.assertEqual(self.tools.load_pose_interactive(prompter=answers), path)
        self.assertEqual(answers.asked[0].default, self.user_folder("pose"))
        self.assertEqual(cmds.getAttr("hero:spine1_00_M_CTRL.translateY"), 0)

    def test_load_pose_dialog_starts_in_the_approved_folder_before_the_user_has_a_library(self):
        self.tools.new_rig(HERO, self.template)
        self.build_outside_the_asset(HERO)
        self.cmds.select(clear=True)
        approved = os.path.join(self.hero.folder, "rigs", "game", "controlposes")
        os.makedirs(approved)
        answers = self.answers(None)
        self.assertIsNone(self.tools.load_pose_interactive(prompter=answers))
        self.assertEqual(answers.asked[0].default, approved)

    def test_a_legacy_pose_file_still_loads(self):
        cmds = self.cmds
        self.build_outside_the_asset(HERO)
        cmds.select(clear=True)
        cmds.setAttr("hero:spine1_00_M_CTRL.translateY", 3)
        legacy = os.path.join(self.hero.path("controlposes", "game"), "old.json")
        os.makedirs(os.path.dirname(legacy))
        cmds.saveRigPose(self.cmds.ls("hero:*", type="rigRootModule")[0], file=legacy.replace("\\", "/"))
        cmds.setAttr("hero:spine1_00_M_CTRL.translateY", 0)
        import bmaya.maya.assethandlers
        names = bmaya.maya.assethandlers.ControlPoseHandler.names(self.hero.path("controlposes", "game"))
        self.assertEqual(names, ["old"])
        bmaya.maya.assethandlers.ControlPoseHandler().load(
            self.hero, self.hero.path("controlposes", "game"), name="old", scope=cmds.ls("hero:*", type="rigRootModule"))
        self.assertEqual(cmds.getAttr("hero:spine1_00_M_CTRL.translateY"), 3)

    def test_pose_tools_use_a_file_dialog_before_the_asset_exists(self):
        cmds = self.cmds
        self.build_outside_the_asset("shooter\\main\\characters\\nobody")
        cmds.select(clear=True)
        path = os.path.join(self.temp, "chosen_pose.json").replace("\\", "/")
        self.assertEqual(self.tools.save_pose_interactive(prompter=self.answers(path)), path)
        self.assertEqual(self.tools.load_pose_interactive(prompter=self.answers(path)), path)
        self.assertTrue(os.path.isfile(path))

    def active_rig(self, rig_root):
        return mock.patch.object(self.tools.bmaya.maya.activerig, "get_active_rig",
                                 return_value=mock.Mock(rig_root=rig_root, asset_id=HERO, rig_name="game"))

    def test_save_animation_names_a_file_in_the_users_own_library_and_replace_keeps_a_version(self):
        cmds = self.cmds
        self.build_outside_the_asset(HERO)
        cmds.select(clear=True)
        cmds.playbackOptions(minTime=1, maxTime=3)
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateY", time=1, value=0)
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateY", time=3, value=4)
        path = self.tools.save_animation_interactive(prompter=self.answers("rise"))
        self.assertEqual(path, os.path.join(self.user_folder("animation"), "rise.controlanim.json"))
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["endFrame"], 3)
        self.assertIsNone(self.tools.save_animation_interactive(prompter=self.answers("rise", False)))
        self.tools.save_animation_interactive(prompter=self.answers("rise", True))
        from bmaya.core.asset import versions
        self.assertEqual(len(versions.list_versions(path, self.root)), 1)

    def test_load_animation_dialog_opens_in_the_users_library_and_mirror_flips_a_center_control(self):
        cmds = self.cmds
        self.build_outside_the_asset(HERO)
        cmds.select(clear=True)
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateX", time=1, value=2)
        path = self.tools.save_animation_interactive(prompter=self.answers("lean"))
        cmds.cutKey("hero:spine1_00_M_CTRL", attribute="translateX", clear=True)
        cmds.setAttr("hero:spine1_00_M_CTRL.translateX", 0)
        answers = self.answers(path)
        self.assertEqual(self.tools.load_animation_interactive(prompter=answers), path)
        self.assertEqual(answers.asked[0].default, self.user_folder("animation"))
        self.assertEqual(cmds.getAttr("hero:spine1_00_M_CTRL.translateX", time=1), 2)
        self.assertEqual(self.tools.load_animation_interactive(mirror=True, prompter=self.answers(path)), path)
        self.assertEqual(cmds.getAttr("hero:spine1_00_M_CTRL.translateX", time=1), -2)

    def test_load_animation_cancelled_changes_nothing(self):
        self.build_outside_the_asset(HERO)
        self.cmds.select(clear=True)
        self.assertIsNone(self.tools.load_animation_interactive(prompter=self.answers(None)))
        self.assertEqual(self.cmds.ls(type="animCurve") or [], [])

    def test_animation_tools_use_a_file_dialog_before_the_asset_exists(self):
        cmds = self.cmds
        self.build_outside_the_asset("shooter\\main\\characters\\nobody")
        cmds.select(clear=True)
        cmds.setKeyframe("nobody:spine1_00_M_CTRL.translateY", time=1, value=1)
        path = os.path.join(self.temp, "chosen_anim.json").replace("\\", "/")
        self.assertEqual(self.tools.save_animation_interactive(prompter=self.answers(path)), path)
        self.assertEqual(self.tools.load_animation_interactive(prompter=self.answers(path)), path)
        self.assertTrue(os.path.isfile(path))

    def test_the_skeleton_export_checks_clips_against_its_joints(self):
        cmds = self.cmds
        self.tools.new_rig(HERO, self.template)
        rig_root = self.build_outside_the_asset(HERO)
        cmds.playbackOptions(minTime=1, maxTime=2)
        exports = os.path.join(self.hero.folder, "skeletons", "default", "exports")
        with self.active_rig(rig_root):
            fbx = self.tools.save_skeleton_export_interactive()
        self.assertEqual(fbx, os.path.join(exports, "hero_default_skeleton.fbx"))
        bone_map = self.read_json(fbx[:-4] + ".bonemap.json")
        self.assertEqual((bone_map["assetId"], bone_map["skeletonId"]), (HERO, "default"))

        clip = self.tools.save_joint_clip(HERO, "walk", rig_root, 1, 2)
        answers = self.answers(clip)
        with self.active_rig(rig_root):
            self.assertEqual(self.tools.check_clip_skeleton_interactive(prompter=answers), clip)
        self.assertEqual(answers.asked[0].default, exports)

        identity = {"translate": [0, 0, 0], "rotate": [0, 0, 0, 1], "scale": [1, 1, 1]}
        other = {"formatVersion": 1, "frameRate": 30.0, "startFrame": 1, "poses": [[identity]],
                 "joints": [{"path": "elbow_00_M_JNT", "markup": "", "rest": identity}]}
        other_json = os.path.join(self.temp, "other.json")
        with open(other_json, "w", encoding="utf-8") as handle:
            json.dump(other, handle)
        cmds.currentUnit(time="ntsc")
        other_fbx = os.path.join(self.temp, "other.fbx")
        import rigmodules.jointclip
        rigmodules.jointclip.write_fbx(other_json, other_fbx)
        with self.assertRaisesRegex(ValueError, "the animation lacks spine1_00_M_JNT, spine2_00_M_JNT"):
            self.tools.check_clip_skeleton(HERO, "game", other_fbx)

    def test_checking_a_clip_needs_the_skeleton_export(self):
        self.tools.new_rig(HERO, self.template)
        with self.assertRaisesRegex(FileNotFoundError, "Save Skeleton Export"):
            self.tools.check_clip_skeleton(HERO, "game", os.path.join(self.temp, "walk.fbx"))

    def test_clip_properties_are_set_from_a_dialog_and_keep_events_and_curves(self):
        import bmaya.core.asset.animproperties as animproperties
        fbx = os.path.join(self.temp, "walk.fbx")
        animproperties.write(animproperties.get_path(fbx), animproperties.AnimProperties(
            events=(animproperties.AnimEvent("footstep", 4.0),),
            curves=(animproperties.AnimCurve("lock", ((1.0, 0.0), (2.0, 1.0))),)))
        properties_path = animproperties.get_path(fbx)
        animproperties.write(properties_path, dataclasses.replace(animproperties.read(properties_path), additive="local"))
        answers = self.answers(fbx, self.tools.ClipSettings(loop=True, root_motion=True, additive="mesh"))
        with self.active_rig("hero:rigRootModule1"):
            self.assertEqual(self.tools.edit_clip_properties_interactive(prompter=answers), fbx)
        self.assertEqual(answers.asked[1].default, self.tools.ClipSettings(additive="local"),
                         "the form starts at the file's values")
        properties = animproperties.read(animproperties.get_path(fbx))
        self.assertEqual((properties.loop, properties.root_motion, properties.additive), (True, True, "mesh"))
        self.assertEqual(len(properties.events), 1)
        self.assertEqual(len(properties.curves), 1)

    def test_editing_clip_properties_cancelled_writes_nothing(self):
        import bmaya.core.asset.animproperties as animproperties
        fbx = os.path.join(self.temp, "walk.fbx")
        for answers in ((None,), (fbx, None)):
            with self.active_rig("hero:rigRootModule1"):
                self.assertIsNone(self.tools.edit_clip_properties_interactive(prompter=self.answers(*answers)))
        self.assertFalse(os.path.exists(animproperties.get_path(fbx)))

    def test_set_clip_properties_refuses_a_bad_value(self):
        import bmaya.core.asset.animproperties as animproperties
        with self.assertRaises(animproperties.AnimPropertiesError):
            self.tools.set_clip_properties(os.path.join(self.temp, "walk.fbx"), additive="relative")

    def test_save_rig_writes_the_rigs_scene_file(self):
        self.tools.new_rig(HERO, self.template)
        self.build_outside_the_asset(HERO)
        path = self.tools.save_rig("hero:spine1_00_M_CTRL")
        self.assertEqual(path, os.path.join(self.hero.folder, "rigs", "game", "hero_game_rig.ma"))
        self.assertTrue(os.path.isfile(path))

    def test_save_rig_needs_the_rig(self):
        self.build_outside_the_asset(HERO)
        with self.assertRaisesRegex(RuntimeError, "Add it with New Rig first"):
            self.tools.save_rig("hero:spine1_00_M_CTRL")

    def test_save_rig_uses_a_file_dialog_before_the_asset_exists(self):
        self.build_outside_the_asset("shooter\\main\\characters\\nobody")
        path = os.path.join(self.temp, "chosen_rig.ma").replace("\\", "/")
        self.assertEqual(self.tools.save_rig("nobody:spine1_00_M_CTRL", prompter=self.answers(path)), path)
        self.assertTrue(os.path.isfile(path))

    # ---- meshes and skin weights ----

    def make_box(self, namespace=""):
        """A 2-unit-tall cube standing on the origin, so spine1 (y=0) and spine2 (y=2) can skin it."""
        cmds = self.cmds
        box = cmds.polyCube(name=f":{namespace}:box_geo" if namespace else "box_geo", height=2, constructionHistory=False)[0]
        cmds.move(0, 1, 0, box)
        cmds.makeIdentity(box, apply=True, translate=True)
        return box

    def skin_box(self, box, namespace="hero"):
        cmds = self.cmds
        joints = [f"{namespace}:spine1_00_M_JNT", f"{namespace}:spine2_00_M_JNT"]
        cluster = cmds.skinCluster(*joints, box, toSelectedBones=True)[0]
        cmds.skinPercent(cluster, box + ".vtx[0]", transformValue=[(joints[0], 0.25), (joints[1], 0.75)])
        return cluster

    def spine2_weights(self, box, namespace="hero"):
        cmds = self.cmds
        cluster = cmds.ls(cmds.listHistory(box), type="skinCluster")[0]
        return [round(cmds.skinPercent(cluster, f"{box}.vtx[{v}]", transform=f"{namespace}:spine2_00_M_JNT", query=True), 6)
                for v in range(8)]

    def test_mark_meshes_for_skinning_marks_the_selected_meshes(self):
        box = self.make_box()
        joint = self.make_skeleton()[0]
        self.cmds.select(box, joint)
        ids = self.tools.mark_meshes_for_skinning()
        self.assertEqual(ids, [self.cmds.getAttr(box + ".meshId")])
        self.assertNotEqual(self.tools.mark_meshes_for_skinning(new_ids=True), ids)

    def test_mark_meshes_for_skinning_logs_new_and_kept_ids(self):
        import bmaya.core.log
        box = self.make_box()
        self.cmds.select(box)
        with mock.patch.object(bmaya.core.log, "info") as info:
            self.tools.mark_meshes_for_skinning()
            self.assertIn("1 new id(s), 0 already", info.call_args[0][0])
            self.tools.mark_meshes_for_skinning()
            self.assertIn("0 new id(s), 1 already", info.call_args[0][0])
            self.tools.mark_meshes_for_skinning(new_ids=True)
            self.assertIn("given new ids", info.call_args[0][0])

    def red_material(self, mesh, namespace=""):
        """Assigns a lambert named red_mat (in a namespace, as a look's materials are in a rig scene) to a mesh."""
        cmds = self.cmds
        prefix = f":{namespace}:" if namespace else ""
        shader = cmds.shadingNode("lambert", asShader=True, name=prefix + "red_mat")
        engine = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=prefix + "red_matSG")
        cmds.connectAttr(shader + ".outColor", engine + ".surfaceShader")
        cmds.sets(mesh, edit=True, forceElement=engine)
        return shader

    def test_save_model_writes_the_looks_model_and_leaves_the_scene_alone(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        box = self.make_box()
        cmds.setRigMeshId(box)
        scene = cmds.file(query=True, sceneName=True)
        nodes = sorted(cmds.ls(long=True))
        path = self.tools.save_model(HERO, "default")
        self.assertEqual(path, os.path.join(self.hero.folder, "looks", "default", "model", "hero_default_model.ma"))
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(cmds.file(query=True, sceneName=True), scene, "the scene is not saved or renamed")
        self.assertEqual(sorted(cmds.ls(long=True)), nodes, "nothing is left behind in the scene")
        self.assertEqual(cmds.namespaceInfo(currentNamespace=True), ":")

    def test_a_model_file_is_only_meshes(self):
        # Saved from a rig scene: the mesh is skinned, posed, parented under a group, and its material is in the
        # rig's namespace. The file holds the mesh at its bind shape and nothing of the rig.
        cmds = self.cmds
        self.tools.new_look(HERO)
        self.build_outside_the_asset(HERO)
        box = self.make_box("hero")
        mesh_id = cmds.setRigMeshId(box)[0]
        cmds.group(box, name="hero:geo_grp")
        box = cmds.ls("hero:box_geo", long=True)[0]
        self.red_material(box, "hero")
        cluster = self.skin_box(box)
        cmds.setAttr(cluster + ".envelope", 1)
        cmds.setAttr("hero:spine2_00_M_CTRL.translateX", 5)     # the pose moves the top of the box
        posed = cmds.xform(box + ".vtx[2]", query=True, worldSpace=True, translation=True)
        self.assertNotAlmostEqual(posed[0], -0.5)
        path = self.tools.save_model(HERO, "default")
        self.assertEqual(cmds.xform(box + ".vtx[2]", query=True, worldSpace=True, translation=True), posed, "still posed")
        self.assertEqual(cmds.ls(cmds.listHistory(box), type="skinCluster"), [cluster], "still skinned")
        self.assertFalse(cmds.namespace(exists=":bmaya_model_export"))

        cmds.file(new=True, force=True)
        new_nodes = cmds.file(path, i=True, type="mayaAscii", namespace="look", returnNewNodes=True)
        self.assertEqual(cmds.ls(type="joint"), [])
        self.assertEqual(cmds.ls(type="skinCluster"), [])
        self.assertEqual(cmds.ls("look:*", type="transform", long=True), ["|look:box_geo"], "at the top level, no group")
        self.assertEqual(cmds.listHistory("look:box_geo"), ["look:box_geoShape"], "no history")
        self.assertEqual(cmds.getAttr("look:box_geo.meshId"), mesh_id)
        # The box is 1 wide and 2 tall, standing on the origin: vertex 2 is a top corner, at its bind position.
        self.assertEqual(cmds.xform("look:box_geo.vtx[2]", query=True, worldSpace=True, translation=True), [-0.5, 2.0, 0.5])
        self.assertEqual(cmds.listConnections("look:box_geoShape", type="shadingEngine"), ["look:red_matSG"])
        self.assertEqual(cmds.listConnections("look:red_matSG.surfaceShader"), ["look:red_mat"])
        self.assertFalse(cmds.namespace(exists=":hero"), "the rig's namespace is not in the file")
        self.assertEqual(sorted(cmds.nodeType(node) for node in new_nodes if cmds.nodeType(node) in ("joint", "skinCluster", "rigRootModule")), [])

    def test_save_model_of_named_meshes_and_of_two_with_one_name(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        box = self.make_box()
        crate = cmds.rename(self.make_box(), "crate_geo")
        path = self.tools.save_model(HERO, "default", meshes=[crate])
        cmds.file(new=True, force=True)
        cmds.file(path, i=True, type="mayaAscii", namespace="look")
        self.assertEqual(cmds.ls("look:*", type="transform"), ["look:crate_geo"])

        cmds.file(new=True, force=True)
        cmds.namespace(add="a")
        with self.assertRaisesRegex(RuntimeError, "used twice: box_geo"):
            self.tools.save_model(HERO, "default", meshes=[self.make_box(), self.make_box("a")])
        del box

    def test_save_model_needs_the_look_and_a_mesh(self):
        self.make_box()
        with self.assertRaisesRegex(RuntimeError, "Add it with New Look first"):
            self.tools.save_model(HERO, "default")
        self.tools.new_look(HERO)
        self.cmds.file(new=True, force=True)
        with self.assertRaisesRegex(RuntimeError, "no meshes"):
            self.tools.save_model(HERO, "default")

    def test_skin_weights_round_trip_through_the_assets_look(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        rig_root = self.build_outside_the_asset(HERO)
        box = self.make_box("hero")
        cmds.setRigMeshId(box)
        cluster = self.skin_box(box)
        saved = self.spine2_weights(box)
        files = self.tools.save_skin_weights(rig_root)   # no prompter: a question would raise
        self.assertEqual([os.path.basename(f) for f in files], ["box_geo.json"])
        self.assertEqual(os.path.dirname(files[0]), os.path.join(self.hero.folder, "looks", "default", "weights"))
        cmds.delete(cluster)
        self.assertEqual([m.split("|")[-1] for m in self.tools.load_skin_weights(rig_root)], ["hero:box_geo"])
        self.assertEqual(self.spine2_weights(box), saved)

    def test_skin_weights_say_which_look_when_the_rig_can_wear_several(self):
        # A built rig doesn't record its look yet, so the tools can't guess between two.
        cmds = self.cmds
        self.tools.new_rig(HERO, self.template)
        self.tools.new_look(HERO)
        self.tools.new_look(HERO, "winter")
        self.tools.new_look(HERO, "head", skeleton="face")       # not for the rig's skeleton: never offered
        rig_root = self.build_outside_the_asset(HERO)
        box = self.make_box("hero")
        cmds.setRigMeshId(box)
        self.skin_box(box)
        with self.assertRaisesRegex(RuntimeError, r"has 2 looks for the rig 'game' \(default, winter\): say which look"):
            self.tools.save_skin_weights(rig_root)
        files = self.tools.save_skin_weights(rig_root, "winter")
        self.assertEqual(os.path.dirname(files[0]), os.path.join(self.hero.folder, "looks", "winter", "weights"))
        with self.assertRaisesRegex(RuntimeError, "has no look 'summer'"):
            self.tools.load_skin_weights(rig_root, "summer")

        self.cmds.select(clear=True)
        answers = self.answers("default")
        with self.active_rig(rig_root):
            self.tools.save_skin_weights_interactive(prompter=answers)
        self.assertEqual(answers.asked[0].options, ("default", "winter"))
        self.assertTrue(os.path.isfile(os.path.join(self.hero.folder, "looks", "default", "weights", "box_geo.json")))
        cancelled = self.answers(None)
        with self.active_rig(rig_root):
            self.tools.load_skin_weights_interactive(prompter=cancelled)   # cancelled: nothing loads, nothing raises

    def test_skin_weights_need_a_look(self):
        rig_root = self.build_outside_the_asset(HERO)
        with self.assertRaisesRegex(RuntimeError, "Add one with New Look"):
            self.tools.save_skin_weights(rig_root)

    def test_save_skin_weights_needs_marked_meshes(self):
        self.tools.new_look(HERO)
        rig_root = self.build_outside_the_asset(HERO)
        self.skin_box(self.make_box("hero"))
        with self.assertRaisesRegex(RuntimeError, "Mark Meshes for Skinning"):
            self.tools.save_skin_weights(rig_root)

    def test_a_renamed_mesh_replaces_its_old_weight_file(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        rig_root = self.build_outside_the_asset(HERO)
        box = self.make_box("hero")
        cmds.setRigMeshId(box)
        self.skin_box(box)
        self.tools.save_skin_weights(rig_root)
        cmds.rename(box, ":hero:crate_geo")
        files = self.tools.save_skin_weights(rig_root)
        self.assertEqual([os.path.basename(f) for f in files], ["crate_geo.json"])
        self.assertEqual(sorted(os.listdir(self.hero.path("weights", "default"))), ["crate_geo.json"])

    def test_load_skips_a_file_whose_mesh_is_not_in_the_scene(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        rig_root = self.build_outside_the_asset(HERO)
        box = self.make_box("hero")
        cmds.setRigMeshId(box)
        self.skin_box(box)
        self.tools.save_skin_weights(rig_root)
        cmds.delete(box)
        self.assertEqual(self.tools.load_skin_weights(rig_root), [])

    def test_load_skin_weights_is_one_undo_step(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        rig_root = self.build_outside_the_asset(HERO)
        box = self.make_box("hero")
        cmds.setRigMeshId(box)
        cluster = self.skin_box(box)
        self.tools.save_skin_weights(rig_root)
        cmds.delete(cluster)
        cmds.undoInfo(state=True, infinity=True)
        self.tools.load_skin_weights(rig_root)
        cmds.undo()
        self.assertEqual(cmds.ls(cmds.listHistory(box), type="skinCluster"), [])

    def test_weights_use_a_folder_dialog_before_the_asset_exists(self):
        cmds = self.cmds
        rig_root = self.build_outside_the_asset("shooter\\main\\characters\\nobody")
        box = self.make_box("nobody")
        cmds.setRigMeshId(box)
        self.skin_box(box, "nobody")
        folder = os.path.join(self.temp, "chosen_weights")
        answers = self.answers(folder)
        self.tools.save_skin_weights(rig_root, prompter=answers)
        self.assertEqual(answers.asked[0].default, self.root, "the folder question starts in the projects root")
        self.assertEqual(os.listdir(folder), ["box_geo.json"])

    def make_look(self, look="default", material=False):
        """Saves a marked box as a look's model, from a scene of its own, and returns to a new scene."""
        cmds = self.cmds
        cmds.file(new=True, force=True)
        if look not in self.hero.looks:
            self.tools.new_look(HERO, look)
        box = self.make_box()
        cmds.setRigMeshId(box)
        if material:
            self.red_material(box)
        self.tools.save_model(HERO, look)
        cmds.file(new=True, force=True)

    def test_build_rig_puts_the_default_look_on_the_rig(self):
        cmds = self.cmds
        self.make_buildable_asset()
        self.make_look(material=True)

        rig_root = self.tools.build_rig(HERO, "game")     # no look named: the asset's "default"
        self.assertEqual(cmds.ls(cmds.listHistory("hero_game:box_geo"), type="skinCluster"), [], "a model is only meshes")
        self.assertEqual(cmds.listConnections("hero_game:box_geoShape", type="shadingEngine"), ["hero_game:red_matSG"])
        self.skin_box("hero_game:box_geo", namespace="hero_game")
        saved = self.spine2_weights("hero_game:box_geo", namespace="hero_game")
        self.tools.save_skin_weights(rig_root)
        # The look is saved again from the rig scene, as a rigger does after editing a mesh: still only meshes.
        self.tools.save_model(HERO, "default")

        cmds.file(new=True, force=True)
        self.tools.build_rig(HERO, "game")
        self.assertEqual(self.spine2_weights("hero_game:box_geo", namespace="hero_game"), saved)
        self.assertEqual(cmds.listConnections("hero_game:box_geoShape", type="shadingEngine"), ["hero_game:red_matSG"],
                         "the material keeps its name through a save from the rig scene")
        self.assertEqual(len(cmds.ls(type="skinCluster")), 1)

    def test_build_rig_with_a_named_look_and_with_none(self):
        cmds = self.cmds
        self.make_buildable_asset()
        self.make_look("winter")
        self.tools.build_rig(HERO, "game")                 # the asset has no "default" look: the rig is built bare
        self.assertEqual(cmds.ls(type="mesh"), [])
        cmds.file(new=True, force=True)
        self.tools.build_rig(HERO, "game", "winter")
        self.assertTrue(cmds.objExists("hero_game:box_geo"))

    def test_build_rig_refuses_a_look_before_it_creates_anything(self):
        self.make_buildable_asset()
        self.tools.new_look(HERO, "head", skeleton="face")
        with self.assertRaisesRegex(RuntimeError, "The look 'head' of .* is not for the skeleton 'default'"):
            self.tools.build_rig(HERO, "game", "head")
        with self.assertRaisesRegex(RuntimeError, "has no look 'summer'"):
            self.tools.build_rig(HERO, "game", "summer")
        self.assertEqual(self.cmds.ls(type="joint"), [])
        self.assertFalse(self.cmds.namespace(exists=":hero_game"))

    # ---- looks on the rig (RigModules D54 phase 5) ----

    def make_two_looks(self):
        """The hero's rig game with two looks that have a model and weights: "default" is a box, "winter" a ball."""
        cmds = self.cmds
        self.make_buildable_asset()
        self.make_look("default")
        cmds.file(new=True, force=True)
        self.tools.new_look(HERO, "winter")
        ball = cmds.polySphere(name="ball_geo", constructionHistory=False)[0]
        cmds.setRigMeshId(ball)
        self.tools.save_model(HERO, "winter")
        for look, mesh in (("default", "hero_game:box_geo"), ("winter", "hero_game:ball_geo")):
            cmds.file(new=True, force=True)
            rig_root = self.tools.build_rig(HERO, "game", look)   # a model with no weights yet: the meshes only
            self.skin_box(mesh, namespace="hero_game")
            self.tools.save_skin_weights(rig_root, look)
        cmds.file(new=True, force=True)

    def look_of(self, rig_root):
        import rigmodules.query
        return rigmodules.query.get_rig_info(rig_root).look

    def test_build_rig_records_the_look_and_the_weight_tools_follow_it(self):
        cmds = self.cmds
        self.make_buildable_asset()
        self.make_look()
        rig_root = self.tools.build_rig(HERO, "game")
        self.assertIsNone(self.look_of(rig_root), "a model with no weights is imported bare, and records no look")
        self.skin_box("hero_game:box_geo", namespace="hero_game")
        self.tools.save_skin_weights(rig_root)
        cmds.file(new=True, force=True)

        rig_root = self.tools.build_rig(HERO, "game")
        look = self.look_of(rig_root)
        self.assertEqual((look.asset_id, look.name), (HERO, "default"))
        self.tools.new_look(HERO, "winter")
        path = os.path.join(self.hero.folder, "looks", "default", "weights", "box_geo.json")
        os.remove(path)
        self.tools.save_skin_weights(rig_root)   # two looks now and none named: the one the rig wears
        self.assertTrue(os.path.isfile(path))
        self.assertEqual([m.split("|")[-1] for m in self.tools.load_skin_weights(rig_root)], ["hero_game:box_geo"])

    def test_apply_look_swaps_the_rigs_look(self):
        cmds = self.cmds
        self.make_two_looks()
        rig_root = self.tools.build_rig(HERO, "game", "default")
        self.assertTrue(cmds.objExists("hero_game:box_geo"))
        cmds.setAttr("hero_game:spine1_00_M_CTRL.rotateZ", 30)

        look_root = self.tools.apply_look(rig_root, "winter")
        self.assertEqual(look_root, "hero_game:lookRoot")
        self.assertEqual(self.look_of(rig_root).name, "winter")
        self.assertFalse(cmds.objExists("hero_game:box_geo"))
        self.assertEqual(len(cmds.ls(type="skinCluster")), 1)
        self.assertTrue(cmds.ls(cmds.listHistory("hero_game:ball_geo"), type="skinCluster"))
        self.assertAlmostEqual(cmds.getAttr("hero_game:spine1_00_M_CTRL.rotateZ"), 30, places=5)
        self.assertTrue(cmds.listRelatives("hero_game:ball_geo", parent=True), "the new mesh joins the rig's mesh group")

        cmds.undo()
        self.assertEqual(self.look_of(rig_root).name, "default")
        self.assertTrue(cmds.objExists("hero_game:box_geo"))
        self.assertTrue(cmds.ls(cmds.listHistory("hero_game:box_geo"), type="skinCluster"))

    def make_unsynced_winter(self):
        """make_two_looks, then the winter look's folder moved out of the workspace into a fake depot that syncs it
        back. Returns the depot."""
        import bmaya.core.asset.sourcecontrol
        self.make_two_looks()
        folder = os.path.join(self.hero.folder, "looks", "winter")
        depot_folder = os.path.join(self.hero.folder, "depot_winter")   # outside looks/, so it is not scanned
        shutil.move(folder, depot_folder)

        class Depot(bmaya.core.asset.sourcecontrol.SourceControl):
            fails = False

            def list_folders(self, path):
                return ["default", "winter"]

            def sync(self, path):
                if self.fails:
                    raise ConnectionError("server down")
                shutil.copytree(depot_folder, path)

        depot = Depot()
        bmaya.core.asset.sourcecontrol.set_current(depot)
        self.addCleanup(bmaya.core.asset.sourcecontrol.set_current, bmaya.core.asset.sourcecontrol.SourceControl())
        return depot

    def test_apply_look_syncs_a_look_that_is_not_local_first(self):
        cmds = self.cmds
        depot = self.make_unsynced_winter()
        rig_root = self.tools.build_rig(HERO, "game", "default")
        self.assertFalse(self.hero.file_exists("lookinfo", "winter"))
        self.assertEqual([(entry.name, entry.local) for entry in self.tools.list_rig_looks(self.hero, "game")],
                         [("default", True), ("winter", False)])
        self.tools.apply_look(rig_root, "winter")
        self.assertTrue(self.hero.file_exists("lookinfo", "winter"))
        self.assertEqual(self.look_of(rig_root).name, "winter")
        self.assertTrue(cmds.objExists("hero_game:ball_geo"))

    def test_apply_look_with_a_failed_sync_changes_nothing(self):
        cmds = self.cmds
        depot = self.make_unsynced_winter()
        rig_root = self.tools.build_rig(HERO, "game", "default")
        depot.fails = True
        with self.assertRaisesRegex(RuntimeError, "Could not sync the look 'winter'"):
            self.tools.apply_look(rig_root, "winter")
        self.assertEqual(self.look_of(rig_root).name, "default")
        self.assertTrue(cmds.objExists("hero_game:box_geo"))
        self.assertFalse(cmds.objExists("hero_game:ball_geo"))

    def test_apply_look_that_does_not_fit_after_syncing_changes_nothing(self):
        cmds = self.cmds
        depot = self.make_unsynced_winter()
        look_json = os.path.join(self.hero.folder, "depot_winter", "look.json")
        data = self.read_json(look_json)
        data["skeletons"] = ["face"]
        with open(look_json, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        rig_root = self.tools.build_rig(HERO, "game", "default")
        with self.assertRaisesRegex(RuntimeError, "is not for the skeleton"):
            self.tools.apply_look(rig_root, "winter")
        self.assertEqual(self.look_of(rig_root).name, "default")
        self.assertTrue(cmds.objExists("hero_game:box_geo"))
        self.assertFalse(cmds.objExists("hero_game:ball_geo"))

    def test_apply_look_with_another_skeletons_weights_fails_and_leaves_the_rig_alone(self):
        cmds = self.cmds
        self.make_two_looks()
        weights = os.path.join(self.hero.folder, "looks", "winter", "weights", "ball_geo.json")
        data = self.read_json(weights)
        data["skeletonHash"] = "0000000000000000"
        with open(weights, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        rig_root = self.tools.build_rig(HERO, "game", "default")
        import bmaya.core.asset
        with self.assertRaisesRegex(bmaya.core.asset.AssetError, "saved from another skeleton.*ball_geo.json.*ignore_skeleton_hash"):
            self.tools.apply_look(rig_root, "winter")
        self.assertEqual(self.look_of(rig_root).name, "default")
        self.assertTrue(cmds.objExists("hero_game:box_geo"))
        self.assertFalse(cmds.objExists("hero_game:ball_geo"), "checked before the model is imported")

        self.tools.apply_look(rig_root, "winter", ignore_skeleton_hash=True)
        self.assertEqual(self.look_of(rig_root).name, "winter")
        self.assertTrue(cmds.ls(cmds.listHistory("hero_game:ball_geo"), type="skinCluster"))

    def test_build_rig_passes_ignore_skeleton_hash_to_the_look(self):
        cmds = self.cmds
        self.make_two_looks()
        weights = os.path.join(self.hero.folder, "looks", "default", "weights", "box_geo.json")
        data = self.read_json(weights)
        data["skeletonHash"] = "0000000000000000"
        with open(weights, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        with self.assertRaisesRegex(RuntimeError, "saved from another skeleton"):
            self.tools.build_rig(HERO, "game", "default")
        cmds.file(new=True, force=True)
        rig_root = self.tools.build_rig(HERO, "game", "default", ignore_skeleton_hash=True)
        self.assertEqual(self.look_of(rig_root).name, "default")

    def test_apply_look_drops_a_mesh_with_no_weight_file(self):
        cmds = self.cmds
        self.make_two_looks()
        import bmaya.core.asset
        import bmaya.maya.assethandlers
        bmaya.maya.assethandlers.register()
        bmaya.core.asset.handlers.load(self.hero, "model", "winter")
        target = cmds.polyCube(name="target_geo", constructionHistory=False)[0]
        cmds.setRigMeshId(target)
        self.tools.save_model(HERO, "winter")
        cmds.file(new=True, force=True)

        rig_root = self.tools.build_rig(HERO, "game", "default")
        self.tools.apply_look(rig_root, "winter")
        self.assertEqual(self.look_of(rig_root).name, "winter")
        self.assertTrue(cmds.objExists("hero_game:ball_geo"))
        self.assertFalse(cmds.ls("hero_game:target_geo*"), "a mesh with no weight file is not left behind")

    def test_apply_look_with_a_weight_file_for_a_missing_mesh_fails_and_cleans_up(self):
        cmds = self.cmds
        self.make_two_looks()
        folder = os.path.join(self.hero.folder, "looks", "winter", "weights")
        data = self.read_json(os.path.join(folder, "ball_geo.json"))
        data["meshId"] = "00000000-0000-0000-0000-000000000000"
        with open(os.path.join(folder, "gone_geo.json"), "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        rig_root = self.tools.build_rig(HERO, "game", "default")
        import bmaya.core.asset
        with self.assertRaisesRegex(bmaya.core.asset.AssetError, "meshes its model doesn't have"):
            self.tools.apply_look(rig_root, "winter")
        self.assertEqual(self.look_of(rig_root).name, "default")
        self.assertFalse(cmds.ls("hero_game:ball_geo*"), "everything the import made is removed again")

    def test_apply_look_needs_a_model_and_weights(self):
        import bmaya.core.asset
        self.make_two_looks()
        rig_root = self.tools.build_rig(HERO, "game", "default")
        self.tools.new_look(HERO, "empty")
        with self.assertRaisesRegex(bmaya.core.asset.AssetError, "has no model file"):
            self.tools.apply_look(rig_root, "empty")
        with self.assertRaisesRegex(bmaya.core.asset.AssetError, "has no look 'summer'"):
            self.tools.apply_look(rig_root, "summer")

    def test_rig_tools_need_a_rig_node(self):
        self.make_skeleton()
        with self.assertRaises(RuntimeError):
            self.tools.save_control_shapes("spine1_00_M_JNT")

    # ---- menu entry points ----

    def test_new_asset_creates_the_asset_with_the_chosen_type(self):
        answers = self.answers("shooter\\main\\props\\crate", "Prop")
        self.tools.new_asset_interactive(prompter=answers)
        import bmaya.core.asset
        self.assertEqual(bmaya.core.asset.Asset("shooter\\main\\props\\crate").asset_type, "Prop")
        self.assertIn("Prop", answers.asked[1].options)

    def test_new_asset_without_a_project_fails(self):
        import bmaya.core.asset
        with self.assertRaises(bmaya.core.asset.ProjectError):
            self.tools.new_asset_interactive(prompter=self.answers("elsewhere\\props\\crate"))

    def test_new_project_writes_a_project_json(self):
        folder = os.path.join(self.root, "other", "main")
        self.tools.new_project_interactive(prompter=self.answers(folder))
        self.assertTrue(os.path.isfile(os.path.join(folder, "project.json")))

    def test_asset_id_dialog_starts_with_the_active_rig_asset(self):
        self.build_outside_the_asset(HERO)
        self.cmds.select(clear=True)
        answers = self.answers(HERO, self.template, "body", "default", "none")
        self.tools.new_rig_interactive(prompter=answers)
        self.assertEqual(answers.asked[0].default, HERO)
        self.assertEqual(answers.asked[2].default, "game", "the template's rigName is offered as the rig's name")
        self.assertEqual((answers.asked[3].kind, answers.asked[3].default), ("ask_text", "default"),
                         "no skeleton is saved yet, so its name is typed, with default offered")
        self.assertEqual(self.hero.rigs, ["body"])
        self.assertEqual(self.read_json(self.hero.path("template", "body"))["rigName"], "body")

    def test_new_rig_and_new_look_take_the_assets_only_skeleton_and_choose_between_several(self):
        self.tools.save_skeleton(HERO, joints=self.make_skeleton())
        self.tools.new_rig_interactive(prompter=self.answers(HERO, self.template, "game", "none"))   # one skeleton: not asked
        self.assertEqual(self.read_json(self.hero.path("riginfo", "game"))["skeleton"], "default")
        look = self.answers(HERO, "default")
        self.tools.new_look_interactive(prompter=look)
        self.assertEqual(look.asked[1].default, "default", "the first look is offered as default")
        self.assertEqual(self.hero.looks, ["default"])

        self.tools.save_skeleton(HERO, "face", joints=self.cmds.ls(type="joint"))
        winter = self.answers(HERO, "winter", "face")
        self.tools.new_look_interactive(prompter=winter)
        self.assertEqual(winter.asked[1].default, "", "only the first look is offered a name")
        self.assertEqual(winter.asked[2].options, ("default", "face"))
        self.assertEqual(self.read_json(self.hero.path("lookinfo", "winter"))["skeletons"], ["face"])

    def test_cancelled_new_rig_and_new_look_write_nothing(self):
        for answers in ((None,), (HERO, None), (HERO, self.template, None), (HERO, self.template, "game", None),
                        (HERO, self.template, "game", "default", None)):
            self.tools.new_rig_interactive(prompter=self.answers(*answers))
        for answers in ((None,), (HERO, None), (HERO, "default", None)):
            self.tools.new_look_interactive(prompter=self.answers(*answers))
        self.assertEqual((self.hero.rigs, self.hero.looks), ([], []))

    def test_save_and_load_skeleton_dialogs(self):
        cmds = self.cmds
        self.make_skeleton()
        first = self.answers(HERO, "default")
        self.tools.save_skeleton_interactive(prompter=first)
        self.assertEqual(first.asked[1].default, "default", "the first skeleton is offered as default")
        again = self.answers(HERO, "default")
        self.tools.save_skeleton_interactive(prompter=again)
        self.assertEqual(again.asked[1].default, "default", "the asset's only skeleton is offered")
        cmds.file(new=True, force=True)
        self.tools.load_skeleton_interactive(prompter=self.answers(HERO))    # one skeleton: no question for it
        self.assertEqual(cmds.ls(selection=True), ["spine1_00_M_JNT", "spine2_00_M_JNT"])
        import bmaya.core.asset
        bmaya.core.asset.Asset.create(VILLAIN, "Character")
        with self.assertRaisesRegex(RuntimeError, "has no skeletons. Add one with Save Skeleton first"):
            self.tools.load_skeleton_interactive(prompter=self.answers(VILLAIN))

    def test_save_model_dialog_saves_the_selected_meshes(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        self.make_box()
        crate = cmds.rename(self.make_box(), "crate_geo")
        cmds.select(crate, replace=True)
        self.tools.save_model_interactive(prompter=self.answers(HERO))        # one look: no question for it
        cmds.file(new=True, force=True)
        cmds.file(self.hero.path("model", "default"), i=True, type="mayaAscii", namespace="look")
        self.assertEqual(cmds.ls("look:*", type="transform"), ["look:crate_geo"])

    def test_asset_id_dialog_starts_empty_without_a_rig(self):
        answers = self.answers(None)
        self.tools.save_skeleton_interactive(prompter=answers)
        self.assertEqual(answers.asked[0].default, "")
        self.assertEqual(len(answers.asked), 1, "cancelled at the asset id: nothing else is asked")

    def test_shape_menu_tool_uses_the_active_rig(self):
        self.build_outside_the_asset(HERO)
        self.cmds.select(clear=True)
        self.tools.save_control_shapes_interactive()
        self.assertTrue(self.hero.file_exists("shapes", "game"))

    def test_build_rig_selects_the_new_rig_root(self):
        self.make_buildable_asset()
        self.tools.build_rig_interactive(prompter=self.answers(HERO))   # one rig and no look: no question for either
        import rigmodules.query
        self.assertEqual(self.cmds.ls(selection=True), [rigmodules.query.get_rigs("hero_game")[0].rig_root])

    def test_build_rig_dialog_asks_for_the_look_only_when_there_are_several(self):
        self.make_buildable_asset()
        self.make_look()
        self.tools.build_rig_interactive(prompter=self.answers(HERO))   # one look the rig can wear: not asked
        self.assertTrue(self.cmds.objExists("hero_game:box_geo"))

        self.make_look("winter")
        self.tools.new_look(HERO, "head", skeleton="face")
        answers = self.answers(HERO, "winter")
        self.tools.build_rig_interactive(prompter=answers)
        self.assertEqual(answers.asked[1].options, ("default", "winter"), "a look for another skeleton is not offered")
        self.cmds.file(new=True, force=True)
        self.tools.build_rig_interactive(prompter=self.answers(HERO, None))   # cancelled at the look: nothing built
        self.assertEqual(self.cmds.ls(type="joint"), [])

    # ---- attachments (RigModules D55) ----

    def make_joint_chain(self, usages, heights, chained=True):
        """Marked joints at the given heights: a chain, or unparented roots (a face's joints hang off no joint)."""
        cmds = self.cmds
        joints = []
        for usage, height in zip(usages, heights):
            if chained and joints:
                cmds.select(joints[-1], replace=True)
            else:
                cmds.select(clear=True)
            joint = cmds.joint(name=f"{usage}_00_M_JNT", position=(0, height, 0))
            cmds.rigJointMarkup(joint, usage=usage, side="Center", export=True, skin=True)
            joints.append(joint)
        return joints

    def make_attachable_asset(self):
        """The hero with the rigs body (skeleton default: a, b, c) and face (skeleton face: n, fA, fB), the face
        attached to the body. The face template is RigModules' attach_face fixture: its chain starts on the body's
        fkChain_00_M_MOD.end and its neckCopy_00_M_MOD follows fkChain_00_M_MOD.index_1. Skeletons are saved, the scene is new."""
        import bmaya.core.asset
        body = {"rigVersion": 1, "rigTemplateName": "AttachBody", "rigName": "body", "rigAuthor": "tests",
                "rigModules": [{"moduleType": "FkChain", "name": "fkChain_00_M_MOD", "shapeType": "Box", "side": "Center",
                                "moduleArgs": {"joints": [["Center", "a"], ["Center", "b"], ["Center", "c"]]}}]}
        face = {"rigVersion": 1, "rigTemplateName": "AttachFace", "rigName": "face", "rigAuthor": "tests",
                "rigModules": [
                    {"moduleType": "FkChain", "name": "faceChain_00_M_MOD", "shapeType": "Box", "side": "Center",
                     "moduleArgs": {"joints": [["Center", "fA"], ["Center", "fB"]]},
                     "parentStructure": {"start": "parent:fkChain_00_M_MOD.end"}},
                    {"moduleType": "FkChain", "name": "neckCopy_00_M_MOD", "shapeType": "Box", "side": "Center",
                     "moduleArgs": {"joints": [["Center", "n"]]}}],
                "constraints": [{"name": "neckFollow_00_M_CON", "target": "neckCopy_00_M_MOD.start",
                                 "drivers": [{"socket": "parent:fkChain_00_M_MOD.index_1", "label": "Body"}]}]}
        self.tools.new_rig(HERO, self.write_template(body, "body.json"), "body")
        self.tools.new_rig(HERO, self.write_template(face, "face.json"), "face", skeleton="face",
                           parent=bmaya.core.asset.RigRef("body"))
        self.tools.save_skeleton(HERO, "default", joints=self.make_joint_chain(("a", "b", "c"), (0, 2, 4)))
        self.cmds.file(new=True, force=True)
        self.tools.save_skeleton(HERO, "face", joints=self.make_joint_chain(("n", "fA", "fB"), (2, 5, 6), chained=False))
        self.cmds.file(new=True, force=True)

    def make_spanning_look(self):
        """A look "default" that names both skeletons: one model (box_geo for the body, face_geo for the face) and
        one weights folder (a file for each). The scene is new afterwards."""
        import bmaya.core.asset
        cmds = self.cmds
        self.hero.add_look("default", [bmaya.core.asset.SkeletonRef("default"), bmaya.core.asset.SkeletonRef("face")])
        for mesh in (self.make_box(), cmds.polyCube(name="face_geo", constructionHistory=False)[0]):
            cmds.setRigMeshId(mesh)
        self.tools.save_model(HERO, "default")
        cmds.file(new=True, force=True)
        # With no weights yet, a look imports its whole model bare into each rig: skin each rig's own mesh from there.
        face_root = self.tools.build_rig(HERO, "face")
        body_root = self.rig_root("hero_body")
        cmds.skinCluster("hero_body:a_00_M_JNT", "hero_body:b_00_M_JNT", "hero_body:box_geo", toSelectedBones=True)
        cmds.skinCluster("hero_face:fA_00_M_JNT", "hero_face:fB_00_M_JNT", "hero_face:face_geo", toSelectedBones=True)
        self.tools.save_skin_weights(body_root, "default")
        self.tools.save_skin_weights(face_root, "default")
        cmds.file(new=True, force=True)

    def rig_root(self, namespace):
        import rigmodules.query
        (info,) = rigmodules.query.get_rigs(namespace)
        return info.rig_root

    def test_new_rig_writes_the_parent(self):
        import bmaya.core.asset
        self.tools.new_rig(HERO, self.template, "body")
        self.tools.new_rig(HERO, self.template, "face", skeleton="face", parent=bmaya.core.asset.RigRef("body"))
        self.tools.new_rig(HERO, self.template, "hat", skeleton="hat",
                           parent=bmaya.core.asset.RigRef("face", VILLAIN))
        self.assertEqual(self.read_json(self.hero.path("riginfo", "face")),
                         {"formatVersion": 1, "skeleton": "face", "parent": "body"})
        self.assertEqual(self.read_json(self.hero.path("riginfo", "hat"))["parent"], {"asset": VILLAIN, "rig": "face"})

    def test_new_rig_with_a_parent_loop_writes_nothing(self):
        import bmaya.core.asset
        self.tools.new_rig(HERO, self.template, "face", skeleton="face", parent=bmaya.core.asset.RigRef("body"))
        with self.assertRaisesRegex(RuntimeError, "attach to itself"):
            self.tools.new_rig(HERO, self.template, "body", parent=bmaya.core.asset.RigRef("face"))
        self.assertEqual(self.hero.rigs, ["face"])
        self.assertFalse(os.path.exists(os.path.dirname(self.hero.path("template", "body"))),
                         "the template is not copied for a rig that is refused")

    def test_new_rig_dialog_asks_what_the_rig_attaches_to(self):
        import bmaya.core.asset
        self.tools.save_skeleton(HERO, joints=self.make_skeleton())
        self.tools.new_rig(HERO, self.template, "body")
        answers = self.answers(HERO, self.template, "face", "body")
        self.tools.new_rig_interactive(prompter=answers)
        self.assertEqual(answers.asked[3].options, ("none", "body", "another asset..."))
        self.assertEqual(self.hero.parent_of("face"), (self.hero, "body"))

        bmaya.core.asset.Asset.create(VILLAIN, "Character").add_rig("body", bmaya.core.asset.SkeletonRef("default"))
        self.tools.new_rig_interactive(prompter=self.answers(HERO, self.template, "hat", "another asset...", VILLAIN))
        self.assertEqual(self.read_json(self.hero.path("riginfo", "hat"))["parent"], {"asset": VILLAIN, "rig": "body"})

        self.tools.new_rig_interactive(prompter=self.answers(HERO, self.template, "prop", "none"))
        self.assertIsNone(self.hero.parent_of("prop"))

    def test_build_rig_builds_the_parent_first_and_the_attachment_follows_it(self):
        import rigmodules.query
        cmds = self.cmds
        self.make_attachable_asset()
        face_root = self.tools.build_rig(HERO, "face")
        body_root = self.rig_root("hero_body")
        self.assertEqual(rigmodules.query.get_rig_info(face_root).parent_rig_root, body_root)
        self.assertIsNone(rigmodules.query.get_rig_info(body_root).parent_rig_root)
        self.assertEqual(sorted(info.rig_name for info in rigmodules.query.get_rigs()), ["body", "face"])
        self.assertEqual(cmds.ls(selection=True), [], "a build leaves nothing selected")

        # A chest-up control of the body moves the face, which is the point of the attachment.
        before = cmds.xform("hero_face:fA_00_M_JNT", query=True, worldSpace=True, translation=True)
        cmds.setAttr("hero_body:a_00_M_CTRL.rotateZ", 90)
        after = cmds.xform("hero_face:fA_00_M_JNT", query=True, worldSpace=True, translation=True)
        self.assertGreater(max(abs(a - b) for a, b in zip(before, after)), 1.0)

    def test_build_rig_without_a_parent_is_as_before(self):
        import rigmodules.query
        self.make_attachable_asset()
        rig_root = self.tools.build_rig(HERO, "body")
        self.assertIsNone(rigmodules.query.get_rig_info(rig_root).parent_rig_root)
        self.assertEqual(len(rigmodules.query.get_rigs()), 1)

    def test_build_rig_reuses_the_parent_already_in_the_scene(self):
        import rigmodules.query
        self.make_attachable_asset()
        body_root = self.tools.build_rig(HERO, "body")
        face_root = self.tools.build_rig(HERO, "face")
        self.assertEqual(len(rigmodules.query.get_rigs()), 2)
        self.assertEqual(rigmodules.query.get_rig_info(face_root).parent_rig_root, body_root)

    def test_build_rig_refuses_several_candidate_parents_and_takes_the_one_named(self):
        import rigmodules.query
        self.make_attachable_asset()
        first = self.tools.build_rig(HERO, "body")
        second = self.tools.build_rig(HERO, "body", namespace="hero_body2")
        with self.assertRaisesRegex(RuntimeError, "2 copies of the rig 'body'.*parent_rig_root"):
            self.tools.build_rig(HERO, "face")
        self.assertEqual(rigmodules.query.get_rigs("hero_face"), [], "nothing was built")
        face_root = self.tools.build_rig(HERO, "face", parent_rig_root=second)
        self.assertEqual(rigmodules.query.get_rig_info(face_root).parent_rig_root, second)
        self.assertNotEqual(first, second)

    def test_build_rig_refuses_a_parent_rig_root_that_is_not_the_parent(self):
        self.make_attachable_asset()
        body_root = self.tools.build_rig(HERO, "body")
        self.cmds.createRigFromTemplate(
            *self.make_skeleton(), template=self.template.replace("\\", "/"), asset=VILLAIN, namespace="villain")
        villain_root = self.rig_root("villain")
        with self.assertRaisesRegex(RuntimeError, "is the rig 'game' of " + re.escape(VILLAIN) + ".*attaches to the rig 'body'"):
            self.tools.build_rig(HERO, "face", parent_rig_root=villain_root)
        with self.assertRaisesRegex(RuntimeError, "is not a rig"):
            self.tools.build_rig(HERO, "face", parent_rig_root="time1")
        with self.assertRaisesRegex(RuntimeError, "attaches to no rig, so it takes no parent_rig_root"):
            self.tools.build_rig(HERO, "body", namespace="hero_body2", parent_rig_root=body_root)
        self.assertEqual(self.cmds.ls("hero_face:*"), [], "a refused build creates nothing")

    def test_a_failed_attachment_leaves_the_parent_and_says_so(self):
        import rigmodules.query
        self.make_attachable_asset()
        path = self.hero.path("template", "face")
        data = self.read_json(path)
        data["rigModules"][0]["parentStructure"]["start"] = "parent:fkChain_00_M_MOD.no_such_socket"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        with self.assertRaisesRegex(RuntimeError, "(?s)attachment 'face'.*no_such_socket.*parent rig .*left in the scene"):
            self.tools.build_rig(HERO, "face")
        self.assertEqual([info.rig_name for info in rigmodules.query.get_rigs()], ["body"])

    def test_rigs_that_attach_to_each_other_in_a_loop_fail_to_build(self):
        import bmaya.core.asset.records
        self.make_attachable_asset()
        bmaya.core.asset.records.write_rig(
            self.hero.path("riginfo", "body"),
            bmaya.core.asset.RigRecord(bmaya.core.asset.SkeletonRef("default"), parent=bmaya.core.asset.RigRef("face")))
        with self.assertRaisesRegex(RuntimeError, "attach to each other in a loop"):
            self.tools.build_rig(HERO, "face")
        self.assertEqual(self.cmds.ls(type="joint"), [], "the loop is found before anything is created")

    def test_a_look_that_spans_both_skeletons_gives_each_rig_its_own_meshes_and_weights(self):
        import rigmodules.query
        cmds = self.cmds
        self.make_attachable_asset()
        self.make_spanning_look()
        face_root = self.tools.build_rig(HERO, "face")
        body_root = self.rig_root("hero_body")
        self.assertTrue(cmds.objExists("hero_body:box_geo"))
        self.assertFalse(cmds.objExists("hero_body:face_geo"), "the body keeps only its own mesh")
        self.assertTrue(cmds.objExists("hero_face:face_geo"))
        self.assertFalse(cmds.objExists("hero_face:box_geo"), "the face keeps only its own mesh")
        for mesh in ("hero_body:box_geo", "hero_face:face_geo"):
            self.assertEqual(len(cmds.ls(cmds.listHistory(mesh), type="skinCluster")), 1, mesh)
        self.assertEqual(len(cmds.ls(type="skinCluster")), 2)
        for root in (body_root, face_root):
            self.assertEqual(rigmodules.query.get_rig_info(root).look.name, "default")
        self.assertEqual(rigmodules.query.get_rig_info(face_root).parent_rig_root, body_root)

    def test_apply_look_on_a_spanning_look_takes_each_rigs_files_only(self):
        cmds = self.cmds
        self.make_attachable_asset()
        self.make_spanning_look()
        face_root = self.tools.build_rig(HERO, "face")
        body_root = self.rig_root("hero_body")
        self.tools.apply_look(face_root, "default")    # the same look again: the swap deletes and re-imports its meshes
        self.tools.apply_look(body_root, "default")
        self.assertEqual(sorted(cmds.ls(type="mesh", noIntermediate=True)), ["hero_body:box_geoShape", "hero_face:face_geoShape"])

    def test_a_weight_file_with_no_hash_is_refused_on_a_spanning_look(self):
        self.make_attachable_asset()
        self.make_spanning_look()
        path = os.path.join(self.hero.path("weights", "default"), "face_geo.json")
        data = self.read_json(path)
        data["skeletonHash"] = ""
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        with self.assertRaisesRegex(RuntimeError, "names several skeletons.*face_geo.json has no skeletonHash"):
            self.tools.build_rig(HERO, "body")

    def test_a_spanning_look_with_no_file_for_a_rig_is_refused_and_names_it(self):
        import rigmodules.query
        self.make_attachable_asset()
        self.make_spanning_look()
        os.remove(os.path.join(self.hero.path("weights", "default"), "face_geo.json"))
        with self.assertRaisesRegex(RuntimeError, "no weight file for the skeleton of the rig 'face'"):
            self.tools.build_rig(HERO, "face")
        # As for any rig whose look fails, the rig itself stays: bare, with no look recorded.
        self.assertEqual([(info.rig_name, info.look is not None) for info in rigmodules.query.get_rigs()],
                         [("body", True), ("face", False)])

    def test_a_look_of_one_skeleton_still_passes_every_file(self):
        # As before: no partition for a look that names one skeleton, so a file with no hash loads (an old file).
        self.make_buildable_asset()
        self.make_look()
        rig_root = self.tools.build_rig(HERO, "game")
        self.skin_box("hero_game:box_geo", namespace="hero_game")
        self.tools.save_skin_weights(rig_root)
        path = os.path.join(self.hero.path("weights", "default"), "box_geo.json")
        data = self.read_json(path)
        data["skeletonHash"] = ""
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        self.cmds.file(new=True, force=True)
        rig_root = self.tools.build_rig(HERO, "game")
        self.assertEqual(self.look_of(rig_root).name, "default")


class MirrorJoints(unittest.TestCase):
    """mirror_joints: a flat set of ribbon and twist joints (which Maya's Mirror Joint can't mirror in place) onto the
    other side. The joints sit under shoulder_00_L_JNT, whose R counterpart exists."""

    def setUp(self):
        from maya import cmds
        import bmaya.maya.assettools

        self.cmds = cmds
        self.tools = bmaya.maya.assettools
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True, infinity=True)
        self.shoulder_l = self.joint("shoulder_00_L_JNT", (5, 10, 0), None, "Left", "shoulder")
        self.shoulder_r = self.joint("shoulder_00_R_JNT", (-5, 10, 0), None, "Right", "shoulder")
        self.ribbon_0 = self.joint("ribbon_00_L_JNT", (8, 10, 2), self.shoulder_l, "Left", "ribbon0")
        self.ribbon_1 = self.joint("ribbon_01_L_JNT", (12, 10, 3), self.shoulder_l, "Left", "ribbon1")
        self.tip = self.joint("tip_00_L_JNT", (14, 11, 3), self.ribbon_1, "Left", "tip")

    def joint(self, name, position, parent, side, usage):
        cmds = self.cmds
        cmds.select(clear=True)
        joint = cmds.joint(name=name, position=position)
        if parent:
            joint = cmds.parent(joint, parent)[0]
        cmds.rigJointMarkup(joint, usage=usage, side=side, export=True, skin=True)
        return joint

    def position(self, joint):
        return [round(v, 4) for v in self.cmds.xform(joint, query=True, worldSpace=True, translation=True)]

    def test_mirrors_a_flat_set_across_yz_under_the_mirror_parent(self):
        result = self.tools.mirror_joints([self.ribbon_0, self.ribbon_1])
        self.assertEqual([r.rpartition("|")[2] for r in result], ["ribbon_00_R_JNT", "ribbon_01_R_JNT"])
        self.assertEqual(self.position("ribbon_00_R_JNT"), [-8, 10, 2])
        self.assertEqual(self.position("ribbon_01_R_JNT"), [-12, 10, 3])
        for name in ("ribbon_00_R_JNT", "ribbon_01_R_JNT"):
            self.assertEqual(self.cmds.listRelatives(name, parent=True), ["shoulder_00_R_JNT"])
        self.assertEqual(self.position(self.ribbon_0), [8, 10, 2])

    def test_a_selected_chain_keeps_its_hierarchy(self):
        self.tools.mirror_joints([self.ribbon_1, self.tip])
        self.assertEqual(self.cmds.listRelatives("tip_00_R_JNT", parent=True), ["ribbon_01_R_JNT"])
        self.assertEqual(self.position("tip_00_R_JNT"), [-14, 11, 3])

    def test_mirror_behavior_turns_the_joint_half_a_turn_about_x_with_no_negative_scale(self):
        self.tools.mirror_joints([self.ribbon_0])
        matrix = self.cmds.xform("ribbon_00_R_JNT", query=True, worldSpace=True, matrix=True)
        # Behavior keeps the bone axis and flips the other two, the same as Maya's own Mirror Joint on an identity joint.
        self.assertEqual([round(v, 4) + 0 for v in matrix[0:3] + matrix[4:7] + matrix[8:11]], [1, 0, 0, 0, -1, 0, 0, 0, -1])
        self.assertEqual([round(v, 4) for v in self.cmds.getAttr("ribbon_00_R_JNT.scale")[0]], [1, 1, 1])

    def test_markup_gets_the_mirrored_side_and_keeps_the_rest(self):
        self.tools.mirror_joints([self.ribbon_0])
        self.assertEqual(self.cmds.rigJointMarkup("ribbon_00_R_JNT", query=True, side=True), ["Right"])
        self.assertEqual(self.cmds.rigJointMarkup("ribbon_00_R_JNT", query=True, usage=True), ["ribbon0"])
        self.assertEqual(self.cmds.rigJointMarkup("ribbon_00_R_JNT", query=True, export=True), ["true"])
        self.assertEqual(self.cmds.rigJointMarkup("ribbon_00_L_JNT", query=True, side=True), ["Left"])

    def test_a_center_parent_is_kept(self):
        cmds = self.cmds
        cmds.select(clear=True)
        spine = cmds.joint(name="spine_00_M_JNT", position=(0, 5, 0))
        cmds.select(clear=True)
        twist = cmds.parent(cmds.joint(name="twist_00_L_JNT", position=(3, 5, 0)), spine)[0]
        self.tools.mirror_joints([twist])
        self.assertEqual(cmds.listRelatives("twist_00_R_JNT", parent=True), ["spine_00_M_JNT"])
        self.assertEqual(self.position("twist_00_R_JNT"), [-3, 5, 0])

    def test_namespaced_joints_mirror_into_the_same_namespace(self):
        cmds = self.cmds
        cmds.namespace(add="skel")
        cmds.select(clear=True)
        left = cmds.joint(name="skel:arm_L_JNT", position=(4, 8, 1))
        self.tools.mirror_joints([left])
        self.assertTrue(cmds.objExists("skel:arm_R_JNT"))
        self.assertEqual(self.position("skel:arm_R_JNT"), [-4, 8, 1])

    def test_no_temporary_nodes_are_left(self):
        before = set(self.cmds.ls(type="joint"))
        self.tools.mirror_joints([self.ribbon_0, self.ribbon_1])
        self.assertEqual(set(self.cmds.ls(type="joint")) - before, {"ribbon_00_R_JNT", "ribbon_01_R_JNT"})

    def test_it_is_one_undo_step(self):
        self.tools.mirror_joints([self.ribbon_0, self.ribbon_1, self.tip])
        self.cmds.undo()
        self.assertEqual(self.cmds.ls("*_R_JNT", type="joint"), ["shoulder_00_R_JNT"])
        self.cmds.redo()
        self.assertTrue(self.cmds.objExists("tip_00_R_JNT"))

    def test_refusals_change_nothing(self):
        cmds = self.cmds
        cmds.select(clear=True)
        center = cmds.joint(name="neck_00_M_JNT", position=(0, 12, 0))
        self.joint("ribbon_00_R_JNT", (-1, 1, 1), None, "Right", "taken")
        orphan = self.joint("orphan_00_L_JNT", (3, 3, 3), None, "Left", "orphan")
        lonely_parent = self.joint("elbow_00_L_JNT", (3, 3, 3), None, "Left", "elbow")
        child = self.joint("wrist_00_L_JNT", (4, 3, 3), lonely_parent, "Left", "wrist")
        before = set(cmds.ls(type="joint"))
        for joints, message in (([center], "neck_00_M_JNT isn't named"), ([self.ribbon_0], "ribbon_00_R_JNT already exists"),
                                ([child], "elbow_00_R_JNT doesn't exist")):
            with self.assertRaisesRegex(RuntimeError, message):
                self.tools.mirror_joints(joints)
        self.assertEqual(set(cmds.ls(type="joint")), before)
        self.assertTrue(orphan)


class AddTwistJoints(unittest.TestCase):
    """add_twist_joints: n joints in a line between a start and an end joint, parented to the start."""

    def setUp(self):
        from maya import cmds
        import bmaya.maya.assettools

        self.cmds = cmds
        self.tools = bmaya.maya.assettools
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True, infinity=True)
        cmds.select(clear=True)
        self.start = cmds.joint(name="shoulder_00_L_JNT", position=(0, 10, 0))
        cmds.rigJointMarkup(self.start, usage="shoulder", side="Left", export=True, skin=True)
        self.end = cmds.joint(name="elbow_00_L_JNT", position=(8, 10, 4))
        cmds.joint(self.start, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", zeroScaleOrient=True)

    def position(self, joint):
        return [round(v, 4) for v in self.cmds.xform(joint, query=True, worldSpace=True, translation=True)]

    def prompter(self, *answers):
        import bmaya.core.prompts
        return bmaya.core.prompts.ScriptedPrompter(answers)

    def test_the_ends_are_included_by_default_and_the_rest_are_evenly_spaced(self):
        joints = self.tools.add_twist_joints(self.start, self.end, 5, "shoulderTwist")
        self.assertEqual([j.rpartition("|")[2] for j in joints], [f"shoulderTwist_0{i}_L_JNT" for i in range(5)])
        self.assertEqual([self.position(j) for j in joints],
                         [[0, 10, 0], [2, 10, 1], [4, 10, 2], [6, 10, 3], [8, 10, 4]])

    def test_without_the_ends_they_sit_strictly_between(self):
        joints = self.tools.add_twist_joints(self.start, self.end, 3, "rib", include_ends=False)
        self.assertEqual([self.position(j) for j in joints], [[2, 10, 1], [4, 10, 2], [6, 10, 3]])

    def test_they_are_children_of_the_start_with_its_orientation(self):
        for joint in self.tools.add_twist_joints(self.start, self.end, 3, "t"):
            self.assertEqual(self.cmds.listRelatives(joint, parent=True), ["shoulder_00_L_JNT"])
            self.assertEqual(self.cmds.getAttr(f"{joint}.rotate")[0], (0, 0, 0))
            self.assertEqual(self.cmds.getAttr(f"{joint}.jointOrient")[0], (0, 0, 0))

    def test_they_lie_on_the_start_joints_bone_axis_when_it_aims_at_the_end(self):
        for joint in self.tools.add_twist_joints(self.start, self.end, 4, "t"):
            local = self.cmds.getAttr(f"{joint}.translate")[0]
            self.assertAlmostEqual(local[1], 0, places=4)
            self.assertAlmostEqual(local[2], 0, places=4)

    def test_markup_copies_the_side_and_numbers_the_usage(self):
        joints = self.tools.add_twist_joints(self.start, self.end, 2, "shoulderTwist", skin=False)
        self.assertEqual(self.cmds.rigJointMarkup(joints[1], query=True, usage=True), ["shoulderTwist_01"])
        self.assertEqual(self.cmds.rigJointMarkup(joints[1], query=True, side=True), ["Left"])
        self.assertEqual(self.cmds.rigJointMarkup(joints[1], query=True, skin=True), ["false"])
        self.assertEqual(self.cmds.rigJointMarkup(joints[1], query=True, export=True), ["true"])

    def test_a_start_without_markup_gives_joints_without_markup(self):
        self.cmds.rigJointMarkup(self.start, remove=True)
        joints = self.tools.add_twist_joints(self.start, self.end, 2, "t")
        self.assertEqual(self.cmds.rigJointMarkup(joints[0], query=True, usage=True), [""])

    def test_the_new_joints_are_selected_and_it_is_one_undo_step(self):
        joints = self.tools.add_twist_joints(self.start, self.end, 3, "t")
        self.assertEqual(self.cmds.ls(selection=True, long=True), joints)
        self.cmds.undo()
        self.assertEqual(self.cmds.ls("t_*", type="joint"), [])
        self.cmds.redo()
        self.assertEqual(len(self.cmds.ls("t_*", type="joint")), 3)

    def test_a_namespace_and_a_right_side_carry_over(self):
        cmds = self.cmds
        cmds.namespace(add="skel")
        cmds.select(clear=True)
        start = cmds.joint(name="skel:arm_00_R_JNT", position=(0, 0, 0))
        end = cmds.joint(name="skel:arm_01_R_JNT", position=(-6, 0, 0))
        joints = self.tools.add_twist_joints(start, end, 3, "armTwist")
        self.assertEqual([j.rpartition("|")[2] for j in joints], [f"skel:armTwist_0{i}_R_JNT" for i in range(3)])
        self.assertEqual(self.position(joints[1]), [-3, 0, 0])

    def test_refusals_create_nothing(self):
        cmds = self.cmds
        cmds.select(clear=True)
        cmds.joint(name="t_01_L_JNT", position=(1, 1, 1))
        cmds.select(clear=True)
        plain = cmds.joint(name="plain", position=(0, 0, 0))
        before = set(cmds.ls(type="joint"))
        for args, message in (((self.start, self.end, 1, "t"), "at least 2"),
                              ((self.start, self.end, 0, "t", True, False), "at least 1"),
                              ((self.start, self.end, 3, "t"), "t_01_L_JNT already exist"),
                              ((self.start, self.end, 3, "bad name"), "isn't a name"),
                              ((plain, self.end, 3, "t"), "plain isn't named")):
            with self.assertRaisesRegex(RuntimeError, message):
                self.tools.add_twist_joints(*args)
        self.assertEqual(set(cmds.ls(type="joint")), before)

    def test_the_tool_needs_exactly_two_selected_joints(self):
        self.cmds.select(self.start, replace=True)
        with self.assertRaisesRegex(RuntimeError, "start joint, then the end joint"):
            self.tools.add_twist_joints_interactive()

    def test_the_tool_uses_the_selection_order_and_the_form(self):
        self.cmds.select(self.start, self.end, replace=True)
        settings = self.tools.TwistJointSettings(name="tw", count=3, skin=False)
        joints = self.tools.add_twist_joints_interactive(self.prompter(settings))
        self.assertEqual(len(joints), 3)
        self.assertEqual(self.cmds.listRelatives(joints[0], parent=True), ["shoulder_00_L_JNT"])

    def test_a_cancelled_form_creates_nothing(self):
        self.cmds.select(self.start, self.end, replace=True)
        self.assertIsNone(self.tools.add_twist_joints_interactive(self.prompter(None)))
        self.assertEqual(self.cmds.ls("*tw*", type="joint"), [])


if __name__ == "__main__":
    unittest.main()
