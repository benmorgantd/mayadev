"""bmaya.core.asset.context and bmaya.core.asset.catalog in plain Python: the asset the Asset Editor works on, and the
list of assets it picks from (RigModules D61).

Run with tests/asset/run.bat, or: python -m unittest discover -s tests/asset -p "test_asset_*.py"
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.core.asset import Asset, AssetError, AssetIdError, Project, RigRef, SkeletonRef  # noqa: E402
from bmaya.core.asset import catalog, context as context_module  # noqa: E402
from bmaya.core.asset.context import AssetContext  # noqa: E402

HERO = "shooter\\main\\characters\\hero"
VILLAIN = "shooter\\main\\characters\\villain"
CRATE = "shooter\\main\\props\\crate"
OTHER = "puzzle\\levels\\props\\gem"


class ContextBase(unittest.TestCase):

    def setUp(self):
        temp = tempfile.mkdtemp(prefix="bmaya_asset_context_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.root = os.path.join(temp, "projects")
        patcher = mock.patch.dict(os.environ, {"RIGGING_PROJECT_DIR": self.root,
                                               "BMAYA_VERSIONS_DIR": os.path.join(temp, "versions")})
        patcher.start()
        self.addCleanup(patcher.stop)
        Project.create(os.path.join(self.root, "shooter", "main"))
        self.hero = Asset.create(HERO, "Character")
        self.addCleanup(self.stop_context)

    def stop_context(self):
        running = AssetContext.current()
        if running is not None:
            running.stop()

    def calls(self, context):
        calls = []
        context.changed.connect(lambda: calls.append(1))
        return calls


class Owners(ContextBase):

    def test_there_is_no_context_until_one_is_started(self):
        self.assertIsNone(AssetContext.current())
        context = AssetContext.start()
        self.assertIs(AssetContext.current(), context)
        self.assertIsNone(context.asset_id)

    def test_start_sets_the_asset(self):
        self.assertEqual(AssetContext.start(HERO).asset_id, HERO)

    def test_an_asset_with_no_parts_has_no_owners(self):
        context = AssetContext.start(HERO)
        self.assertEqual((context.skeleton, context.rig, context.look), (None, None, None))
        self.assertEqual((context.skeletons(), context.rigs(), context.looks()), ([], [], []))

    def test_set_asset_picks_default_first_for_a_skeleton_and_a_look_and_the_first_rig(self):
        self.hero.add_rig("body", SkeletonRef("biped"))
        self.hero.add_rig("face", SkeletonRef("biped"))
        self.hero.add_look("zeta", [SkeletonRef("biped")])
        self.hero.add_look("default", [SkeletonRef("biped")])
        for name in ("biped", "default"):
            os.makedirs(os.path.dirname(self.hero.path("skeleton", name)))
            open(self.hero.path("skeleton", name), "w").close()
        context = AssetContext.start(HERO)
        self.assertEqual((context.skeleton, context.rig, context.look), ("default", "body", "default"))
        self.assertEqual(context.rigs(), ["body", "face"])

    def test_owners_of_an_asset_with_no_folder_are_empty(self):
        context = AssetContext.start("shooter\\main\\characters\\nobody")
        self.assertEqual((context.skeletons(), context.rigs(), context.looks()), ([], [], []))

    def test_an_asset_outside_any_project_has_no_owners_and_raises_nothing(self):
        context = AssetContext.start("nowhere\\thing")
        self.assertEqual(context.rigs(), [])


class Changes(ContextBase):

    def test_set_asset_emits_once_and_the_same_asset_emits_nothing(self):
        context = AssetContext.start()
        calls = self.calls(context)
        context.set_asset(HERO)
        context.set_asset(HERO)
        self.assertEqual(len(calls), 1)

    def test_an_invalid_id_raises_and_changes_nothing(self):
        context = AssetContext.start(HERO)
        calls = self.calls(context)
        with self.assertRaises(AssetIdError):
            context.set_asset("Shooter\\Hero")
        self.assertEqual((context.asset_id, len(calls)), (HERO, 0))

    def test_changing_the_asset_resets_the_owners(self):
        self.hero.add_rig("body", SkeletonRef("default"))
        context = AssetContext.start(HERO)
        context.set_asset(CRATE)
        self.assertEqual((context.rig, context.skeleton, context.look), (None, None, None))

    def test_set_rig_to_one_the_asset_has(self):
        self.hero.add_rig("body", SkeletonRef("default"))
        self.hero.add_rig("face", SkeletonRef("default"), parent=RigRef("body"))
        context = AssetContext.start(HERO)
        calls = self.calls(context)
        context.set_rig("face")
        self.assertEqual((context.rig, len(calls)), ("face", 1))
        context.set_rig("face")
        self.assertEqual(len(calls), 1, "choosing the same rig emits nothing")

    def test_set_rig_to_one_the_asset_lacks_raises_and_names_what_it_has(self):
        self.hero.add_rig("body", SkeletonRef("default"))
        context = AssetContext.start(HERO)
        with self.assertRaisesRegex(AssetError, "no rig 'tail'.*body"):
            context.set_rig("tail")
        self.assertEqual(context.rig, "body")

    def test_refresh_picks_up_a_rig_added_on_disk_and_drops_one_that_is_gone(self):
        context = AssetContext.start(HERO)
        calls = self.calls(context)
        self.hero.add_rig("body", SkeletonRef("default"))
        context.refresh()
        self.assertEqual((context.rig, len(calls)), ("body", 1))
        context.refresh()
        self.assertEqual(len(calls), 1, "nothing changed, so nothing is emitted")
        shutil.rmtree(os.path.dirname(self.hero.path("riginfo", "body")))
        context.refresh()
        self.assertIsNone(context.rig)

    def test_a_scene_never_changes_it(self):
        # The context reads files and never the scene: it has no Maya import to follow one with.
        source = open(context_module.__file__, encoding="utf-8").read()
        self.assertNotIn("maya", source.replace("bmaya", ""))


class Stopping(ContextBase):

    def test_stop_clears_the_context_and_current_is_none(self):
        context = AssetContext.start(HERO)
        calls = self.calls(context)
        context.stop()
        self.assertEqual((context.asset_id, AssetContext.current(), len(calls)), (None, None, 1))

    def test_an_old_context_stopping_leaves_the_new_one_running(self):
        old = AssetContext.start(HERO)
        new = AssetContext.start(VILLAIN)
        old.stop()
        self.assertIs(AssetContext.current(), new)
        self.assertEqual(new.asset_id, VILLAIN)


class Catalog(ContextBase):

    def test_lists_the_assets_of_every_project_sorted(self):
        Asset.create(VILLAIN, "Character")
        Asset.create(CRATE, "Prop")
        Project.create(os.path.join(self.root, "puzzle", "levels"))
        Asset.create(OTHER, "Prop")
        self.assertEqual(catalog.asset_ids(), [OTHER, HERO, VILLAIN, CRATE])

    def test_project_folders_stop_at_a_project_and_skip_the_user_folder(self):
        os.makedirs(os.path.join(self.root, "user", "someone", "animlibrary"))
        Project.create(os.path.join(self.root, "user", "hidden"))
        self.assertEqual(catalog.project_folders(), [os.path.join(self.root, "shooter", "main")])

    def test_a_projects_root_that_is_not_a_folder_lists_nothing(self):
        self.assertEqual(catalog.asset_ids(os.path.join(self.root, "missing")), [])

    def test_an_unset_projects_root_raises_the_project_error(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("RIGGING_PROJECT_DIR")
            with self.assertRaises(Exception) as caught:
                catalog.asset_ids()
        self.assertIn("RIGGING_PROJECT_DIR", str(caught.exception))

    def test_exists(self):
        self.assertTrue(context_module.exists(HERO))
        self.assertFalse(context_module.exists(VILLAIN))
        self.assertFalse(context_module.exists("Not An Id"))


if __name__ == "__main__":
    unittest.main()
