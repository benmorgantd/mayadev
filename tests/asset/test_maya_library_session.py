"""bmaya.maya.librarybrowser.LibrarySession on built rigs, in mayapy: the listing that follows the active rig, search,
scope, apply, save and the file commands (RigModules D51, design/library-browser.md).

Needs RIGMODULES_PLUGIN, the path of a RigModules.mll (copy it first if a Maya session has the build loaded),
and the rigmodules package on the path (RigModules.mod puts it there). Skipped without them.
Run with tests/asset/run.bat.
"""

import getpass
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
HERO = "shooter\\hero"
VILLAIN = "shooter\\villain"
BIPED = "shooter\\biped"
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "LibraryTest",
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


class LibraryBase(unittest.TestCase):

    def setUp(self):
        from maya import cmds
        import bmaya.core.asset
        import bmaya.core.asset.library
        import bmaya.maya.activerig
        import bmaya.maya.librarybrowser
        import rigmodules.query

        self.cmds = cmds
        self.asset = bmaya.core.asset
        self.library = bmaya.core.asset.library
        self.activerig = bmaya.maya.activerig
        self.browser = bmaya.maya.librarybrowser
        self.query = rigmodules.query
        temp = tempfile.mkdtemp(prefix="bmaya_library_session_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.temp = temp
        self.root = os.path.join(temp, "projects")
        environ = {"RIGGING_PROJECT_DIR": self.root, "BMAYA_VERSIONS_DIR": os.path.join(temp, "local_versions")}
        patcher = mock.patch.dict(os.environ, environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        login = mock.patch.object(self.library, "login", return_value="tester")
        login.start()
        self.addCleanup(login.stop)

        self.asset.Project.create(os.path.join(self.root, "shooter"))
        # The library is a rig's (RigModules D54). The biped holds the rig "game", and the hero's rig "game" is a copy
        # of it, so the hero's rig lists the biped rig's files as its Shared source.
        default = self.asset.SkeletonRef("default")
        self.biped = self.asset.Asset.create(BIPED, "Skeleton")
        self.biped.add_rig("game", default)
        self.hero_asset = self.asset.Asset.create(HERO, "Character")
        self.hero_asset.add_rig("game", default, source=self.asset.RigRef("game", asset=BIPED))
        self.template = os.path.join(temp, "template.json").replace("\\", "/")
        with open(self.template, "w", encoding="utf-8") as handle:
            json.dump(TEMPLATE, handle)
        cmds.file(new=True, force=True)
        cmds.undoInfo(state=True, infinity=True)

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

    def user_folder(self, kind, asset=None):
        return self.library.user_source(asset or self.hero_asset, "game").folders[kind]

    def entry(self, session, name):
        return next(entry for entry in session.entries if entry.name == name)

    def left_right(self, root):
        return (self.cmds.getRigControls(root, side="Left")[0], self.cmds.getRigControls(root, side="Right")[0])


class Looks(LibraryBase):
    """The looks the session offers for the active rig (RigModules D54 phase 5). Applying one is assettools.apply_look,
    tested with real files in test_maya_asset_tools.py."""

    def test_the_rig_is_offered_the_looks_its_skeleton_can_wear(self):
        self.hero_asset.add_look("default", [self.asset.SkeletonRef("default")])
        self.hero_asset.add_look("head", [self.asset.SkeletonRef("face")])
        self.hero_asset.add_look("winter", [self.asset.SkeletonRef("default")])
        root = self.build(HERO)
        session = self.browser.LibrarySession()
        self.assertEqual(session.looks(), ["default", "winter"])
        self.assertIsNone(session.worn_look())
        self.assertEqual(self.query.get_rig_info(root).look, None)

    def test_a_look_that_is_not_synced_is_offered_with_a_not_local_flag(self):
        self.hero_asset.add_look("default", [self.asset.SkeletonRef("default")])
        self.hero_asset.add_look("head", [self.asset.SkeletonRef("face")])
        self.build(HERO)

        class Depot(self.asset.sourcecontrol.SourceControl):
            def list_folders(self, path):
                return ["default", "head", "winter"]

        self.asset.sourcecontrol.set_current(Depot())
        self.addCleanup(self.asset.sourcecontrol.set_current, self.asset.sourcecontrol.SourceControl())
        session = self.browser.LibrarySession()
        self.assertEqual([(entry.name, entry.local) for entry in session.look_entries()],
                         [("default", True), ("winter", False)], "head is local and fits another skeleton")
        self.assertEqual(session.looks(), ["default", "winter"])

    def test_apply_look_goes_through_assettools_and_refuses_a_look_the_rig_cannot_wear(self):
        self.hero_asset.add_look("default", [self.asset.SkeletonRef("default")])
        self.hero_asset.add_look("head", [self.asset.SkeletonRef("face")])
        root = self.build(HERO)
        session = self.browser.LibrarySession()
        with mock.patch.object(self.browser.bmaya.maya.assettools, "apply_look", return_value="hero:lookRoot") as apply_look:
            self.assertEqual(session.apply_look("default"), "hero:lookRoot")
            apply_look.assert_called_once_with(root, "default")
            with self.assertRaisesRegex(RuntimeError, "no look 'head' that the rig 'game' can wear: default"):
                session.apply_look("head")
            apply_look.assert_called_once()

    def test_looks_need_an_active_rig(self):
        session = self.browser.LibrarySession()
        with self.assertRaisesRegex(RuntimeError, "no active rig"):
            session.looks()
        with self.assertRaisesRegex(RuntimeError, "no active rig"):
            session.apply_look("default")


class Listing(LibraryBase):

    def test_with_no_rig_the_state_is_empty_with_a_reason_and_commands_say_so(self):
        session = self.browser.LibrarySession()
        self.assertEqual((session.entries, session.masks, session.sources, session.asset_id, session.rig_name), ([], [], [], None, None))
        self.assertEqual(session.reason, "There is no active rig.")
        with self.assertRaisesRegex(RuntimeError, "no active rig"):
            session.save("x")
        with self.assertRaisesRegex(RuntimeError, "no active rig"):
            session.scope_controls()

    def test_the_session_lists_the_user_library_of_the_active_rigs_asset(self):
        root = self.build(HERO)
        session = self.browser.LibrarySession()
        self.assertEqual((session.reason, session.asset_id, session.rig_name, session.rig_root), ("", HERO, "game", root))
        self.assertEqual([source.key for source in session.sources], ["approved", "shared", "user"])
        self.assertEqual(session.entries, [])

        left, _right = self.left_right(root)
        self.cmds.setAttr(left + ".rotateY", 20)
        saved = session.save("wave", tags=("arm", "friendly"), description="Raised hand")
        self.assertEqual(session.entries, [saved])
        self.assertEqual(session.selected, saved)
        self.assertEqual(saved.path, os.path.join(self.user_folder(self.library.POSE), "wave.controlpose.json"))
        self.assertEqual((saved.tags, saved.description, saved.source), (["arm", "friendly"], "Raised hand", "user"))
        self.assertEqual((saved.meta("assetId"), saved.meta("author"), saved.meta("template"), saved.meta("skeleton")),
                         (HERO, "tester", "game", "default"))
        self.assertEqual((saved.info.control_count, saved.info.unmatched_controls),
                         (len(self.cmds.getRigControls(root)), ()))

    def test_every_source_is_listed_with_its_own_files(self):
        root = self.build(HERO)
        os.makedirs(self.hero_asset.path("controlposes", "game"))
        self.cmds.saveRigPose(root, file=os.path.join(self.hero_asset.path("controlposes", "game"), "approved_pose.controlpose.json").replace("\\", "/"))
        os.makedirs(self.biped.path("controlposes", "game"))
        self.cmds.saveRigPose(root, file=os.path.join(self.biped.path("controlposes", "game"), "t_pose.json").replace("\\", "/"))
        session = self.browser.LibrarySession()
        session.save("mine")
        self.assertEqual([(entry.name, entry.source) for entry in session.entries],
                         [("approved_pose", "approved"), ("mine", "user"), ("t_pose", "shared")])
        session.set_source_enabled("shared", False)
        self.assertEqual([entry.name for entry in session.entries], ["approved_pose", "mine"])

    def test_poses_and_animations_are_two_lists(self):
        root = self.build(HERO)
        left, _right = self.left_right(root)
        self.cmds.setKeyframe(left + ".rotateY", time=1, value=5)
        session = self.browser.LibrarySession()
        session.save("a_pose")
        session.set_kind("animation")
        self.assertEqual(session.entries, [])
        session.save("a_move", start_frame=1, end_frame=4)
        self.assertEqual([entry.name for entry in session.entries], ["a_move"])
        session.set_kind("pose")
        self.assertEqual([entry.name for entry in session.entries], ["a_pose"])
        with self.assertRaises(ValueError):
            session.set_kind("clip")

    def test_the_query_filters_and_a_selection_the_filter_hides_is_dropped(self):
        self.build(HERO)
        session = self.browser.LibrarySession()
        session.save("fist", tags=("hands",))
        session.save("idle", tags=("body",))
        self.assertEqual([entry.name for entry in session.entries], ["fist", "idle"])
        session.set_query("tag:body")
        self.assertEqual([entry.name for entry in session.entries], ["idle"])
        self.assertEqual(session.selected.name, "idle", "the last save is selected and still shown")
        session.set_query("tag:hands")
        self.assertEqual([entry.name for entry in session.entries], ["fist"])
        self.assertIsNone(session.selected, "idle is hidden now, so it is not selected")
        session.set_query("")
        self.assertEqual(len(session.entries), 2)

    def test_changed_emits_for_each_change_and_a_refresh_keeps_the_selection(self):
        self.build(HERO)
        session = self.browser.LibrarySession()
        calls = []
        session.changed.connect(lambda: calls.append(1))
        session.save("fist")
        before = len(calls)
        session.select(session.entries[0])
        session.set_query("fi")
        session.refresh()
        self.assertGreater(len(calls), before)
        self.assertEqual(session.selected.name, "fist")

    def test_only_files_that_changed_are_read_again(self):
        self.build(HERO)
        reads = []

        def counting(paths, context):
            reads.append([os.path.basename(path) for path in paths])
            return self.browser.read_file_infos(paths, context)

        session = self.browser.LibrarySession(index=self.library.Index(counting))
        session.save("a")
        session.save("b")
        session.refresh()
        self.assertEqual(reads, [["a.controlpose.json"], ["b.controlpose.json"]], "a save reads its own file, a refresh none")

    def test_the_listing_follows_the_active_rig(self):
        self.asset.Asset.create(VILLAIN, "Character")
        hero = self.build(HERO)
        villain = self.build(VILLAIN)
        self.cmds.select(self.left_right(hero)[0], replace=True)
        session = self.browser.LibrarySession()
        self.assertEqual(session.asset_id, HERO)
        session.save("hero_pose")
        self.cmds.select(self.left_right(villain)[0], replace=True)
        self.assertEqual((session.asset_id, session.entries), (VILLAIN, []))
        self.cmds.select(self.left_right(hero)[0], replace=True)
        self.assertEqual([entry.name for entry in session.entries], ["hero_pose"])

    def test_a_closed_session_stops_following_the_tracker(self):
        self.build(HERO)
        session = self.browser.LibrarySession()
        calls = []
        session.changed.connect(lambda: calls.append(1))
        session.close()
        self.activerig.ActiveRigTracker().refresh()
        self.assertEqual(calls, [])

    def test_an_asset_that_is_not_on_disk_still_has_a_user_library(self):
        self.build("shooter\\ghost")
        session = self.browser.LibrarySession()
        self.assertEqual([source.key for source in session.sources], ["user"])
        saved = session.save("x")
        self.assertIn(os.path.join("user", "tester", "animlibrary", "shooter", "ghost", "game", "controlposes"), saved.path)

    def test_without_a_projects_root_the_listing_is_empty_with_the_reason(self):
        self.build(HERO)
        with mock.patch.dict(os.environ):
            del os.environ["RIGGING_PROJECT_DIR"]
            session = self.browser.LibrarySession()
        self.assertEqual(session.entries, [])
        self.assertIn("RIGGING_PROJECT_DIR", session.reason)

    def test_a_broken_file_is_listed_with_its_error_and_cannot_be_applied(self):
        self.build(HERO)
        folder = self.user_folder(self.library.POSE)
        os.makedirs(folder)
        with open(os.path.join(folder, "broken.controlpose.json"), "w", encoding="utf-8") as handle:
            handle.write("not json")
        session = self.browser.LibrarySession()
        broken = self.entry(session, "broken")
        self.assertTrue(broken.info.error)
        self.assertEqual(session.details(broken), [broken.info.error])
        session.select(broken)
        with self.assertRaises(RuntimeError):
            session.apply()


class Applying(LibraryBase):

    def setUp(self):
        super().setUp()
        self.root_node = self.build(HERO)
        self.left, self.right = self.left_right(self.root_node)
        self.session = self.browser.LibrarySession()

    def rotate_y(self, control):
        return self.cmds.getAttr(control + ".rotateY")

    def test_apply_loads_a_pose_and_one_undo_restores_the_scene(self):
        self.cmds.setAttr(self.left + ".rotateY", 20)
        self.session.save("wave")
        self.cmds.setAttr(self.left + ".rotateY", 3)
        changed = self.session.apply()
        self.assertEqual(self.rotate_y(self.left), 20)
        self.assertIn(self.left, [name.split("|")[-1] for name in changed])
        self.cmds.undo()
        self.assertAlmostEqual(self.rotate_y(self.left), 3)

    def test_apply_needs_a_selected_entry(self):
        with self.assertRaisesRegex(RuntimeError, "Select a pose"):
            self.session.apply()

    def test_mirror_puts_the_files_left_on_the_right_before_it_is_written(self):
        self.cmds.setAttr(self.left + ".rotateY", 20)
        self.session.save("wave")
        self.cmds.setAttr(self.left + ".rotateY", 7)
        self.session.apply(mirror=True)
        self.assertEqual((self.rotate_y(self.right), self.rotate_y(self.left)), (20, 0))

    def test_an_animation_lands_on_its_own_start_and_start_at_moves_it(self):
        cmds = self.cmds
        cmds.setKeyframe(self.left + ".rotateY", time=5, value=0)
        cmds.setKeyframe(self.left + ".rotateY", time=10, value=40)
        self.session.set_kind("animation")
        self.session.save("raise", start_frame=5, end_frame=10)

        def times():
            return cmds.keyframe(self.left + ".rotateY", query=True, timeChange=True)

        cmds.cutKey(self.left, attribute="rotateY", clear=True)
        self.session.apply()
        self.assertEqual(times(), [5, 10])
        cmds.undo()
        self.assertFalse(cmds.keyframe(self.left + ".rotateY", query=True, keyframeCount=True), "one undo removes every key")
        self.session.apply(start_frame=20)
        self.assertEqual(times(), [20, 25])
        self.assertEqual(cmds.keyframe(self.left + ".rotateY", query=True, valueChange=True), [0, 40])

    def test_an_animation_of_another_frame_rate_is_explained_before_it_is_applied_and_refused(self):
        cmds = self.cmds
        cmds.setKeyframe(self.left + ".rotateY", time=1, value=1)
        self.session.set_kind("animation")
        entry = self.session.save("held", start_frame=1, end_frame=2)
        self.assertEqual(len(self.session.details(entry)), 1)
        cmds.currentUnit(time="ntsc")
        lines = self.session.details(entry)
        self.assertRegex(lines[-1], r"24 fps and the scene is 30 fps")
        with self.assertRaises(RuntimeError):
            self.session.apply()

    def test_details_summarize_the_file_and_name_the_controls_the_rig_lacks(self):
        self.cmds.setAttr(self.left + ".rotateY", 2)
        saved = self.session.save("a")
        count = len(self.cmds.getRigControls(self.root_node))
        self.assertEqual(self.session.details(saved)[0], f"{count} controls, {saved.info.channel_count} channels, 0 unmatched.")
        self.assertGreater(saved.info.channel_count, count)

    def test_selection_is_the_default_scope_when_something_is_selected(self):
        self.cmds.setAttr(self.left + ".rotateY", 20)
        self.cmds.setAttr(self.right + ".rotateY", 20)
        self.session.save("both")
        for control in (self.left, self.right):
            self.cmds.setAttr(control + ".rotateY", 0)
        self.assertEqual(self.session.scope_controls(), [self.root_node])
        self.cmds.select(self.left, replace=True)
        self.assertEqual(self.session.scope_controls(), self.cmds.ls(self.left, long=True))
        self.session.select(self.entry(self.session, "both"))
        self.session.apply()
        self.assertEqual((self.rotate_y(self.left), self.rotate_y(self.right)), (20, 0))

    def test_the_selection_scope_needs_a_selection(self):
        self.session.set_scope("selection")
        with self.assertRaisesRegex(RuntimeError, "Select controls"):
            self.session.scope_controls()

    def test_saving_a_selection_stores_only_those_controls(self):
        self.cmds.select(self.left, replace=True)
        saved = self.session.save("left_only")
        self.assertEqual(saved.info.control_count, 1)

    def test_the_rig_gives_masks_by_module_type_side_and_module(self):
        names = [mask.name for mask in self.session.masks]
        for expected in ("FkChain", "Left", "Right", "Center", "spine"):
            self.assertIn(expected, names)
        self.assertTrue(all(mask.source == "rig" for mask in self.session.masks))
        spine = next(mask for mask in self.session.masks if mask.name == "spine")
        self.assertEqual({(item.side, item.usage) for item in spine.items}, {("Center", "spine1"), ("Center", "spine2")})

    def test_a_mask_limits_apply_to_its_controls_and_the_selection_narrows_it(self):
        for control in (self.left, self.right):
            self.cmds.setAttr(control + ".rotateY", 20)
        self.session.save("both")
        for control in (self.left, self.right):
            self.cmds.setAttr(control + ".rotateY", 0)
        self.session.set_scope("Left")
        self.session.select(self.entry(self.session, "both"))
        self.session.apply()
        self.assertEqual((self.rotate_y(self.left), self.rotate_y(self.right)), (20, 0))

        self.cmds.select(self.right, replace=True)
        with self.assertRaisesRegex(RuntimeError, "'Left' has no controls in the selection"):
            self.session.apply()
        self.cmds.select(self.left, replace=True)
        self.assertEqual(len(self.session.scope_controls()), 1)

    def test_an_unknown_scope_is_refused(self):
        with self.assertRaisesRegex(ValueError, "not a scope"):
            self.session.set_scope("Elbows")
        self.session.set_scope("Left")
        self.session.set_scope(None)

    def test_a_saved_mask_is_listed_after_the_rigs_and_can_be_a_scope(self):
        self.session.save_mask(self.library.Mask("Hand pair", (self.library.MaskItem(usage="arm"),)))
        self.assertEqual(self.session.masks[-1].name, "Hand pair")
        self.assertEqual(self.session.masks[-1].source, "user")
        self.session.set_scope("Hand pair")
        self.assertEqual(len(self.session.scope_controls()), 2)
        with self.assertRaisesRegex(self.library.LibraryError, "mask the rig gives"):
            self.session.save_mask(self.library.Mask("left", (self.library.MaskItem(side="Left"),)))
        self.session.delete_mask("Hand pair")
        self.assertIsNone(self.session.scope)
        self.assertNotIn("Hand pair", [mask.name for mask in self.session.masks])


class Files(LibraryBase):

    def setUp(self):
        super().setUp()
        self.root_node = self.build(HERO)
        self.session = self.browser.LibrarySession()

    def put_approved(self, name):
        folder = self.hero_asset.path("controlposes", "game")
        os.makedirs(folder, exist_ok=True)
        self.cmds.saveRigPose(self.root_node, file=os.path.join(folder, name + ".controlpose.json").replace("\\", "/"))
        self.session.refresh()
        return self.entry(self.session, name)

    def test_save_offers_a_free_name_and_refuses_a_taken_one_unless_it_replaces(self):
        self.assertEqual(self.session.suggest_name(), "pose_001")
        self.session.save("pose_001")
        self.assertEqual(self.session.suggest_name(), "pose_002")
        with self.assertRaisesRegex(self.library.LibraryError, "already have a pose called 'pose_001'"):
            self.session.save("pose_001")
        self.session.save("pose_001", replace=True)
        self.assertEqual(len(self.session.entries), 1)
        self.assertEqual(len(self.asset.versions.list_versions(self.session.entries[0].path, self.root)), 1)
        with self.assertRaises(self.library.LibraryError):
            self.session.save("a/b")

    def test_set_meta_edits_tags_and_description_and_keeps_a_version(self):
        saved = self.session.save("fist", tags=("old",))
        self.session.set_meta(saved, tags=["hands", "fist"], description="Clenched")
        again = self.entry(self.session, "fist")
        self.assertEqual((again.tags, again.description), (["hands", "fist"], "Clenched"))
        self.assertEqual(again.meta("author"), "tester", "the rest of the meta is kept")
        self.assertEqual(self.session.selected, again)
        self.assertEqual(len(self.asset.versions.list_versions(again.path, self.root)), 1)
        self.session.set_meta(again, tags=[])
        self.assertEqual(self.entry(self.session, "fist").tags, [])
        self.assertEqual(self.entry(self.session, "fist").description, "Clenched")

    def test_rename_and_delete_work_in_the_users_library_only(self):
        saved = self.session.save("fist")
        renamed = self.session.rename(saved, "clench")
        self.assertEqual([entry.name for entry in self.session.entries], ["clench"])
        self.assertEqual(self.session.selected, renamed)
        self.session.delete(renamed)
        self.assertEqual((self.session.entries, self.session.selected), ([], None))

        approved = self.put_approved("signed_off")
        for call in (lambda: self.session.rename(approved, "x"), lambda: self.session.delete(approved),
                     lambda: self.session.set_meta(approved, tags=["x"])):
            with self.assertRaisesRegex(self.library.LibraryError, "approved library, which can't be changed"):
                call()
        self.assertTrue(os.path.isfile(approved.path))

    def test_an_approved_entry_applies_and_copies_to_the_users_own_library(self):
        left, _right = self.left_right(self.root_node)
        self.cmds.setAttr(left + ".rotateY", 11)
        approved = self.put_approved("signed_off")
        self.cmds.setAttr(left + ".rotateY", 0)
        self.session.select(approved)
        self.session.apply()
        self.assertEqual(self.cmds.getAttr(left + ".rotateY"), 11)
        copy = self.session.copy_to_user(approved)
        self.assertEqual((copy.source, copy.name), ("user", "signed_off"))
        self.assertTrue(copy.file.writable)
        with self.assertRaisesRegex(self.library.LibraryError, "already has"):
            self.session.copy_to_user(approved)

    def test_legacy_files_are_listed_and_apply(self):
        left, _right = self.left_right(self.root_node)
        self.cmds.setAttr(left + ".rotateY", 9)
        folder = self.user_folder(self.library.POSE)
        os.makedirs(folder)
        self.cmds.saveRigPose(self.root_node, file=os.path.join(folder, "old.json").replace("\\", "/"))
        self.cmds.setAttr(left + ".rotateY", 0)
        self.session.refresh()
        old = self.entry(self.session, "old")
        self.assertTrue(old.file.legacy)
        self.session.select(old)
        self.session.apply()
        self.assertEqual(self.cmds.getAttr(left + ".rotateY"), 9)
        self.assertFalse(self.session.rename(old, "old").file.legacy)


class ForTheWindow(LibraryBase):
    """What the library browser's window reads from the session that it can't compute itself (design 12e)."""

    def setUp(self):
        super().setUp()
        self.root_node = self.build(HERO)
        self.left, self.right = self.left_right(self.root_node)
        self.session = self.browser.LibrarySession()

    def set_file_meta(self, entry, **meta):
        import rigmodules.library
        rigmodules.library.set_data_file_meta(entry.path, meta)
        # The file is edited behind the session's back. The index caches by modified time, and two writes can land
        # on one tick of the file system's clock, so the cached read is dropped as the session's own edits drop it.
        self.session._index.forget(entry.path)
        self.session.refresh()
        return self.entry(self.session, entry.name)

    def test_facets_are_the_values_in_use_before_the_search_filters_them(self):
        first = self.session.save("fist", tags=("hands", "Angry"))
        self.set_file_meta(first, category="Expressions", status="review", rigRegions=["hands"])
        self.session.save("idle", tags=("body",))
        self.session.set_query("tag:body")
        facets = self.session.facets()
        self.assertEqual(facets["tag"], ["Angry", "body", "hands"], "sorted ignoring case, and fist is not hidden by the query")
        self.assertEqual((facets["region"], facets["status"], facets["category"]), (["hands"], ["review"], ["Expressions"]))
        self.assertEqual(facets["template"], ["game"])
        self.assertEqual(list(facets), list(self.browser.FACET_FIELDS))

    def test_facets_leave_out_a_source_that_is_switched_off(self):
        os.makedirs(self.hero_asset.path("controlposes", "game"))
        self.cmds.saveRigPose(self.root_node, file=os.path.join(self.hero_asset.path("controlposes", "game"), "a.controlpose.json").replace("\\", "/"),
                              meta=json.dumps({"tags": ["approved_only"]}))
        self.session.refresh()
        self.assertIn("approved_only", self.session.facets()["tag"])
        self.session.set_source_enabled("approved", False)
        self.assertNotIn("approved_only", self.session.facets()["tag"])

    def test_name_taken_looks_in_the_users_library_for_the_open_kind(self):
        self.assertFalse(self.session.name_taken("wave"))
        self.session.save("wave")
        self.assertTrue(self.session.name_taken("wave"))
        self.session.set_kind("animation")
        self.assertFalse(self.session.name_taken("wave"), "poses and animations are different libraries")
        with self.assertRaises(self.library.LibraryError):
            self.session.name_taken("a/b")

    def test_frames_come_from_the_scene(self):
        self.cmds.playbackOptions(minTime=3, maxTime=17)
        self.cmds.currentTime(8)
        self.assertEqual((self.session.playback_range(), self.session.current_frame()), ((3, 17), 8.0))

    def test_a_mask_is_made_of_the_selected_controls_by_side_and_usage(self):
        with self.assertRaisesRegex(RuntimeError, "Select controls"):
            self.session.mask_from_selection("Arm")
        self.cmds.select(self.left, replace=True)
        mask = self.session.mask_from_selection("  Left arm ")
        self.assertEqual((mask.name, mask.source), ("Left arm", "user"))
        self.assertEqual({(item.side, item.usage) for item in mask.items}, {("Left", "arm")})
        with self.assertRaisesRegex(self.library.LibraryError, "needs a name"):
            self.session.mask_from_selection(" ")

        self.session.save_mask(mask)
        self.session.set_scope("Left arm")
        self.cmds.select(clear=True)
        self.assertEqual(self.cmds.ls(self.session.scope_controls(), long=True), self.cmds.ls(self.left, long=True))

    def test_a_status_or_region_outside_the_projects_lists_is_a_warning_in_the_details(self):
        entry = self.session.save("odd")
        self.assertEqual(len(self.session.details(entry)), 1)
        entry = self.set_file_meta(entry, status="draft", rigRegions=["hands", "tail"])
        lines = self.session.details(entry)
        self.assertEqual(len(lines), 3)
        self.assertRegex(lines[1], r"rig region 'tail' is not one this project lists \(lowerBody, upperBody, head, hands\)")
        self.assertRegex(lines[2], r"status 'draft' is not one this project lists \(scratch, review, final\)")
        entry = self.set_file_meta(entry, status="final", rigRegions=["hands"])
        self.assertEqual(len(self.session.details(entry)), 1)

    def test_a_project_that_lists_no_vocabulary_checks_nothing(self):
        entry = self.session.save("odd")
        entry = self.set_file_meta(entry, status="anything", rigRegions=["wherever"])
        with mock.patch.object(self.session, "_vocabulary", return_value=([], [])):
            self.assertEqual(len(self.session.details(entry)), 1)

    def test_an_asset_whose_project_cannot_be_read_is_not_checked(self):
        entry = self.set_file_meta(self.session.save("x"), status="draft")
        self.assertEqual(len(self.session.details(entry)), 2)
        with mock.patch.object(self.asset.Asset, "project", new_callable=mock.PropertyMock,
                               side_effect=self.asset.ProjectError("no project.json")):
            self.assertEqual(self.session._vocabulary(), ([], []))
            self.assertEqual(len(self.session.details(entry)), 1)


if __name__ == "__main__":
    unittest.main()
