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
HERO = "shooter\\main\\characters\\hero"
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "HandlerTest",
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


class MayaHandlers(unittest.TestCase):

    def setUp(self):
        from maya import cmds
        from bmaya.core.asset import Asset, Project, SkeletonRef, handlers
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
        # The hero has the rig "game" on its skeleton "default", and the look "default" (RigModules D54).
        self.hero = Asset.create(HERO, "Character", root=self.root)
        self.hero.add_rig("game", SkeletonRef("default"))
        self.hero.add_look("default", [SkeletonRef("default")])

        assethandlers.register()
        for file_type in ("skeleton", "model", "rig", "template", "weights", "shapes", "exports", "sources", "controlposes", "controlanims"):
            self.addCleanup(handlers.unregister, file_type)
        cmds.file(new=True, force=True)
        cmds.currentUnit(time="ntsc")   # the clips here are 30 fps

    def make_skeleton(self):
        cmds = self.cmds
        cmds.namespace(add=":skel")
        joints = []
        for i, usage in enumerate(("spine1", "spine2")):
            if joints:
                cmds.select(joints[-1], replace=True)
            else:
                cmds.select(clear=True)
            joint = cmds.joint(name=f":skel:{usage}_00_M_JNT", position=(0, i * 2, 0))
            cmds.rigJointMarkup(joint, usage=usage, side="Center", export=True, skin=True)
            joints.append(joint)
        return joints

    def build_rig(self):
        path = os.path.join(self.root, "template.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(TEMPLATE, handle)
        self.cmds.createRigFromTemplate(*self.make_skeleton(), template=path.replace("\\", "/"), asset=HERO, namespace="hero")
        return "hero:rigRootModule1"

    def test_shapes_save_and_load_through_rigmodules(self):
        cmds = self.cmds
        rig_root = self.build_rig()
        control = "hero:spine1_00_M_CTRL"
        self.assertEqual(cmds.getAttr(control + ".shapeType", asString=True), "Box")

        path = self.handlers.save(self.hero, "shapes", "game", rig_root=rig_root)
        self.assertEqual(path, self.hero.path("shapes", "game"))
        self.assertTrue(os.path.isfile(path))

        cmds.setAttr(control + ".shapeType", 1)  # Sphere
        loaded = self.handlers.load(self.hero, "shapes", "game", rig_root=rig_root)
        self.assertIn(control, [c.lstrip(":") for c in loaded])
        self.assertEqual(cmds.getAttr(control + ".shapeType", asString=True), "Box")

        self.handlers.save(self.hero, "shapes", "game", rig_root=rig_root)
        from bmaya.core.asset import versions
        self.assertEqual(len(versions.list_versions(path, self.root)), 1, "the second save keeps the first as a version")

    def test_shapes_need_a_rig_root(self):
        self.build_rig()
        with self.assertRaises(ValueError):
            self.handlers.save(self.hero, "shapes", "game")

    def test_a_skeleton_saves_as_its_skeleton_file_and_loads_as_joints(self):
        cmds = self.cmds
        joints = self.make_skeleton()
        path = self.handlers.save(self.hero, "skeleton", "default", joints=joints)
        self.assertEqual(path, os.path.join(self.hero.folder, "skeletons", "default", "skeleton.json"))
        data = self.read_json(path)
        self.assertEqual([joint["markup"] for joint in data["joints"]], [["Center", "spine1"], ["Center", "spine2"]])
        self.assertEqual(self.hero.skeletons, ["default"])

        cmds.file(new=True, force=True)
        loaded = self.handlers.load(self.hero, "skeleton", "default", namespace="hero_game")
        self.assertEqual(loaded, ["hero_game:spine1_00_M_JNT", "hero_game:spine2_00_M_JNT"])
        self.assertEqual(cmds.listRelatives("hero_game:spine2_00_M_JNT", parent=True), ["hero_game:spine1_00_M_JNT"])
        self.assertEqual(cmds.xform("hero_game:spine2_00_M_JNT", query=True, worldSpace=True, translation=True), [0.0, 2.0, 0.0])

        # A skeleton is not a scene: a second load into the same namespace is refused, where an import would merge.
        with self.assertRaisesRegex(RuntimeError, "already exists in the namespace"):
            self.handlers.load(self.hero, "skeleton", "default", namespace="hero_game")
        self.assertEqual(self.handlers.load(self.hero, "skeleton", "default"), ["spine1_00_M_JNT", "spine2_00_M_JNT"])

    def test_a_skeleton_needs_joints_and_a_second_save_keeps_a_version(self):
        with self.assertRaisesRegex(ValueError, "Pass joints"):
            self.handlers.save(self.hero, "skeleton", "default")
        joints = self.make_skeleton()
        path = self.handlers.save(self.hero, "skeleton", "default", joints=joints)
        self.handlers.save(self.hero, "skeleton", "default", joints=joints)
        from bmaya.core.asset import versions
        self.assertEqual(len(versions.list_versions(path, self.root)), 1)

    def test_a_rig_scene_saves_and_imports_into_a_namespace(self):
        cmds = self.cmds
        self.make_skeleton()
        path = self.handlers.save(self.hero, "rig", "game")
        self.assertEqual(path, os.path.join(self.hero.folder, "rigs", "game", "hero_game_rig.ma"))
        self.assertEqual(os.path.normpath(cmds.file(query=True, sceneName=True)), path, "saving a rig saves the scene")

        cmds.file(new=True, force=True)
        nodes = self.handlers.load(self.hero, "rig", "game")
        self.assertIn("|hero:skel:spine1_00_M_JNT", nodes)
        # A second load merges into the namespace instead of making hero1.
        self.handlers.load(self.hero, "rig", "game")
        self.assertFalse(cmds.namespace(exists=":hero1"))
        self.handlers.load(self.hero, "rig", "game", namespace="hero2")
        self.assertTrue(cmds.objExists("hero2:skel:spine1_00_M_JNT"))

    def test_a_model_saves_as_meshes_only_and_imports_into_a_namespace(self):
        cmds = self.cmds
        joints = self.make_skeleton()
        box = cmds.polyCube(name="box_geo", height=2, constructionHistory=False)[0]
        cmds.skinCluster(*joints, box, toSelectedBones=True)
        scene = cmds.file(query=True, sceneName=True)
        path = self.handlers.save(self.hero, "model", "default")       # no meshes named: every mesh in the scene
        self.assertEqual(path, os.path.join(self.hero.folder, "looks", "default", "model", "hero_default_model.ma"))
        self.assertEqual(cmds.file(query=True, sceneName=True), scene, "saving a model does not save the scene")
        self.assertEqual(len(cmds.ls(type="skinCluster")), 1, "the scene keeps its skinning")

        cmds.file(new=True, force=True)
        nodes = self.handlers.load(self.hero, "model", "default", namespace="hero_game")
        self.assertEqual(sorted(cmds.ls(nodes, long=True)), ["|hero_game:box_geo", "|hero_game:box_geo|hero_game:box_geoShape"])
        self.assertEqual((cmds.ls(type="joint"), cmds.ls(type="skinCluster")), ([], []))

    def test_a_template_is_written_with_the_rigs_name(self):
        source = os.path.join(self.root, "shared_template.json")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(TEMPLATE, rigName="human"), indent=2))
        path = self.handlers.save(self.hero, "template", "body", source=source)
        self.assertEqual(path, os.path.join(self.hero.folder, "rigs", "body", "template.json"))
        self.assertEqual(self.read_json(path), dict(TEMPLATE, rigName="body"))
        with open(path, encoding="utf-8") as handle:
            self.assertIn('\n  "rigVersion"', handle.read(), "the copy keeps the source's indent")
        self.assertEqual(self.handlers.load(self.hero, "template", "body"), path)
        with self.assertRaisesRegex(ValueError, "Pass source"):
            self.handlers.save(self.hero, "template", "other")

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

    def test_a_clip_saves_as_fbx_in_its_own_exports_folder_and_loads_back(self):
        path = self.handlers.save(self.hero, "exports", "default", name="walk", joint_clip=self.write_joint_clip())
        self.assertEqual(path, os.path.join(self.hero.folder, "skeletons", "default", "exports"))
        fbx = os.path.join(path, "walk", "walk.fbx")
        self.assertTrue(os.path.isfile(fbx))

        clip = self.handlers.load(self.hero, "exports", "default", name="walk")
        self.assertEqual((clip.name, clip.fbx, clip.sidecar), ("walk", fbx, None))
        data = self.read_json(clip.joint_clip)
        self.assertEqual(len(data["poses"]), 2)
        self.assertEqual([joint["path"] for joint in data["joints"]], ["hips", "hips/tip"])
        self.assertAlmostEqual(data["poses"][1][0]["translate"][1], 101, places=4)

    def test_a_clip_can_be_captured_from_a_rig(self):
        cmds = self.cmds
        rig_root = self.build_rig()
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateY", time=1, value=0)
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateY", time=3, value=4)
        fbx = self.assethandlers.save_anim_clip(self.hero, "game", "rise", rig_root=rig_root, start_frame=1, end_frame=3)
        self.assertEqual(fbx, os.path.join(self.hero.path("exports", "default"), "rise", "rise.fbx"))

        data = self.read_json(self.handlers.load(self.hero, "exports", "default", name="rise").joint_clip)
        self.assertEqual(len(data["poses"]), 3)
        self.assertEqual({joint["path"] for joint in data["joints"]}, {"spine1_00_M_JNT", "spine1_00_M_JNT/spine2_00_M_JNT"})
        self.assertEqual([name for name in os.listdir(tempfile.gettempdir()) if name.endswith(".jointclip.json")], [])

    def test_a_clip_captured_from_a_rig_carries_its_control_anim_and_restores_with_it(self):
        cmds = self.cmds
        rig_root = self.build_rig()
        cmds.currentUnit(time="film")
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateY", time=1, value=0)
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateY", time=3, value=4)
        fbx = self.assethandlers.save_anim_clip(self.hero, "game", "rise", rig_root=rig_root, start_frame=1, end_frame=3)
        control_anim = os.path.join(os.path.dirname(fbx), "rise.controlanim.json")
        self.assertTrue(os.path.isfile(control_anim))
        self.assertEqual(sorted(os.listdir(os.path.dirname(fbx))), ["rise.animproperties.json", "rise.controlanim.json", "rise.fbx"])

        clip = self.handlers.load(self.hero, "exports", "default", name="rise")
        self.assertEqual(clip.sidecar, control_anim)
        cmds.cutKey("hero:spine1_00_M_CTRL", attribute="translateY", clear=True)
        cmds.setAttr("hero:spine1_00_M_CTRL.translateY", 0)
        cmds.animateRigFromJointClip(rig_root, jointClip=clip.joint_clip.replace("\\", "/"), sidecar=clip.sidecar.replace("\\", "/"))
        self.assertAlmostEqual(cmds.getAttr("hero:spine1_00_M_CTRL.translateY", time=3), 4.0, places=3)

    def test_a_clip_without_a_control_anim_has_no_sidecar(self):
        self.handlers.save(self.hero, "exports", "default", name="walk", joint_clip=self.write_joint_clip())
        self.assertIsNone(self.handlers.load(self.hero, "exports", "default", name="walk").sidecar)

    def test_an_export_gets_default_properties_and_a_re_export_keeps_edited_ones(self):
        from bmaya.core.asset import animproperties
        joint_clip = self.write_joint_clip()
        self.handlers.save(self.hero, "exports", "default", name="walk", joint_clip=joint_clip)
        self.assertEqual(self.handlers.load(self.hero, "exports", "default", name="walk").properties, animproperties.AnimProperties())

        edited = animproperties.AnimProperties(loop=True, events=(animproperties.AnimEvent("footstep", 12.0),))
        self.handlers.save(self.hero, "exports", "default", name="walk", joint_clip=joint_clip, properties=edited)
        self.assertEqual(self.handlers.load(self.hero, "exports", "default", name="walk").properties, edited)

        self.handlers.save(self.hero, "exports", "default", name="walk", joint_clip=joint_clip)
        self.assertEqual(self.handlers.load(self.hero, "exports", "default", name="walk").properties, edited)

    def test_a_clip_without_a_properties_file_has_none_and_a_bad_one_is_refused_on_load(self):
        from bmaya.core.asset import animproperties
        self.handlers.save(self.hero, "exports", "default", name="walk", joint_clip=self.write_joint_clip())
        path = animproperties.get_path(os.path.join(self.hero.path("exports", "default"), "walk", "walk.fbx"))
        os.remove(path)
        self.assertIsNone(self.handlers.load(self.hero, "exports", "default", name="walk").properties)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('{"formatVersion": 1}')
        with self.assertRaises(animproperties.AnimPropertiesError):
            self.handlers.load(self.hero, "exports", "default", name="walk")

    # ---- control data, sources and the skeleton export ---------------------------------------

    def test_a_control_pose_saves_to_controlposes_and_loads_onto_the_rig(self):
        cmds = self.cmds
        rig_root = self.build_rig()
        cmds.setAttr("hero:spine1_00_M_CTRL.translateY", 3)
        path = self.assethandlers.save_control_file(
            self.assethandlers.ControlPoseHandler(), self.hero, "game", "controlposes", "idle", scope=[rig_root])
        self.assertEqual(path, os.path.join(self.hero.folder, "rigs", "game", "controlposes", "idle.controlpose.json"))
        self.assertEqual(self.assethandlers.ControlPoseHandler.names(self.hero.path("controlposes", "game")), ["idle"])

        cmds.setAttr("hero:spine1_00_M_CTRL.translateY", 0)
        changed = self.handlers.load(self.hero, "controlposes", "game", name="idle", scope=[rig_root])
        self.assertIn("hero:spine1_00_M_CTRL", [c.lstrip(":") for c in changed])
        self.assertEqual(cmds.getAttr("hero:spine1_00_M_CTRL.translateY"), 3)

    def test_a_control_animation_saves_to_controlanims_and_loads_with_an_offset(self):
        cmds = self.cmds
        rig_root = self.build_rig()
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateY", time=1, value=0)
        cmds.setKeyframe("hero:spine1_00_M_CTRL.translateY", time=3, value=4)
        path = self.assethandlers.save_control_file(
            self.assethandlers.ControlAnimHandler(), self.hero, "game", "controlanims", "rise", scope=[rig_root], start_frame=1, end_frame=3)
        self.assertEqual(path, os.path.join(self.hero.path("controlanims", "game"), "rise.controlanim.json"))

        cmds.cutKey("hero:spine1_00_M_CTRL", attribute="translateY", clear=True)
        self.handlers.load(self.hero, "controlanims", "game", name="rise", scope=[rig_root], offset=10)
        self.assertEqual(cmds.keyframe("hero:spine1_00_M_CTRL.translateY", query=True, timeChange=True), [11, 13])
        self.assertEqual(cmds.keyframe("hero:spine1_00_M_CTRL.translateY", query=True, valueChange=True), [0, 4])

    def test_control_data_arguments_are_checked_before_anything_is_written(self):
        rig_root = self.build_rig()
        handler = self.assethandlers.ControlPoseHandler()
        with self.assertRaisesRegex(ValueError, "not a pose name"):
            self.assethandlers.save_control_file(handler, self.hero, "game", "controlposes", "a/b", scope=[rig_root])
        with self.assertRaisesRegex(ValueError, "scope"):
            handler.save(self.hero, self.hero.path("controlposes", "game"), name="idle")
        with self.assertRaisesRegex(ValueError, "start_frame"):
            self.assethandlers.ControlAnimHandler().save(self.hero, self.hero.path("controlanims", "game"), name="x", scope=[rig_root])
        self.assertFalse(os.path.exists(os.path.join(self.hero.path("controlposes", "game"), "idle.controlpose.json")))

    def test_loading_control_data_that_is_not_there_names_the_files_that_are(self):
        rig_root = self.build_rig()
        self.assethandlers.save_control_file(
            self.assethandlers.ControlPoseHandler(), self.hero, "game", "controlposes", "idle", scope=[rig_root])
        with self.assertRaisesRegex(FileNotFoundError, "idle"):
            self.handlers.load(self.hero, "controlposes", "game", name="walk", scope=[rig_root])

    def test_the_new_file_types_are_in_a_new_projects_project_json(self):
        for file_type in ("controlposes", "controlanims", "exports", "sources"):
            self.assertTrue(self.hero.project.file_type(file_type).folder)

    def test_a_source_loads_like_a_clip_and_is_never_saved(self):
        sources = self.hero.path("sources")
        os.makedirs(sources)
        self.assethandlers.AnimClipHandler().save(
            None, sources, name="take", joint_clip=self.write_joint_clip(), own_folder=False)
        clip = self.handlers.load(self.hero, "sources", name="take")
        self.assertEqual(clip.fbx, os.path.join(sources, "take.fbx"))
        self.assertEqual(len(self.read_json(clip.joint_clip)["poses"]), 2)
        with self.assertRaises(NotImplementedError):
            self.handlers.save(self.hero, "sources", name="take", joint_clip=self.write_joint_clip())

    def test_the_skeleton_export_is_an_fbx_and_a_bone_map_in_the_exports_folder_and_is_not_a_clip(self):
        rig_root = self.build_rig()
        fbx, bone_map = self.assethandlers.save_skeleton_export(self.hero, "game", rig_root)
        exports = os.path.join(self.hero.folder, "skeletons", "default", "exports")
        self.assertEqual(fbx, os.path.join(exports, "hero_default_skeleton.fbx"))
        self.assertEqual(bone_map, os.path.join(exports, "hero_default_skeleton.bonemap.json"))
        data = self.read_json(bone_map)
        self.assertEqual((data["assetId"], data["skeletonId"]), (HERO, "default"))
        self.assertEqual(sorted(data["joints"]), ["spine1_00_M_JNT", "spine2_00_M_JNT"])
        self.assertEqual(self.assethandlers.AnimClipHandler.names(self.hero.path("exports", "default")), [])

        from bmaya.core.asset import versions
        self.assethandlers.save_skeleton_export(self.hero, "game", rig_root)
        self.assertEqual(len(versions.list_versions(fbx, self.root)), 1, "a second export keeps the first as a version")
        self.assertEqual(len(versions.list_versions(bone_map, self.root)), 1)

    def test_a_file_chosen_in_a_dialog_is_written_where_it_was_chosen(self):
        fbx = self.assethandlers.AnimClipHandler().save(
            None, self.root, name="chosen", joint_clip=self.write_joint_clip(), own_folder=False)
        self.assertEqual(fbx, os.path.join(self.root, "chosen.fbx"))
        self.assertNotIn("chosen.animproperties.json", os.listdir(self.root), "a dialog's file gets no properties")
        clip = self.assethandlers.AnimClipHandler().load(None, self.root, name="chosen")
        self.assertEqual(clip.fbx, fbx)

    def test_a_bone_map_beside_an_fbx_marks_its_joints_when_it_loads(self):
        from rigmodules import bonemap
        unmarked = self.write_joint_clip()
        with open(unmarked, encoding="utf-8") as handle:
            clip = json.load(handle)
        for joint in clip["joints"]:
            joint["markup"] = ""
        with open(unmarked, "w", encoding="utf-8") as handle:
            json.dump(clip, handle)
        fbx = self.assethandlers.AnimClipHandler().save(None, self.root, name="mocap", joint_clip=unmarked, own_folder=False)
        markup = {"markupVersion": 1, "side": "Center", "usage": "hips", "export": True, "skin": True}
        bonemap.write_bone_map(fbx[:-4] + ".bonemap.json", "shooter\\main\\characters\\hero", "shooter\\main\\skeletons\\human",
                               {"hips": json.dumps(markup)})
        data = self.read_json(self.assethandlers.AnimClipHandler().load(None, self.root, name="mocap").joint_clip)
        self.assertEqual(json.loads(data["joints"][0]["markup"]), markup)
        self.assertEqual(data["joints"][1]["markup"], "")

    def test_save_anim_clip_versions_only_that_clips_fbx(self):
        from bmaya.core.asset import versions
        module = self.assethandlers
        source = self.write_joint_clip()
        module.save_anim_clip(self.hero, "game", "walk", joint_clip=source)
        module.save_anim_clip(self.hero, "game", "run", joint_clip=source)
        fbx = os.path.join(self.hero.path("exports", "default"), "walk", "walk.fbx")
        self.assertEqual(versions.list_versions(fbx, self.root), [], "a first save has nothing to version")

        module.save_anim_clip(self.hero, "game", "walk", joint_clip=self.write_joint_clip(poses=3))
        self.assertEqual(len(versions.list_versions(fbx, self.root)), 1)
        self.assertEqual(versions.list_versions(os.path.join(self.hero.path("exports", "default"), "run", "run.fbx"), self.root), [])
        self.assertEqual(len(self.read_json(self.handlers.load(self.hero, "exports", "default", name="walk").joint_clip)["poses"]), 3)
        self.assertEqual(module.AnimClipHandler.names(self.hero.path("exports", "default")), ["run", "walk"])

    def test_clip_arguments_are_checked_before_anything_is_written(self):
        source = self.write_joint_clip()
        for kwargs in (
            {"name": None, "joint_clip": source},
            {"name": "../walk", "joint_clip": source},
            {"name": "walk"},
            {"name": "walk", "joint_clip": source, "rig_root": "hero:rigRootModule1"},
            {"name": "walk", "rig_root": "hero:rigRootModule1"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, FileNotFoundError)):
                self.handlers.save(self.hero, "exports", "default", **kwargs)
        self.assertFalse(os.path.exists(os.path.join(self.hero.path("exports", "default"), "walk")))

    def test_loading_a_clip_that_is_not_there_names_the_clips_that_are(self):
        self.handlers.save(self.hero, "exports", "default", name="walk", joint_clip=self.write_joint_clip())
        with self.assertRaisesRegex(FileNotFoundError, "no clip 'run'.*walk"):
            self.handlers.load(self.hero, "exports", "default", name="run")


if __name__ == "__main__":
    unittest.main()
