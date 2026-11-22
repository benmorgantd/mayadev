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
        for file_type in ("skeleton", "model", "rig", "shapes", "template", "weights", "textures"):
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
        self.assertEqual([row.key for row in files.rows], ["skeleton", "model", "weights", "textures", "rig", "shapes", "template"])
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

    def test_the_textures_row_makes_and_opens_the_folder_and_counts_the_images(self):
        self.tools.new_look(HERO)
        files = self.session(HERO).files
        opened = []
        files.opener = opened.append
        row = files.row("textures")
        self.assertEqual((row.opens_folder, row.saves, row.loads, row.exists, row.file_count), (True, True, True, False, None))
        self.assertEqual((row.open_blocked, row.note, row.versions), ("", "not mapped to meshes yet", 0))
        self.assertTrue(row.path.endswith(os.path.join("textures", "textures.json")))
        path = files.open_folder("textures")
        self.assertEqual(opened, [path])
        self.assertTrue(os.path.isdir(path))
        self.assertEqual(files.row("textures").file_count, 0)
        for name in ("skin_albedo.PNG", "skin_normal.tga", "notes.txt"):
            with open(os.path.join(path, name), "wb"):
                pass
        os.makedirs(os.path.join(path, "old.png"))   # a folder with an image's name is not an image
        files.refresh()
        self.assertEqual(files.row("textures").file_count, 2)
        self.assertEqual(files.open_folder("textures"), path)   # an existing folder is kept as it is
        self.assertEqual(files.row("textures").file_count, 2)

    def test_the_textures_row_is_the_sidecar_and_says_how_many_meshes_it_maps(self):
        import bmaya.core.asset.textures
        self.tools.new_look(HERO)
        files = self.session(HERO).files
        folder = self.hero.path("textures", "default")
        os.makedirs(folder)
        texture_map = bmaya.core.asset.textures.TextureMap(
            {"mat": bmaya.core.asset.textures.Material(slots={"baseColor": "a.png"})},
            {"id1": bmaya.core.asset.textures.MeshEntry("box_geo", "mat")})
        bmaya.core.asset.textures.write(bmaya.core.asset.textures.get_path(folder), texture_map)
        files.refresh()
        row = files.row("textures")
        self.assertEqual((row.exists, row.note), (True, "1 meshes mapped"))
        self.assertIsNotNone(row.modified)

    def test_textures_save_and_load_need_a_rig_in_the_scene(self):
        self.tools.new_look(HERO)
        row = self.session(HERO).files.row("textures")
        self.assertIn("no rig", row.save_blocked)
        self.assertIn("no rig", row.load_blocked)

    def test_the_textures_row_imports_textures_through_its_form_and_shades_the_rig(self):
        cmds = self.cmds
        self.make_buildable_hero()
        self.tools.new_look(HERO)
        files = self.session(HERO).files
        files.build_rig()
        cmds.setRigMeshId(cmds.polyCube(name="hero_game:box_geo", constructionHistory=False)[0])
        cmds.select("hero_game:box_geo", replace=True)
        self.assertTrue(files.row("textures").imports_images)
        scans = os.path.join(self.temp, "scans")
        os.makedirs(scans)
        source = os.path.join(scans, "skin.png")
        with open(source, "wb"):
            pass
        form = self.tools.TextureFiles(material="body", albedo=source)
        folder = files.import_textures("textures", self.answers(form))
        self.assertEqual(folder, self.hero.path("textures", "default"))
        row = files.row("textures")
        self.assertEqual((row.exists, row.file_count, row.note), (True, 1, "1 meshes mapped"))
        self.assertEqual(os.listdir(folder).count("hero_default_body_albedo.png"), 1)

    def test_cancelling_import_textures_returns_none(self):
        self.make_buildable_hero()
        self.tools.new_look(HERO)
        files = self.session(HERO).files
        files.build_rig()
        mesh = self.cmds.polyCube(name="hero_game:box_geo", constructionHistory=False)[0]
        self.cmds.setRigMeshId(mesh)
        self.cmds.select(mesh, replace=True)
        self.assertIsNone(files.import_textures("textures", self.answers(None)))
        self.cmds.select(clear=True)
        with self.assertRaisesRegex(RuntimeError, "Select the meshes"):
            files.import_textures("textures", self.answers())

    def test_import_textures_without_a_rig_says_why_and_other_rows_take_none(self):
        self.tools.new_look(HERO)
        files = self.session(HERO).files
        with self.assertRaisesRegex(RuntimeError, "no rig"):
            files.import_textures("textures", self.answers())
        with self.assertRaisesRegex(RuntimeError, "takes no textures"):
            files.import_textures("template", self.answers())

    def test_the_textures_row_is_blocked_without_a_look(self):
        files = self.session(HERO).files
        self.assertIn("no look", files.row("textures").open_blocked)
        with self.assertRaisesRegex(RuntimeError, "no look"):
            files.open_folder("textures")

    def test_only_a_folder_row_opens(self):
        files = self.session(HERO).files
        with self.assertRaisesRegex(RuntimeError, "no folder to open"):
            files.open_folder("template")

    def test_the_textures_handler_saves_a_folder_and_loads_its_images(self):
        self.tools.new_look(HERO)
        import bmaya.maya.assethandlers
        bmaya.maya.assethandlers.register()
        self.addCleanup(self.asset_module.handlers.unregister, "textures")
        hero = self.asset_module.Asset(HERO)
        look = self.session(HERO).context.look
        path = self.asset_module.handlers.save(hero, "textures", look)
        self.assertTrue(os.path.isdir(path))
        with open(os.path.join(path, "a.png"), "wb"):
            pass
        self.assertEqual(self.asset_module.handlers.load(hero, "textures", look), [os.path.join(path, "a.png")])

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

    def test_the_whole_scene_is_saved_whatever_is_selected(self):
        self.tools.new_rig(HERO, self.template)
        joints = self.make_skeleton()
        self.cmds.select(joints[0], replace=True)
        files = self.session(HERO).files
        files.save("skeleton", self.answers())
        self.cmds.file(new=True, force=True)
        files.load("skeleton")
        self.assertEqual(sorted(self.cmds.ls(type="joint")), ["spine_00_M_JNT", "spine_01_M_JNT"],
                         "a selected joint does not shrink the skeleton")

    def test_the_whole_model_is_saved_whatever_is_selected(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        cmds.polyCube(name="box_geo", constructionHistory=False)
        crate = cmds.polyCube(name="crate_geo", constructionHistory=False)[0]
        cmds.select(crate, replace=True)
        self.session(HERO).files.save("model", self.answers())
        cmds.file(new=True, force=True)
        cmds.file(self.hero.path("model", "default"), i=True, type="mayaAscii", namespace="look")
        self.assertEqual(sorted(cmds.ls("look:*", type="transform")), ["look:box_geo", "look:crate_geo"],
                         "a selected mesh does not shrink the model")

    def test_restore_puts_a_version_back_and_keeps_the_replaced_file(self):
        import bmaya.maya.assetfiles
        cmds = self.cmds
        self.tools.new_look(HERO)
        cmds.polyCube(name="box_geo", constructionHistory=False)
        files = self.session(HERO).files
        files.save("model", self.answers())                   # only box_geo
        cmds.polyCube(name="crate_geo", constructionHistory=False)
        files.save("model", self.answers(True))               # box_geo and crate_geo; version 1 is box_geo alone
        prompter = self.answers(bmaya.maya.assetfiles.RestoreChoice(version=1))
        path = files.restore("model", prompter)
        self.assertEqual([(q.kind, q.title, q.default) for q in prompter.asked],
                         [("ask_form", "Restore Model (versions 1 to 1)", bmaya.maya.assetfiles.RestoreChoice(1))])
        self.assertEqual(files.row("model").versions, 2, "the replaced model is kept, so the restore can be undone")
        self.assertEqual(sorted(cmds.ls("*_geo", type="transform")), ["box_geo", "crate_geo"], "the scene is not touched")
        cmds.file(new=True, force=True)
        cmds.file(path, i=True, type="mayaAscii", namespace="look")
        self.assertEqual(cmds.ls("look:*", type="transform"), ["look:box_geo"])

    def test_restore_cancelled_or_without_versions_changes_nothing(self):
        cmds = self.cmds
        self.tools.new_look(HERO)
        cmds.polyCube(name="box_geo", constructionHistory=False)
        files = self.session(HERO).files
        files.save("model", self.answers())
        with self.assertRaisesRegex(RuntimeError, "no local versions"):
            files.restore("model", self.answers())
        files.save("model", self.answers(True))
        before = os.path.getmtime(self.hero.path("model", "default"))
        self.assertIsNone(files.restore("model", self.answers(None)))
        self.assertEqual((os.path.getmtime(self.hero.path("model", "default")), files.row("model").versions),
                         (before, 1))

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
    def test_build_rig_passes_ignore_skeleton_hash_on(self):
        """The weights check itself is tested in test_maya_asset_tools; this covers the editor's pass-through."""
        import unittest.mock
        self.make_buildable_hero()
        files = self.session(HERO).files
        real = self.tools.build_rig
        with unittest.mock.patch.object(self.tools, "build_rig", side_effect=real) as build:
            files.build_rig()
            self.cmds.file(new=True, force=True)
            files.build_rig(ignore_skeleton_hash=True)
        self.assertEqual([call.kwargs["ignore_skeleton_hash"] for call in build.call_args_list], [False, True])

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


class Markup(EditorBase):

    def joints(self, *names, namespace=""):
        """Unmarked joints with these names, each its own root."""
        made = []
        for index, name in enumerate(names):
            self.cmds.select(clear=True)
            made.append(self.cmds.joint(name=f"{namespace}{name}", position=(index, 0, 0)))
        return made

    def mark(self, joint, usage, side="Center", export=True, skin=True):
        self.cmds.rigJointMarkup(joint, usage=usage, side=side, export=export, skin=skin)

    def model(self, *selected):
        session = self.session(HERO)
        if selected:
            self.cmds.select(list(selected), replace=True)
        else:
            self.cmds.select(clear=True)
        session.markup.set_active(True)
        return session.markup

    def read(self, joint):
        return json.loads(self.cmds.rigJointMarkup(joint, query=True)[0])

    def test_with_no_selection_it_says_what_to_select(self):
        self.assertEqual(self.model().summary, "Select joints or rig controls.")

    def test_an_inactive_model_does_not_read_the_selection(self):
        session = self.session(HERO)
        [joint] = self.joints("a_00_M_JNT")
        self.assertEqual(session.markup.joints, [])
        session.markup.set_active(True)
        self.assertEqual(session.markup.joints, [self.cmds.ls(joint, long=True)[0]])

    def test_the_selection_changing_refreshes_an_active_model_only(self):
        session = self.session(HERO)
        session.watch_selection(True)
        [joint] = self.joints("a_00_M_JNT")
        self.mark(joint, "spine")
        self.cmds.select(joint, replace=True)
        self.assertEqual(session.markup.joints, [])
        session.markup.set_active(True)
        self.cmds.select(clear=True)
        self.assertEqual(session.markup.joints, [])
        self.cmds.select(joint, replace=True)
        self.assertEqual(len(session.markup.joints), 1)

    def test_marked_and_unmarked_joints_are_told_apart(self):
        a, b, c = self.joints("a_00_M_JNT", "b_00_M_JNT", "c_00_M_JNT")
        self.mark(a, "spine")
        self.mark(b, "chest")
        model = self.model(a, b, c)
        self.assertEqual((len(model.marked), len(model.unmarked)), (2, 1))
        self.assertEqual(model.summary, "3 joint(s): 2 marked, 1 not")

    def test_a_field_the_joints_agree_on_has_one_value_and_one_they_dont_is_mixed(self):
        a, b = self.joints("a_00_L_JNT", "b_00_L_JNT")
        self.mark(a, "arm", "Left", export=True, skin=True)
        self.mark(b, "hand", "Left", export=False, skin=True)
        fields = self.model(a, b).fields
        self.assertEqual((fields["side"].value, fields["side"].mixed), ("Left", False))
        self.assertEqual((fields["usage"].value, fields["usage"].mixed), (None, True))
        self.assertEqual((fields["export"].value, fields["export"].mixed), (None, True))
        self.assertEqual((fields["skin"].value, fields["skin"].mixed), (True, False))

    def test_set_field_edits_every_marked_joint_in_one_undo_step(self):
        self.cmds.undoInfo(state=True, infinity=True)
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm", "Left")
        self.mark(b, "hand", "Left")
        model = self.model(a, b)
        model.set_field("side", "Right")
        self.assertEqual([self.read(j)["side"] for j in (a, b)], ["Right", "Right"])
        self.assertEqual(model.fields["side"].value, "Right")
        self.cmds.undo()
        self.assertEqual([self.read(j)["side"] for j in (a, b)], ["Left", "Left"])

    def test_set_field_on_the_booleans(self):
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm", skin=True)
        self.mark(b, "hand", skin=False)
        self.model(a, b).set_field("skin", True)
        self.assertEqual([self.read(j)["skin"] for j in (a, b)], [True, True])

    def test_set_field_skips_unmarked_joints(self):
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm")
        self.model(a, b).set_field("side", "Left")
        self.assertEqual(self.read(a)["side"], "Left")
        self.assertEqual(self.cmds.rigJointMarkup(b, query=True), [""])

    def test_set_field_with_nothing_marked_says_to_add_markup(self):
        [a] = self.joints("a_00_M_JNT")
        with self.assertRaisesRegex(RuntimeError, "Add markup first"):
            self.model(a).set_field("side", "Left")

    def test_two_joints_cannot_be_given_one_usage_and_nothing_changes(self):
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm")
        self.mark(b, "hand")
        with self.assertRaisesRegex(RuntimeError, "unique on a skeleton"):
            self.model(a, b).set_field("usage", "arm")
        self.assertEqual([self.read(j)["usage"] for j in (a, b)], ["arm", "hand"])

    def test_a_usage_another_joint_of_the_skeleton_has_is_refused(self):
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm")
        self.mark(b, "hand")
        with self.assertRaisesRegex(RuntimeError, "unique on a skeleton"):
            self.model(b).set_field("usage", "arm")

    def test_the_same_usage_in_another_namespace_is_a_different_skeleton(self):
        self.cmds.namespace(add="one")
        self.cmds.namespace(add="two")
        a, = self.joints("a_00_M_JNT", namespace=":one:")
        b, = self.joints("b_00_M_JNT", namespace=":two:")
        self.mark(a, "arm")
        self.mark(b, "hand")
        self.model(b).set_field("usage", "arm")
        self.assertEqual(self.read(b)["usage"], "arm")

    def test_an_empty_usage_or_a_bad_side_is_refused(self):
        [a] = self.joints("a_00_M_JNT")
        self.mark(a, "arm")
        model = self.model(a)
        with self.assertRaisesRegex(RuntimeError, "can't be empty"):
            model.set_field("usage", "  ")
        with self.assertRaisesRegex(RuntimeError, "Center, Left, Right"):
            model.set_field("side", "Up")
        with self.assertRaisesRegex(RuntimeError, "not a markup field"):
            model.set_field("colour", "red")

    def test_add_markup_marks_one_joint(self):
        [a] = self.joints("a_00_M_JNT")
        model = self.model(a)
        model.add_markup("spine", "Center", export=True, skin=False)
        self.assertEqual(self.read(a), {"markupVersion": 1, "usage": "spine", "side": "Center", "export": True,
                                        "skin": False})
        self.assertEqual((len(model.marked), len(model.unmarked)), (1, 0))

    def test_add_markup_to_several_joints_needs_numbering(self):
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        model = self.model(a, b)
        with self.assertRaisesRegex(RuntimeError, "Number them"):
            model.add_markup("spine")
        self.assertEqual(self.cmds.rigJointMarkup(a, b, query=True), ["", ""])

    def test_numbered_markup_follows_the_selection_order_in_one_undo_step(self):
        self.cmds.undoInfo(state=True, infinity=True)
        a, b, c = self.joints("a_00_M_JNT", "b_00_M_JNT", "c_00_M_JNT")
        model = self.model(c, a, b)
        model.add_markup("spine", "Left", numbered=True)
        self.assertEqual([self.read(j)["usage"] for j in (c, a, b)], ["spine_00", "spine_01", "spine_02"])
        self.assertEqual({self.read(j)["side"] for j in (a, b, c)}, {"Left"})
        self.cmds.undo()
        self.assertEqual(self.cmds.rigJointMarkup(a, b, c, query=True), ["", "", ""])

    def test_add_markup_leaves_marked_joints_alone(self):
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm")
        self.model(a, b).add_markup("hand")
        self.assertEqual((self.read(a)["usage"], self.read(b)["usage"]), ("arm", "hand"))

    def test_add_markup_refuses_a_usage_the_skeleton_has(self):
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm")
        with self.assertRaisesRegex(RuntimeError, "unique on a skeleton"):
            self.model(b).add_markup("arm")
        self.assertEqual(self.cmds.rigJointMarkup(b, query=True), [""])

    def test_add_markup_with_every_joint_marked_says_so(self):
        [a] = self.joints("a_00_M_JNT")
        self.mark(a, "arm")
        with self.assertRaisesRegex(RuntimeError, "already has markup"):
            self.model(a).add_markup("hand")

    def test_remove_clears_the_markup_in_one_undo_step(self):
        self.cmds.undoInfo(state=True, infinity=True)
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm")
        self.mark(b, "hand")
        model = self.model(a, b)
        self.assertEqual(len(model.remove()), 2)
        self.assertEqual(self.cmds.rigJointMarkup(a, b, query=True), ["", ""])
        self.cmds.undo()
        self.assertEqual([self.read(j)["usage"] for j in (a, b)], ["arm", "hand"])

    def test_remove_with_nothing_marked_says_so(self):
        [a] = self.joints("a_00_M_JNT")
        with self.assertRaisesRegex(RuntimeError, "has markup"):
            self.model(a).remove()

    def test_joints_that_share_a_side_and_usage_are_a_warning(self):
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        self.mark(a, "arm")
        self.mark(b, "arm")
        warnings = self.model(a).warnings
        self.assertEqual(len(warnings), 1)
        self.assertIn("2 joints share side Center and usage 'arm'", warnings[0])

    def test_the_usages_in_the_scene_are_the_suggestions(self):
        a, b, c = self.joints("a_00_M_JNT", "b_00_M_JNT", "c_00_M_JNT")
        self.mark(a, "spine")
        self.mark(b, "arm")
        self.assertEqual(self.model(a).usages, ["arm", "spine"])
        self.assertEqual(c, self.cmds.ls(c)[0])

    def test_a_huge_selection_is_not_read(self):
        import bmaya.maya.markupmodel
        a, b = self.joints("a_00_M_JNT", "b_00_M_JNT")
        with mock.patch.object(bmaya.maya.markupmodel, "MAX_SELECTED", 1):
            model = self.model(a, b)
        self.assertEqual((model.joints, "Select fewer" in model.summary), ([], True))

    def test_rig_controls_are_listed_with_their_markup_and_never_edited(self):
        self.make_buildable_hero()
        session = self.session(HERO)
        session.files.build_rig()
        controls = self.cmds.ls(type="rigControlNode", long=True)
        control = controls[0]
        self.cmds.select(controls, replace=True)
        session.markup.set_active(True)
        listed = session.markup.controls
        self.assertEqual(session.markup.controls_selected, len(controls))
        self.assertEqual({entry.module_type for entry in listed}, {"Layout", "FkChain"})
        self.assertTrue(all(entry.usage and entry.side == "Center" for entry in listed))
        self.assertEqual(session.markup.summary, f"{len(controls)} rig control(s)")
        before = self.cmds.getAttr(control + ".controlMarkup")
        with self.assertRaises(RuntimeError):
            session.markup.set_field("usage", "x")   # no joint is selected
        self.assertEqual(self.cmds.getAttr(control + ".controlMarkup"), before)

    def test_joints_and_controls_selected_together_are_both_shown(self):
        self.make_buildable_hero()
        session = self.session(HERO)
        session.files.build_rig()
        control = self.cmds.ls(type="rigControlNode", long=True)[0]
        [joint] = self.joints("loose_00_M_JNT")
        self.cmds.select([control, joint], replace=True)
        session.markup.set_active(True)
        self.assertEqual(session.markup.summary, "1 joint(s): 0 marked, 1 not, 1 rig control(s)")

    def test_mirror_joints_copies_markup_to_the_other_side(self):
        [a] = self.joints("arm_00_L_JNT")
        self.cmds.xform(a, worldSpace=True, translation=(3, 5, 0))
        self.mark(a, "arm", "Left")
        self.model(a).mirror_joints()
        self.assertTrue(self.cmds.objExists("arm_00_R_JNT"))
        self.assertEqual(self.read("arm_00_R_JNT")["side"], "Right")

    def test_mirror_joints_with_no_joint_selected_says_so(self):
        with self.assertRaisesRegex(RuntimeError, "Select joints"):
            self.model().mirror_joints()

    def test_add_twist_joints_asks_for_the_settings_and_adds_marked_joints(self):
        start, end = self.joints("start_00_L_JNT", "end_00_L_JNT")
        self.cmds.xform(end, worldSpace=True, translation=(0, 10, 0))
        self.mark(start, "upperArm", "Left")
        self.mark(end, "lowerArm", "Left")
        model = self.model(start, end)
        created = model.add_twist_joints(self.answers(self.tools.TwistJointSettings(name="twist", count=3)))
        self.assertEqual(len(created), 3)
        self.assertEqual(sorted(self.read(j)["usage"] for j in created), ["twist_00", "twist_01", "twist_02"])


MIRROR_TEMPLATE = {
    "rigVersion": 1,
    "rigTemplateName": "AssetEditorMirrorTest",
    "rigName": "game",
    "rigAuthor": "tests",
    "rigModules": [
        {"moduleType": "FkChain", "name": "spine_00_M_MOD", "shapeType": "Box",
         "moduleArgs": {"joints": [["Center", "spine1"], ["Center", "spine2"]]}},
        {"moduleType": "FkChain", "name": "arm_00_L_MOD", "side": "Left", "shapeType": "Circle", "mirror": True,
         "moduleArgs": {"joints": [["Left", "arm"]]}, "parentStructure": {"start": "spine_00_M_MOD.end"}},
    ],
}


class Shapes(EditorBase):

    IDENTITY = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)

    def rig_controls(self):
        """A built hero and its rig controls, selected, with the shapes tab active."""
        self.make_buildable_hero()
        session = self.session(HERO)
        session.files.build_rig()
        controls = self.cmds.ls(type="rigControlNode", long=True)
        self.assertGreaterEqual(len(controls), 2)
        for control in controls:
            self.set_matrix(control, self.IDENTITY)
        self.cmds.select(controls, replace=True)
        session.shapes.set_active(True)
        return session, controls

    def set_matrix(self, control, matrix):
        self.cmds.setAttr(control + ".shapeTransform", *matrix, type="matrix")

    def matrix(self, control):
        return self.cmds.getAttr(control + ".shapeTransform")

    def assertMatrix(self, control, expected):
        actual = self.matrix(control)
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=6, msg=f"{control}: {actual} != {expected}")

    def test_with_no_selection_it_says_what_to_select(self):
        session = self.session(HERO)
        session.shapes.set_active(True)
        self.assertEqual((session.shapes.summary, session.shapes.fields), ("Select rig controls.", {}))

    def test_an_inactive_model_does_not_read_the_selection(self):
        self.make_buildable_hero()
        session = self.session(HERO)
        session.files.build_rig()
        session.watch_selection(True)
        self.cmds.select(self.cmds.ls(type="rigControlNode", long=True), replace=True)
        self.assertEqual(session.shapes.controls, [])
        session.shapes.set_active(True)
        self.assertTrue(session.shapes.controls)
        self.cmds.select(clear=True)
        self.assertEqual(session.shapes.controls, [])

    def test_the_fields_show_the_shape_the_controls_have(self):
        session, controls = self.rig_controls()
        names = session.shapes.enum_names
        self.assertEqual(names[0], "Box")
        shapes = {names[self.cmds.getAttr(c + ".shapeType")] for c in controls}
        fields = session.shapes.fields
        self.assertEqual(fields["shapeType"].mixed, len(shapes) > 1)
        self.assertEqual(fields["scale"].value, 1.0)
        self.assertEqual((fields["translateX"].value, fields["rotateZ"].value, fields["scaleY"].value), (0.0, 0.0, 1.0))
        self.assertEqual(fields["wireframeAlpha"].value, 1.0)
        self.assertEqual(fields["filled"].value, False)

    def test_a_field_the_controls_differ_on_is_mixed(self):
        session, controls = self.rig_controls()
        self.set_matrix(controls[0], (2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 5, 0, 1))
        self.cmds.setAttr(controls[0] + ".filled", True)
        session.shapes.refresh()
        fields = session.shapes.fields
        self.assertEqual([fields[name].mixed for name in ("scale", "translateY", "filled")], [True, True, True])
        self.assertEqual(fields["translateX"].value, 0.0)

    def test_a_non_uniform_scale_has_no_uniform_value(self):
        session, controls = self.rig_controls()
        for control in controls:
            self.set_matrix(control, (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 3, 0, 0, 0, 0, 1))
        session.shapes.refresh()
        fields = session.shapes.fields
        self.assertEqual((fields["scale"].mixed, fields["scaleY"].value, fields["scaleZ"].value), (True, 2.0, 3.0))

    def test_set_the_filled_box_on_every_control_in_one_undo_step(self):
        self.cmds.undoInfo(state=True, infinity=True)
        session, controls = self.rig_controls()
        session.shapes.set_field("filled", True)
        self.assertEqual([self.cmds.getAttr(c + ".filled") for c in controls], [True] * len(controls))
        self.assertEqual(session.shapes.fields["filled"].value, True)
        self.cmds.undo()
        self.assertEqual([self.cmds.getAttr(c + ".filled") for c in controls], [False] * len(controls))

    def test_set_the_shape_type_by_name(self):
        session, controls = self.rig_controls()
        session.shapes.set_field("shapeType", "Sphere")
        self.assertEqual({self.cmds.getAttr(c + ".shapeType", asString=True) for c in controls}, {"Sphere"})
        self.assertEqual(session.shapes.fields["shapeType"].value, "Sphere")

    def test_an_unknown_shape_changes_nothing_and_lists_the_shapes(self):
        session, controls = self.rig_controls()
        before = [self.cmds.getAttr(c + ".shapeType") for c in controls]
        with self.assertRaisesRegex(RuntimeError, "'Hexagon' is not a shape.*Box.*Sphere"):
            session.shapes.set_field("shapeType", "Hexagon")
        self.assertEqual([self.cmds.getAttr(c + ".shapeType") for c in controls], before)

    def test_set_the_alpha_and_adjust_it_within_zero_and_one(self):
        session, controls = self.rig_controls()
        session.shapes.set_field("wireframeAlpha", 0.5)
        self.assertEqual({self.cmds.getAttr(c + ".wireframeAlpha") for c in controls}, {0.5})
        session.shapes.set_field("wireframeAlpha", 0.25, "adjust")
        self.assertAlmostEqual(self.cmds.getAttr(controls[0] + ".wireframeAlpha"), 0.75)
        session.shapes.set_field("wireframeAlpha", 5, "adjust")
        self.assertEqual(self.cmds.getAttr(controls[0] + ".wireframeAlpha"), 1.0)
        session.shapes.set_field("wireframeAlpha", -5, "adjust")
        self.assertEqual(self.cmds.getAttr(controls[0] + ".wireframeAlpha"), 0.0)

    def test_set_translate_gives_every_control_the_value(self):
        session, controls = self.rig_controls()
        self.set_matrix(controls[0], (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 3, 0, 0, 1))
        session.shapes.refresh()
        session.shapes.set_field("translateY", 2.0)
        self.assertMatrix(controls[0], (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 3, 2, 0, 1))
        self.assertMatrix(controls[1], (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 2, 0, 1))

    def test_adjust_translate_adds_to_each_controls_own_value(self):
        session, controls = self.rig_controls()
        self.set_matrix(controls[0], (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 3, 0, 0, 1))
        session.shapes.refresh()
        session.shapes.set_field("translateX", 1.5, "adjust")
        self.assertMatrix(controls[0], (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 4.5, 0, 0, 1))
        self.assertMatrix(controls[1], (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1.5, 0, 0, 1))

    def test_set_the_uniform_scale_sets_all_three_axes(self):
        session, controls = self.rig_controls()
        self.set_matrix(controls[0], (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 3, 0, 0, 1, 0, 1))
        session.shapes.refresh()
        session.shapes.set_field("scale", 2.0)
        self.assertMatrix(controls[0], (2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 1, 0, 1))
        self.assertEqual(session.shapes.fields["scale"].value, 2.0)

    def test_adjust_scale_multiplies_each_controls_own_scale(self):
        session, controls = self.rig_controls()
        self.set_matrix(controls[0], (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 3, 0, 0, 1, 0, 1))
        session.shapes.refresh()
        session.shapes.set_field("scale", 1.5, "adjust")
        self.assertMatrix(controls[0], (1.5, 0, 0, 0, 0, 3, 0, 0, 0, 0, 4.5, 0, 0, 1, 0, 1))
        self.assertMatrix(controls[1], (1.5, 0, 0, 0, 0, 1.5, 0, 0, 0, 0, 1.5, 0, 0, 0, 0, 1))

    def test_one_axis_of_scale_leaves_the_others(self):
        session, controls = self.rig_controls()
        session.shapes.set_field("scaleX", 4.0)
        self.assertMatrix(controls[0], (4, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))

    def test_a_negative_scale_flips_the_shape(self):
        session, controls = self.rig_controls()
        session.shapes.set_field("scaleX", -1.0)
        self.assertMatrix(controls[0], (-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))

    def test_rotate_sets_and_adjusts_in_degrees(self):
        session, controls = self.rig_controls()
        session.shapes.set_field("rotateZ", 90.0)
        self.assertMatrix(controls[0], (0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))
        session.shapes.set_field("rotateZ", 90.0, "adjust")
        self.assertMatrix(controls[0], (-1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1))

    def test_a_scale_edit_keeps_the_rotation_and_the_translation(self):
        session, controls = self.rig_controls()
        session.shapes.set_field("rotateX", 90.0)
        session.shapes.set_field("translateZ", 7.0)
        session.shapes.set_field("scale", 2.0)
        self.assertMatrix(controls[0], (2, 0, 0, 0, 0, 0, 2, 0, 0, -2, 0, 0, 0, 0, 7, 1))

    def test_a_scale_of_zero_a_word_and_an_unknown_field_are_refused_and_change_nothing(self):
        session, controls = self.rig_controls()
        with self.assertRaisesRegex(RuntimeError, "scale of 0"):
            session.shapes.set_field("scaleY", 0)
        with self.assertRaisesRegex(RuntimeError, "needs a number"):
            session.shapes.set_field("translateX", "far")
        with self.assertRaisesRegex(RuntimeError, "not a shape field"):
            session.shapes.set_field("colour", 1.0)
        with self.assertRaisesRegex(RuntimeError, "mode must be"):
            session.shapes.set_field("scale", 2.0, "double")
        for control in controls:
            self.assertMatrix(control, self.IDENTITY)

    def test_an_edit_with_no_controls_selected_says_so(self):
        session = self.session(HERO)
        session.shapes.set_active(True)
        with self.assertRaisesRegex(RuntimeError, "Select rig controls"):
            session.shapes.set_field("filled", True)

    def test_a_scale_edit_is_one_undo_step(self):
        self.cmds.undoInfo(state=True, infinity=True)
        session, controls = self.rig_controls()
        session.shapes.set_field("scale", 3.0)
        self.cmds.undo()
        for control in controls:
            self.assertMatrix(control, self.IDENTITY)

    def test_a_huge_selection_is_not_read(self):
        import bmaya.maya.shapemodel
        session, controls = self.rig_controls()
        with mock.patch.object(bmaya.maya.shapemodel, "MAX_CONTROLS", 1):
            session.shapes.refresh()
        self.assertEqual((session.shapes.controls, "Select fewer" in session.shapes.summary), ([], True))

    def build_mirror_rig(self):
        """A rig with a Left arm and its mirror, built from MIRROR_TEMPLATE, and the session on it."""
        cmds = self.cmds
        path = os.path.join(self.temp, "mirror_template.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(MIRROR_TEMPLATE, handle)
        self.tools.new_rig(HERO, path, "game")
        cmds.select(clear=True)
        spine = []
        for i in range(2):
            joint = cmds.joint(name=f"spine_{i:02d}_M_JNT", position=(0, 10 + 2 * i, 0))
            cmds.rigJointMarkup(joint, usage=f"spine{i + 1}", side="Center", export=True, skin=True)
            spine.append(joint)
        for side, x in (("L", 2), ("R", -2)):
            cmds.select(spine[1], replace=True)
            joint = cmds.joint(name=f"arm_00_{side}_JNT", position=(x, 12, 0))
            cmds.rigJointMarkup(joint, usage="arm", side="Left" if side == "L" else "Right", export=True, skin=True)
        cmds.select(clear=True)
        self.tools.save_skeleton(HERO, joints=cmds.ls(type="joint", long=True))
        cmds.file(new=True, force=True)
        session = self.session(HERO)
        session.files.build_rig()
        by_side = {}
        for control in cmds.ls(type="rigControlNode", long=True):
            info = self.query_control(control)
            by_side[(info.side, info.usage)] = control
        return session, by_side

    def query_control(self, control):
        import rigmodules.query
        return rigmodules.query.get_control(control)

    def test_mirror_left_to_right_copies_the_left_shapes_onto_the_right(self):
        session, controls = self.build_mirror_rig()
        left, right = controls[("Left", "arm")], controls[("Right", "arm")]
        self.set_matrix(left, (2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 1, 0, 0, 1))
        self.cmds.setAttr(left + ".filled", True)
        self.cmds.select(left, replace=True)
        session.shapes.set_active(True)
        session.shapes.mirror(True)
        self.assertTrue(self.cmds.getAttr(right + ".filled"))
        scale = [abs(v) for v in self.matrix(right)[0:12:5]]
        self.assertAlmostEqual(scale[0], 2.0, places=6)

    def test_mirror_right_to_left_goes_the_other_way_in_one_undo_step(self):
        self.cmds.undoInfo(state=True, infinity=True)
        session, controls = self.build_mirror_rig()
        left, right = controls[("Left", "arm")], controls[("Right", "arm")]
        self.cmds.setAttr(right + ".filled", True)
        self.cmds.select(right, replace=True)
        session.shapes.set_active(True)
        session.shapes.mirror(False)
        self.assertTrue(self.cmds.getAttr(left + ".filled"))
        self.cmds.undo()
        self.assertFalse(self.cmds.getAttr(left + ".filled"))

    def test_mirror_with_nothing_selected_uses_the_given_rig_and_otherwise_asks_for_controls(self):
        session, controls = self.build_mirror_rig()
        left, right = controls[("Left", "arm")], controls[("Right", "arm")]
        self.cmds.setAttr(left + ".filled", True)
        self.cmds.select(clear=True)
        session.shapes.set_active(True)
        with self.assertRaisesRegex(RuntimeError, "Select rig controls"):
            session.shapes.mirror(True)
        session.shapes.mirror(True, session.files.rig_root)
        self.assertTrue(self.cmds.getAttr(right + ".filled"))


if __name__ == "__main__":
    unittest.main()
