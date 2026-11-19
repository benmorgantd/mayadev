"""bmaya.maya.asseteditor and bmaya.maya.assetfiles in mayapy: the Asset Editor's session and its file rows, on real
rigs and a temporary projects root (RigModules D61).

Needs RIGMODULES_PLUGIN, the path of a RigModules.mll (copy it first if a Maya session has the build loaded), and the
rigmodules package on the path (RigModules.mod puts it there). Skipped without them.
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
HERO = "shooter\\main\\characters\\hero"
VILLAIN = "shooter\\main\\characters\\villain"
TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "AssetEditorTest",
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


class EditorBase(unittest.TestCase):

    def setUp(self):
        from maya import cmds
        import bmaya.core.asset
        import bmaya.core.asset.context
        import bmaya.core.asset.handlers
        import bmaya.core.prompts
        import bmaya.maya.activerig
        import bmaya.maya.asseteditor
        import bmaya.maya.assethandlers
        import bmaya.maya.assettools
        import bmaya.maya.eventsregistry

        self.cmds = cmds
        self.asset_module = bmaya.core.asset
        self.context_module = bmaya.core.asset.context
        self.prompts = bmaya.core.prompts
        self.activerig = bmaya.maya.activerig
        self.editor = bmaya.maya.asseteditor
        self.tools = bmaya.maya.assettools
        self.registry = bmaya.maya.eventsregistry.EventsRegistry()
        temp = tempfile.mkdtemp(prefix="bmaya_asset_editor_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.temp = temp
        self.root = os.path.join(temp, "projects")
        environ = {"RIGGING_PROJECT_DIR": self.root, "BMAYA_VERSIONS_DIR": os.path.join(temp, "local_versions")}
        patcher = mock.patch.dict(os.environ, environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        bmaya.core.asset.Project.create(os.path.join(self.root, "shooter", "main"))
        self.hero = bmaya.core.asset.Asset.create(HERO, "Character")
        self.template = os.path.join(temp, "template.json")
        with open(self.template, "w", encoding="utf-8") as handle:
            json.dump(TEMPLATE, handle)
        for file_type in ("skeleton", "model", "rig", "shapes", "template", "weights"):
            self.addCleanup(bmaya.core.asset.handlers.unregister, file_type)
        cmds.optionVar(remove=self.editor.LAST_ASSET_OPTION)
        cmds.file(new=True, force=True)
        self.addCleanup(self.cleanup_session)
        self.sessions = []

    def cleanup_session(self):
        for session in self.sessions:
            session.close()
        tracker = self.activerig.ActiveRigTracker.current()
        if tracker is not None:
            tracker.stop()
        self.cmds.optionVar(remove=self.editor.LAST_ASSET_OPTION)

    def session(self, asset_id=None):
        session = self.editor.AssetEditorSession(asset_id)
        self.sessions.append(session)
        return session

    def answers(self, *answers):
        return self.prompts.ScriptedPrompter(answers)

    def make_skeleton(self):
        cmds = self.cmds
        joints = []
        for i, usage in enumerate(("spine1", "spine2")):
            if joints:
                cmds.select(joints[-1], replace=True)
            else:
                cmds.select(clear=True)
            joint = cmds.joint(name=f"spine_{i:02d}_M_JNT", position=(0, i * 2, 0))
            cmds.rigJointMarkup(joint, usage=usage, side="Center", export=True, skin=True)
            joints.append(joint)
        cmds.select(clear=True)
        return joints

    def make_buildable_hero(self):
        """The hero with the rig game and its skeleton saved, in a new empty scene."""
        self.tools.new_rig(HERO, self.template)
        self.tools.save_skeleton(HERO, joints=self.make_skeleton())
        self.cmds.file(new=True, force=True)

    def callback_keys(self):
        return [key for key in self.registry.callbacks if key.startswith(self.editor.CALLBACK_PREFIX)]


class Context(EditorBase):

    def test_the_session_starts_the_context_on_the_given_asset(self):
        session = self.session(HERO)
        self.assertIs(self.context_module.AssetContext.current(), session.context)
        self.assertEqual(session.context.asset_id, HERO)

    def test_with_no_asset_it_takes_the_active_rigs(self):
        self.make_buildable_hero()
        rig_root = self.tools.build_rig(HERO, "game")
        self.assertEqual(self.session().context.asset_id, HERO, rig_root)

    def test_with_no_rig_it_prefills_the_asset_it_was_last_on(self):
        first = self.session(HERO)
        first.set_asset(HERO)
        first.close()
        self.assertEqual(self.session().context.asset_id, HERO)

    def test_with_neither_it_starts_empty(self):
        self.assertIsNone(self.session().context.asset_id)

    def test_new_open_and_save_do_not_change_the_asset(self):
        self.make_buildable_hero()
        session = self.session(HERO)
        self.cmds.file(new=True, force=True)
        self.assertEqual(session.context.asset_id, HERO)
        self.tools.build_rig(HERO, "game")
        self.cmds.file(rename=os.path.join(self.temp, "scene.ma"))
        self.cmds.file(save=True, type="mayaAscii", force=True)
        self.assertEqual(session.context.asset_id, HERO)
        self.cmds.file(os.path.join(self.temp, "scene.ma"), open=True, force=True)
        self.assertEqual(session.context.asset_id, HERO)

    def test_a_new_scene_reads_the_scene_again(self):
        self.make_buildable_hero()
        session = self.session(HERO)
        session.files.build_rig()
        self.assertIsNotNone(session.files.rig_root)
        calls = []
        session.changed.connect(lambda: calls.append(1))
        self.cmds.file(new=True, force=True)
        self.assertIsNone(session.files.rig_root)
        self.assertTrue(calls)

    def test_another_assets_active_rig_is_shown_but_not_followed(self):
        self.make_buildable_hero()
        self.asset_module.Asset.create(VILLAIN, "Character")
        session = self.session(VILLAIN)
        self.assertEqual(session.rig_mismatch(), "")
        self.tools.build_rig(HERO, "game")
        self.assertEqual(session.context.asset_id, VILLAIN)
        self.assertIn(HERO, session.rig_mismatch())

    def test_use_active_rig_switches_to_its_asset_and_rig(self):
        self.make_buildable_hero()
        self.tools.build_rig(HERO, "game")
        session = self.session(HERO)
        session.set_asset(None)
        session.use_active_rig()
        self.assertEqual((session.context.asset_id, session.context.rig), (HERO, "game"))
        self.assertEqual(session.rig_mismatch(), "")

    def test_use_active_rig_with_no_rig_raises(self):
        with self.assertRaisesRegex(RuntimeError, "no RigModules rig"):
            self.session(HERO).use_active_rig()

    def test_the_active_rig_changing_tells_the_view(self):
        self.make_buildable_hero()
        session = self.session(HERO)
        calls = []
        session.changed.connect(lambda: calls.append(1))
        self.tools.build_rig(HERO, "game")
        self.activerig.ActiveRigTracker().refresh()
        self.assertTrue(calls)

    def test_set_asset_remembers_it_for_the_next_editor(self):
        session = self.session()
        session.set_asset(HERO)
        self.assertEqual(self.editor.read_last_asset(), HERO)

    def test_an_invalid_id_raises_and_is_not_remembered(self):
        session = self.session()
        with self.assertRaises(self.asset_module.AssetIdError):
            session.set_asset("Not An Id")
        self.assertIsNone(self.editor.read_last_asset())

    def test_the_asset_list_is_the_projects_assets(self):
        self.assertEqual(self.session().asset_ids, [HERO])


class Closing(EditorBase):

    def test_close_removes_every_callback_and_clears_the_context(self):
        session = self.session(HERO)
        session.watch_selection(True)
        self.assertEqual(len(self.callback_keys()), 4)
        session.close()
        self.assertEqual(self.callback_keys(), [])
        self.assertIsNone(self.context_module.AssetContext.current())
        self.assertIsNone(session.context.asset_id)

    def test_close_stops_following_the_tracker_and_the_scene(self):
        self.make_buildable_hero()
        session = self.session(HERO)
        session.close()
        calls = []
        session.changed.connect(lambda: calls.append(1))
        self.tools.build_rig(HERO, "game")
        self.activerig.ActiveRigTracker().refresh()
        self.cmds.file(new=True, force=True)
        self.assertEqual(calls, [])

    def test_close_twice_is_safe(self):
        session = self.session(HERO)
        session.close()
        session.close()
        self.assertTrue(session.closed)

    def test_maya_exiting_closes_the_session(self):
        session = self.session(HERO)
        session._on_maya_exiting()
        self.assertTrue(session.closed)
        self.assertEqual(self.callback_keys(), [])

    def test_a_new_session_after_a_close_has_a_fresh_context(self):
        self.session(HERO).close()
        self.assertIsNone(self.context_module.AssetContext.current())
        self.assertEqual(self.session(HERO).context.asset_id, HERO)

    def test_two_sessions_keep_their_own_callbacks(self):
        first, second = self.session(HERO), self.session(HERO)
        self.assertEqual(len(self.callback_keys()), 6)
        first.close()
        self.assertEqual(len(self.callback_keys()), 3)
        self.assertIs(self.context_module.AssetContext.current(), second.context)

    def test_the_selection_callback_exists_only_while_watching(self):
        session = self.session(HERO)
        self.assertEqual(len(self.callback_keys()), 3)
        session.watch_selection(True)
        session.watch_selection(True)
        self.assertEqual(len(self.callback_keys()), 4)
        selections = []
        session.selection_changed.connect(lambda: selections.append(1))
        self.cmds.polyCube()
        self.assertTrue(selections)
        session.watch_selection(False)
        self.assertEqual(len(self.callback_keys()), 3)

    def test_watching_a_closed_session_registers_nothing(self):
        session = self.session(HERO)
        session.close()
        session.watch_selection(True)
        self.assertEqual(self.callback_keys(), [])


class FileRows(EditorBase):

    def test_the_rows_of_an_asset_with_a_rig_and_no_skeleton_file(self):
        self.tools.new_rig(HERO, self.template)
        files = self.session(HERO).files
        self.assertEqual([row.key for row in files.rows], ["skeleton", "model", "weights", "rig", "shapes", "template"])
        skeleton = files.row("skeleton")
        self.assertEqual((skeleton.owner, skeleton.exists, skeleton.versions), ("default", False, 0))
        self.assertTrue(files.row("template").exists)
        self.assertEqual((files.row("template").saves, files.row("template").loads), (False, False))

    def test_a_missing_asset_has_a_message_and_no_rows(self):
        files = self.session("shooter\\main\\characters\\ghost").files
        self.assertEqual(files.rows, [])
        self.assertIn("no asset.json", files.message)

    def test_no_asset_has_a_message(self):
        files = self.session().files
        self.assertEqual((files.rows, files.message), ([], "Pick an asset."))

    def test_blocked_reasons_without_joints_a_look_or_a_rig_in_the_scene(self):
        self.tools.new_rig(HERO, self.template)
        files = self.session(HERO).files
        self.assertEqual(files.row("skeleton").save_blocked, "There are no joints in the scene.")
        self.assertIn("no look", files.row("model").save_blocked)
        self.assertIn("no look", files.row("weights").save_blocked)
        self.assertIn("not in the scene", files.row("rig").save_blocked)
        self.assertIn("not in the scene", files.row("shapes").save_blocked)
        self.assertIn("not saved yet", files.row("skeleton").load_blocked)

    def test_an_asset_with_no_rig_says_to_add_one(self):
        files = self.session(HERO).files
        self.assertIn("no rig", files.row("rig").save_blocked)

    def test_a_blocked_save_raises_its_reason(self):
        files = self.session(HERO).files
        with self.assertRaisesRegex(RuntimeError, "no joints"):
            files.save("skeleton", self.answers())

    def test_a_template_has_no_save_or_load(self):
        self.tools.new_rig(HERO, self.template)
        files = self.session(HERO).files
        with self.assertRaisesRegex(RuntimeError, "not saved from here"):
            files.save("template", self.answers())
        with self.assertRaisesRegex(RuntimeError, "not loaded from here"):
            files.load("template")


class SkeletonFiles(EditorBase):

    def test_save_writes_the_skeleton_and_the_row_follows(self):
        self.tools.new_rig(HERO, self.template)
        self.make_skeleton()
        session = self.session(HERO)
        calls = []
        session.changed.connect(lambda: calls.append(1))
        path = session.files.save("skeleton", self.answers())
        self.assertEqual(path, self.hero.path("skeleton", "default"))
        self.assertTrue(os.path.isfile(path))
        row = session.files.row("skeleton")
        self.assertEqual((row.exists, row.versions, row.save_blocked), (True, 0, ""))
        self.assertEqual(session.context.skeleton, "default", "the first skeleton becomes the chosen one")

    def test_replacing_asks_first_and_keeps_a_version(self):
        self.tools.new_rig(HERO, self.template)
        self.make_skeleton()
        files = self.session(HERO).files
        files.save("skeleton", self.answers())
        prompter = self.answers(True)
        files.save("skeleton", prompter)
        self.assertEqual([(q.kind, q.title, q.options) for q in prompter.asked],
                         [("confirm", "Save Skeleton", ("Replace",))])
        self.assertEqual(files.row("skeleton").versions, 1)

    def test_declining_the_replace_changes_nothing(self):
        self.tools.new_rig(HERO, self.template)
        self.make_skeleton()
        files = self.session(HERO).files
        files.save("skeleton", self.answers())
        before = os.path.getmtime(self.hero.path("skeleton", "default"))
        self.assertIsNone(files.save("skeleton", self.answers(False)))
        self.assertEqual((os.path.getmtime(self.hero.path("skeleton", "default")), files.row("skeleton").versions),
                         (before, 0))

    def test_the_selected_joints_are_saved_not_the_whole_scene(self):
        self.tools.new_rig(HERO, self.template)
        joints = self.make_skeleton()
        extra = self.cmds.joint(name="stray_00_M_JNT")
        self.cmds.select(joints, replace=True)
        files = self.session(HERO).files
        files.save("skeleton", self.answers())
        self.cmds.file(new=True, force=True)
        files.load("skeleton")
        self.assertEqual(sorted(self.cmds.ls(type="joint")), ["spine_00_M_JNT", "spine_01_M_JNT"], extra)

    def test_load_creates_the_joints_and_selects_them(self):
        self.tools.new_rig(HERO, self.template)
        self.make_skeleton()
        files = self.session(HERO).files
        files.save("skeleton", self.answers())
        self.cmds.file(new=True, force=True)
        files.load("skeleton")
        self.assertEqual(len(self.cmds.ls(type="joint")), 2)
        self.assertEqual(len(self.cmds.ls(selection=True)), 2)

    def test_joints_driven_by_a_rig_are_refused_with_the_assettools_message(self):
        self.make_buildable_hero()
        session = self.session(HERO)
        session.files.build_rig()
        with self.assertRaisesRegex(RuntimeError, "driven by a rig"):
            session.files.save("skeleton", self.answers(True))


class RigFiles(EditorBase):

    def test_build_rig_builds_selects_and_unblocks_the_rig_rows(self):
        self.make_buildable_hero()
        files = self.session(HERO).files
        rig_root = files.build_rig()
        self.assertEqual(files.rig_root, rig_root)
        self.assertEqual(self.cmds.ls(selection=True), [rig_root])
        self.assertEqual((files.row("rig").save_blocked, files.row("shapes").save_blocked), ("", ""))

    def test_build_rig_without_a_rig_says_so(self):
        with self.assertRaisesRegex(RuntimeError, "no rig"):
            self.session(HERO).files.build_rig()

    def test_a_rig_of_another_asset_does_not_unblock_this_assets_rows(self):
        self.make_buildable_hero()
        self.asset_module.Asset.create(VILLAIN, "Character")
        self.tools.build_rig(HERO, "game")
        files = self.session(VILLAIN).files
        self.assertIsNone(files.rig_root)

    def test_save_and_load_the_control_shapes(self):
        self.make_buildable_hero()
        files = self.session(HERO).files
        files.build_rig()
        path = files.save("shapes", self.answers())
        self.assertTrue(os.path.isfile(path))
        control = self.cmds.ls(type="rigControlNode")[0]
        self.cmds.setAttr(control + ".filled", True)
        files.load("shapes")
        self.assertFalse(self.cmds.getAttr(control + ".filled"))

    def test_save_rig_writes_the_scene_as_the_rig_file(self):
        self.make_buildable_hero()
        files = self.session(HERO).files
        files.build_rig()
        path = files.save("rig", self.answers())
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(files.row("rig").exists)


class AskingForTheAsset(EditorBase):

    def test_without_the_editor_a_tool_asks_for_the_id(self):
        prompter = self.answers(HERO)
        self.assertEqual(self.tools._ask_asset_id(prompter, "Save Skeleton"), HERO)
        self.assertEqual([q.kind for q in prompter.asked], ["ask_text"])

    def test_with_the_editor_open_a_tool_offers_its_asset_and_confirms_with_one_question(self):
        self.session(HERO)
        prompter = self.answers(HERO)
        self.assertEqual(self.tools._ask_asset_id(prompter, "Save Skeleton"), HERO)
        question = prompter.asked[0]
        self.assertEqual((question.kind, question.options), ("choose", (HERO, "Another asset...")))
        self.assertEqual(len(prompter.asked), 1)

    def test_choosing_another_asset_asks_for_the_id(self):
        self.session(HERO)
        prompter = self.answers("Another asset...", VILLAIN)
        self.assertEqual(self.tools._ask_asset_id(prompter, "Save Skeleton"), VILLAIN)
        self.assertEqual([q.kind for q in prompter.asked], ["choose", "ask_text"])

    def test_cancelling_the_offer_cancels_the_tool(self):
        self.session(HERO)
        self.assertIsNone(self.tools._ask_asset_id(self.answers(None), "Save Skeleton"))

    def test_an_editor_with_no_asset_asks_as_before(self):
        self.session()
        prompter = self.answers(HERO)
        self.tools._ask_asset_id(prompter, "Save Skeleton")
        self.assertEqual([q.kind for q in prompter.asked], ["ask_text"])

    def test_a_new_assets_id_is_never_the_editors(self):
        self.session(HERO)
        prompter = self.answers(VILLAIN)
        self.tools._ask_asset_id(prompter, "New Asset", use_context=False)
        self.assertEqual([q.kind for q in prompter.asked], ["ask_text"])

    def test_after_close_the_tools_ask_as_before(self):
        session = self.session(HERO)
        session.close()
        prompter = self.answers(HERO)
        self.tools._ask_asset_id(prompter, "Save Skeleton")
        self.assertEqual([q.kind for q in prompter.asked], ["ask_text"])

    def test_the_save_skeleton_tool_uses_the_editors_asset(self):
        self.tools.new_rig(HERO, self.template)
        self.make_skeleton()
        self.session(HERO)
        self.tools.save_skeleton_interactive(self.answers(HERO, "default"))
        self.assertTrue(os.path.isfile(self.hero.path("skeleton", "default")))


class Creating(EditorBase):

    def test_create_asset_works_on_it(self):
        session = self.session()
        asset_id = session.create_asset(self.answers(VILLAIN, "Character"))
        self.assertEqual((asset_id, session.context.asset_id), (VILLAIN, VILLAIN))
        self.assertIn(VILLAIN, session.asset_ids)
        self.assertTrue(self.asset_module.Asset(VILLAIN).exists())

    def test_a_cancelled_create_asset_changes_nothing(self):
        session = self.session(HERO)
        self.assertIsNone(session.create_asset(self.answers(None)))
        self.assertEqual(session.context.asset_id, HERO)

    def test_create_rig_adds_it_to_the_editors_asset_and_picks_it(self):
        session = self.session(HERO)
        rig = session.create_rig(self.answers(self.template, "body", "default", "none"))
        self.assertEqual((rig, session.context.rig), ("body", "body"))
        self.assertEqual(self.hero.rigs, ["body"])

    def test_create_look_adds_it_and_picks_it(self):
        session = self.session(HERO)
        look = session.create_look(self.answers("default", "default"))
        self.assertEqual((look, session.context.look), ("default", "default"))

    def test_create_rig_with_no_asset_asks_to_pick_one(self):
        with self.assertRaisesRegex(RuntimeError, "Pick an asset"):
            self.session().create_rig(self.answers())

    def test_create_project_makes_it_and_reads_the_list_again(self):
        session = self.session(HERO)
        folder = os.path.join(self.root, "puzzle", "levels")
        self.assertEqual(session.create_project(self.answers(folder)), os.path.normpath(folder))
        self.asset_module.Asset.create("puzzle\\levels\\props\\gem", "Prop")
        session.refresh()
        self.assertIn("puzzle\\levels\\props\\gem", session.asset_ids)


if __name__ == "__main__":
    unittest.main()
