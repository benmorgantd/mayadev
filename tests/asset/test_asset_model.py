"""bmaya.core.asset in plain Python: ids, projects, assets, the registry, publishes, local versions, source
control calls and handler dispatch.

Run with tests/asset/run.bat, or: python -m unittest discover -s tests/asset -p "test_asset_*.py"
"""

import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.core.asset import Asset, AssetError, AssetIdError, Project, ProjectError, Registry  # noqa: E402
from bmaya.core.asset import assetid, handlers, publishes, sourcecontrol, versions  # noqa: E402
from bmaya.core.asset.project import (  # noqa: E402
    DEFAULT_PROJECT, FORMAT_VERSION, PROJECTS_ROOT_ENV, projects_root, update_project_data, write_json)

HERO = "shooter\\main\\characters\\hero"


class RecordingSourceControl(sourcecontrol.SourceControl):
    def __init__(self):
        self.calls = []

    def checkout(self, path):
        self.calls.append(("checkout", path))

    def add(self, path):
        self.calls.append(("add", path))


class TempRoot(unittest.TestCase):
    """A projects root with one project, shooter\\main, using the default project.json. Local versions go
    to a temporary folder, and source control calls are recorded."""

    def setUp(self):
        temp = tempfile.mkdtemp(prefix="bmaya_asset_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.root = os.path.join(temp, "projects")
        self.versions_dir = os.path.join(temp, "local_versions")
        patcher = mock.patch.dict(os.environ, {versions.VERSIONS_DIR_ENV: self.versions_dir})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.source_control = RecordingSourceControl()
        sourcecontrol.set_current(self.source_control)
        self.addCleanup(sourcecontrol.set_current, sourcecontrol.SourceControl())
        self.project = Project.create(os.path.join(self.root, "shooter", "main"))

    def create(self, asset_id=HERO, asset_type="Character", variants=(), **kwargs):
        asset = Asset.create(asset_id, asset_type, root=self.root, **kwargs)
        for variant in variants:
            self.add_variant(asset, variant)
        return asset

    def add_variant(self, asset, variant):
        self.write(asset.path("template", variant), "{}")

    def registry(self):
        return Registry(self.project, root=self.root)

    def write(self, path, text="x"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()


class AssetIds(unittest.TestCase):

    def test_valid_ids_any_depth(self):
        for asset_id in ["hero", "shooter\\hero", HERO, "a_1\\b2\\c"]:
            self.assertTrue(assetid.is_valid(asset_id), asset_id)

    def test_invalid_ids(self):
        for asset_id in ["", "\\hero", "hero\\", "a\\\\b", "shooter/hero", "shooter|hero", "main chars\\hero", "hero\n", "h-ero", None, 5,
                         "Hero", "shooter\\Main\\hero", HERO.upper()]:
            self.assertFalse(assetid.is_valid(asset_id), repr(asset_id))
        with self.assertRaises(AssetIdError):
            assetid.check("a\\\\b")

    def test_name_is_the_last_token(self):
        self.assertEqual(assetid.name(HERO), "hero")
        self.assertEqual(assetid.name("hero"), "hero")

    def test_uppercase_is_rejected_not_converted(self):
        # Ids are lowercase only (RigModules D54), so two ids never differ only in case and == compares them.
        for token in ("Hero", "HERO", "hEro"):
            self.assertFalse(assetid.is_valid_token(token), token)
        with self.assertRaises(AssetIdError) as raised:
            assetid.check("shooter\\Main\\hero")
        self.assertIn("lowercase", str(raised.exception))
        self.assertFalse(hasattr(assetid, "equals"))
        self.assertFalse(hasattr(assetid, "key"))

    def test_relative_path_round_trip(self):
        relative = assetid.to_relative_path(HERO)
        self.assertEqual(relative, os.path.join("shooter", "main", "characters", "hero"))
        self.assertEqual(assetid.from_relative_path(relative), HERO)
        with self.assertRaises(AssetIdError):
            assetid.from_relative_path(os.path.join("..", "outside"))


class Projects(TempRoot):

    def test_create_writes_the_default_project_with_sorted_keys(self):
        path = os.path.join(self.project.root, "project.json")
        self.assertEqual(json.loads(self.read(path)), DEFAULT_PROJECT)
        self.assertEqual(self.read(path), json.dumps(DEFAULT_PROJECT, indent=2, sort_keys=True) + "\n")
        self.assertIn("Character", self.project.asset_types)
        with self.assertRaises(ProjectError):
            Project.create(self.project.root)

    def test_find_walks_up_from_a_path_that_need_not_exist(self):
        found = Project.find(os.path.join(self.project.root, "characters", "hero", "variants", "game"))
        self.assertEqual(found.root, self.project.root)
        with self.assertRaises(ProjectError):
            Project.find(os.path.join(self.root, "elsewhere"))

    def test_nearest_project_wins(self):
        inner = Project.create(os.path.join(self.project.root, "dlc"))
        self.assertEqual(Project.find(os.path.join(inner.root, "props", "crate")).root, inner.root)

    def test_bad_format_version_fails(self):
        root = os.path.join(self.root, "old")
        self.write(os.path.join(root, "project.json"), json.dumps({"formatVersion": 0}))
        with self.assertRaises(ProjectError):
            Project(root)

    def old_project(self, data: dict) -> str:
        """Writes a project.json by hand, as an older mayadev would have, and returns its folder."""
        root = os.path.join(self.root, "old")
        self.write(os.path.join(root, "project.json"), json.dumps(data))
        return root

    def test_a_version_1_project_without_the_library_folders_is_updated_and_written_back(self):
        old = {"formatVersion": 1, "assetTypes": ["Prop"], "fileTypes": {
            "poses": {"folder": True, "path": "poses"}, "shapes": {"path": "shapes.json"}}}
        root = self.old_project(old)
        project = Project(root)
        for key in ("controlposes", "controlanims", "exports", "sources"):
            self.assertEqual(project.file_type(key).relative_path("hero"), key)
            self.assertTrue(project.file_type(key).folder)
        self.assertEqual(project.rig_regions, ["lowerBody", "upperBody", "head", "hands"])
        self.assertEqual(project.library_statuses, ["scratch", "review", "final"])
        saved = json.loads(self.read(os.path.join(root, "project.json")))
        self.assertEqual(saved["formatVersion"], FORMAT_VERSION)
        self.assertIn("controlposes", saved["fileTypes"])
        self.assertEqual(saved["fileTypes"]["poses"], old["fileTypes"]["poses"], "a file type that isn't a default stays")

    def test_an_update_never_replaces_what_a_studio_edited(self):
        root = self.old_project({
            "formatVersion": 1, "assetTypes": ["Prop"], "rig": {"regions": ["face"]}, "library": {"statuses": ["wip"]},
            "fileTypes": {"controlposes": {"folder": True, "path": "library/poses"}}})
        project = Project(root)
        self.assertEqual(project.file_type("controlposes").relative_path("hero"), os.path.join("library", "poses"))
        self.assertEqual((project.rig_regions, project.library_statuses), (["face"], ["wip"]))

    def test_a_current_project_is_not_rewritten(self):
        path = os.path.join(self.project.root, "project.json")
        os.utime(path, (1, 1))
        Project(self.project.root)
        self.assertEqual(os.path.getmtime(path), 1)

    def test_a_project_that_cannot_be_written_back_still_loads_updated(self):
        root = self.old_project({"formatVersion": 1, "assetTypes": ["Prop"], "fileTypes": {}})
        with mock.patch("bmaya.core.asset.project.write_json", side_effect=PermissionError("read-only")):
            project = Project(root)
        self.assertIn("controlposes", project.file_types)
        self.assertEqual(json.loads(self.read(os.path.join(root, "project.json")))["formatVersion"], 1)

    def test_a_failed_write_leaves_no_temp_file(self):
        path = os.path.join(self.root, "x.json")
        with self.assertRaises(TypeError):
            write_json(path, {"bad": object()})
        self.assertEqual(os.listdir(self.root).count("x.json.tmp"), 0)

    def test_bad_and_newer_versions_name_the_file(self):
        for version in (0, "1", True, None, FORMAT_VERSION + 1):
            root = self.old_project({"formatVersion": version})
            with self.assertRaises(ProjectError, msg=repr(version)) as raised:
                Project(root)
            self.assertIn("project.json", str(raised.exception))
        self.assertIn("newer mayadev", str(raised.exception))

    def test_update_project_data_reports_whether_it_changed_anything(self):
        data = {"formatVersion": FORMAT_VERSION}
        self.assertFalse(update_project_data(data))
        self.assertTrue(update_project_data({"formatVersion": 1}))

    def test_file_type_paths(self):
        shapes = self.project.file_type("shapes")
        self.assertTrue(shapes.per_variant)
        self.assertEqual(shapes.relative_path("hero", "game"), os.path.join("variants", "game", "shapes.json"))
        self.assertEqual(self.project.file_type("skeleton").relative_path("hero"),
                         os.path.join("skeleton", "hero_skeleton.ma"))
        self.assertEqual(self.project.file_type("rig").relative_path("hero", "game"),
                         os.path.join("variants", "game", "hero_game_rig.ma"))
        self.assertEqual(self.project.file_type("template").variant_parent(), "variants")
        with self.assertRaises(ProjectError):
            self.project.file_type("skeleton").variant_parent()

    def test_variant_rules(self):
        with self.assertRaises(ProjectError):
            self.project.file_type("shapes").relative_path("hero")            # per variant, none given
        with self.assertRaises(ProjectError):
            self.project.file_type("skeleton").relative_path("hero", "game")  # asset level, variant given
        with self.assertRaises(ProjectError):
            self.project.file_type("shapes").relative_path("hero", "bad/variant")
        with self.assertRaises(ProjectError):
            self.project.file_type("nope")

    def test_asset_type_check(self):
        self.assertEqual(self.project.check_asset_type("Prop"), "Prop")
        with self.assertRaises(ProjectError):
            self.project.check_asset_type("prop")

    def test_projects_root_comes_from_the_environment(self):
        with mock.patch.dict(os.environ, {PROJECTS_ROOT_ENV: self.root}):
            self.assertEqual(projects_root(), os.path.normpath(self.root))
            self.assertEqual(Asset(HERO).folder, os.path.join(self.root, "shooter", "main", "characters", "hero"))
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ProjectError):
                projects_root()


class Assets(TempRoot):

    def test_create_writes_only_identity(self):
        hero = self.create(skeleton="shooter\\main\\skeletons\\biped")
        self.assertTrue(hero.exists())
        self.assertEqual(json.loads(self.read(hero.info_path)),
                         {"formatVersion": 1, "assetType": "Character", "skeleton": "shooter\\main\\skeletons\\biped"})
        self.assertEqual(hero.project.root, self.project.root)
        self.assertEqual(self.source_control.calls, [("add", hero.info_path)])

    def test_create_checks(self):
        self.create()
        with self.assertRaises(AssetError):
            self.create()                                                    # already exists
        with self.assertRaises(ProjectError):
            self.create("shooter\\main\\props\\crate", asset_type="Crate")      # not a project asset type
        with self.assertRaises(ProjectError):
            Asset.create("loose\\crate", "Prop", root=self.root)              # no project.json above
        with self.assertRaises(AssetIdError):
            self.create("shooter\\main\\props\\crate", skeleton="bad\\\\id")

    def test_assets_never_nest(self):
        self.create()
        with self.assertRaises(AssetError):
            self.create(HERO + "\\sword", asset_type="Weapon")
        self.create("shooter\\main\\props\\crate\\lid", asset_type="Prop")
        with self.assertRaises(AssetError):
            self.create("shooter\\main\\props\\crate", asset_type="Prop")
        with self.assertRaises(AssetError):
            self.create("shooter\\main", asset_type="Prop")                    # the project folder itself

    def test_paths_never_touch_the_disk(self):
        hero = Asset(HERO, root=self.root)
        path = hero.path("shapes", variant="game")
        self.assertEqual(path, os.path.join(hero.folder, "variants", "game", "shapes.json"))
        self.assertFalse(os.path.exists(hero.folder))
        self.assertFalse(hero.file_exists("shapes", "game"))

    def test_info_of_a_missing_asset_fails(self):
        with self.assertRaises(AssetError):
            Asset(HERO, root=self.root).info

    def test_from_path_finds_the_enclosing_asset(self):
        hero = self.create()
        inside = os.path.join(hero.folder, "variants", "game", "weights", "body.json")
        self.assertEqual(Asset.from_path(inside, root=self.root), hero)
        with self.assertRaises(AssetError):
            Asset.from_path(os.path.join(self.project.root, "props"), root=self.root)

    def test_skeleton_defaults_to_the_asset_itself(self):
        self.assertEqual(self.create().skeleton, HERO)
        villain = self.create("shooter\\main\\characters\\villain", skeleton=HERO)
        self.assertEqual(villain.skeleton, HERO)

    def test_variants_are_folders_with_a_template(self):
        hero = self.create()
        self.assertEqual(hero.variants, [])
        self.add_variant(hero, "game")
        self.add_variant(hero, "cine")
        os.makedirs(os.path.join(hero.folder, "variants", "scratch"))     # no template: not a variant
        self.assertEqual(hero.variants, ["cine", "game"])
        self.assertNotIn("rigs", hero.info, "adding a variant edits nothing")


class Publishes(TempRoot):

    def setUp(self):
        super().setUp()
        self.hero = self.create(variants=["game"])

    def test_ids_sort_in_time_order(self):
        early = publishes.make_id("bmorgan", datetime.datetime(2026, 11, 8, 9, 5, 1, tzinfo=datetime.timezone.utc))
        late = publishes.make_id("alice", datetime.datetime(2026, 11, 8, 14, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(early, "20261108T090501Z_bmorgan")
        self.assertLess(early, late)
        self.assertEqual(publishes.make_id("Ben Morgan.2", datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)),
                         "20260101T000000Z_Ben_Morgan_2")

    def test_create_adds_a_folder_and_edits_nothing(self):
        before = self.read(self.hero.info_path)
        folder = publishes.create(self.hero, "game", {"pluginVersion": "0.1"}, user="bmorgan")
        publish_id = os.path.basename(folder)
        self.assertEqual(self.read(self.hero.info_path), before)
        self.assertEqual(publishes.latest(self.hero, "game"), publish_id)
        record = publishes.info(self.hero, "game", publish_id)
        self.assertEqual(record, {"formatVersion": 1, "id": publish_id, "user": "bmorgan", "pluginVersion": "0.1"})
        self.assertIn(("add", os.path.join(folder, "publish.json")), self.source_control.calls)

    def test_latest_is_the_newest_id(self):
        base = self.hero.path("publish", "game")
        for publish_id in ("20261108T090000Z_bmorgan", "20261109T080000Z_alice", "20261108T120000Z_alice"):
            self.write(os.path.join(base, publish_id, "publish.json"), "{}")
        os.makedirs(os.path.join(base, "not_a_publish"))
        os.makedirs(os.path.join(base, "20261110T000000Z_halfwritten"))   # no publish.json yet
        self.assertEqual(publishes.list_ids(self.hero, "game"),
                         ["20261108T090000Z_bmorgan", "20261108T120000Z_alice", "20261109T080000Z_alice"])
        self.assertEqual(publishes.latest(self.hero, "game"), "20261109T080000Z_alice")

    def test_create_checks(self):
        self.assertIsNone(publishes.latest(self.hero, "game"))
        with self.assertRaises(AssetError):
            publishes.create(self.hero, "cine")        # not a variant
        fixed = datetime.datetime(2026, 11, 8, tzinfo=datetime.timezone.utc)
        with mock.patch.object(publishes, "make_id", return_value=publishes.make_id("bmorgan", fixed)):
            publishes.create(self.hero, "game")
            with self.assertRaises(AssetError):
                publishes.create(self.hero, "game")    # same second, same user


class Registries(TempRoot):

    def test_writes_nothing(self):
        self.create(variants=["game"])
        self.registry().refresh()
        written = [name for _, _, files in os.walk(self.root) for name in files]
        self.assertEqual(sorted(written), ["asset.json", "project.json", "template.json"])

    def test_scan_finds_assets_at_any_depth(self):
        self.create()
        self.create("shooter\\main\\props\\crate", asset_type="Prop")
        self.create("shooter\\main\\env\\forest\\rocks\\boulder", asset_type="Environment")
        registry = self.registry()
        self.assertEqual(registry.ids(), ["shooter\\main\\characters\\hero", "shooter\\main\\env\\forest\\rocks\\boulder",
                                          "shooter\\main\\props\\crate"])
        self.assertEqual(registry.errors, [])

    def test_entries(self):
        hero = self.create(variants=["game", "cine"])
        folder = publishes.create(hero, "game", user="bmorgan")
        entry = self.registry().get(HERO)
        self.assertEqual(entry, {"assetType": "Character", "skeleton": HERO, "variants": ["cine", "game"],
                                 "latestPublish": {"game": os.path.basename(folder)}})
        self.assertEqual(self.registry().latest_publish(HERO, "game"), os.path.basename(folder))
        self.assertIsNone(self.registry().latest_publish(HERO, "cine"))

    def test_find_by_type_and_skeleton(self):
        self.create("shooter\\main\\skeletons\\biped", asset_type="Skeleton")
        self.create(skeleton="shooter\\main\\skeletons\\biped")
        self.create("shooter\\main\\characters\\villain", skeleton="shooter\\main\\skeletons\\biped")
        self.create("shooter\\main\\characters\\dog")
        registry = self.registry()
        self.assertEqual(registry.find(asset_type="Character"),
                         ["shooter\\main\\characters\\dog", HERO, "shooter\\main\\characters\\villain"])
        self.assertEqual(registry.find(skeleton="shooter\\main\\skeletons\\biped"),
                         [HERO, "shooter\\main\\characters\\villain", "shooter\\main\\skeletons\\biped"])
        self.assertEqual(registry.find(asset_type="Character", skeleton="shooter\\main\\characters\\dog"),
                         ["shooter\\main\\characters\\dog"])

    def test_refresh_sees_changes_on_disk(self):
        registry = Registry.of(self.project, root=self.root)
        self.assertIs(Registry.of(self.project, root=self.root), registry, "one index per project per session")
        self.assertEqual(registry.ids(), [])
        self.create()
        self.assertEqual(registry.ids(), [], "the index changes only on refresh")
        self.assertEqual(registry.refresh().ids(), [HERO])

    def test_scan_skips_other_projects_and_stops_at_assets(self):
        hero = self.create()
        dlc = Project.create(os.path.join(self.project.root, "dlc"))
        Asset.create("shooter\\main\\dlc\\props\\crate", "Prop", root=self.root)
        # An asset.json inside an asset (made by hand) is not walked into.
        self.write(os.path.join(hero.folder, "sword", "asset.json"), json.dumps({"formatVersion": 1, "assetType": "Weapon"}))
        self.assertEqual(self.registry().ids(), [HERO])
        self.assertEqual(Registry(dlc, root=self.root).ids(), ["shooter\\main\\dlc\\props\\crate"])

    def test_scan_reports_unreadable_assets(self):
        self.create()
        self.write(os.path.join(self.project.root, "props", "broken", "asset.json"), "{not json")
        registry = self.registry()
        self.assertEqual(registry.ids(), [HERO])
        self.assertEqual(len(registry.errors), 1)

    def test_unknown_asset(self):
        self.assertIsNone(self.registry().get(HERO))
        with self.assertRaises(ProjectError):
            self.registry().latest_publish(HERO, "game")


class Versions(TempRoot):

    def path(self, name="shapes.json"):
        return os.path.join(self.root, "shooter", "main", "characters", "hero", name)

    def test_nothing_to_version(self):
        self.assertIsNone(versions.version(self.path("missing.json"), self.root))

    def test_copies_go_outside_the_workspace(self):
        self.write(self.path(), "one")
        copy = versions.version(self.path(), self.root)
        self.assertEqual(copy, os.path.join(self.versions_dir, "shooter", "main", "characters", "hero", "shapes.v001.json"))
        self.assertEqual(os.listdir(os.path.dirname(self.path())), ["shapes.json"])

    def test_numbers_count_up_from_the_highest(self):
        for text in ("one", "two", "three"):
            self.write(self.path(), text)
            versions.version(self.path(), self.root)
        found = versions.list_versions(self.path(), self.root)
        self.assertEqual([number for number, _ in found], [1, 2, 3])
        self.assertEqual(self.read(found[1][1]), "two")
        os.remove(found[1][1])
        self.assertTrue(versions.version(self.path(), self.root).endswith("shapes.v004.json"),
                        "a deleted number is never reused")

    def test_folders_are_copied_whole(self):
        folder = self.path("weights")
        self.write(os.path.join(folder, "body.json"), "w")
        copy = versions.version(folder, self.root)
        self.assertEqual(os.path.basename(copy), "weights.v001")
        self.assertEqual(self.read(os.path.join(copy, "body.json")), "w")

    def test_other_files_in_the_versions_folder_are_ignored(self):
        self.write(self.path())
        folder = versions.versions_folder(self.path(), self.root)
        self.write(os.path.join(folder, "shapes_old.json"))
        self.write(os.path.join(folder, "other.v009.json"))
        self.assertTrue(versions.version(self.path(), self.root).endswith("shapes.v001.json"))

    def test_default_root_is_local_app_data(self):
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\local"}):
            del os.environ[versions.VERSIONS_DIR_ENV]
            self.assertEqual(versions.versions_root(), os.path.join(r"C:\local", "bmaya", "versions"))

    def test_path_outside_the_root_fails(self):
        with self.assertRaises(ValueError):
            versions.versions_folder(os.path.join(os.path.dirname(self.root), "elsewhere", "x.json"), self.root)


class RecordingHandler(handlers.FileHandler):
    def __init__(self):
        self.calls = []

    def save(self, asset, path, **context):
        self.calls.append(("save", path, context))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(context.get("text", ""))

    def load(self, asset, path, **context):
        self.calls.append(("load", path, context))
        with open(path, encoding="utf-8") as handle:
            return handle.read()


class Handlers(TempRoot):

    def setUp(self):
        super().setUp()
        self.handler = RecordingHandler()
        handlers.register("shapes", self.handler)
        self.addCleanup(handlers.unregister, "shapes")
        self.hero = self.create(variants=["game"])
        self.source_control.calls.clear()

    def test_save_makes_folders_versions_and_tells_source_control(self):
        path = handlers.save(self.hero, "shapes", variant="game", text="first", rig_root="hero:rigRootModule1")
        self.assertEqual(path, self.hero.path("shapes", "game"))
        self.assertEqual(versions.list_versions(path, self.root), [])
        self.assertEqual(self.source_control.calls, [("add", path)])

        handlers.save(self.hero, "shapes", variant="game", text="second")
        self.assertEqual(self.read(path), "second")
        self.assertEqual(self.read(versions.list_versions(path, self.root)[0][1]), "first")
        self.assertEqual(self.source_control.calls, [("add", path), ("checkout", path)])
        self.assertEqual(self.handler.calls[0][2], {"variant": "game", "text": "first", "rig_root": "hero:rigRootModule1"})

    def test_load_returns_the_handler_result(self):
        handlers.save(self.hero, "shapes", variant="game", text="data")
        self.assertEqual(handlers.load(self.hero, "shapes", variant="game"), "data")

    def test_load_of_a_missing_file_fails(self):
        with self.assertRaises(FileNotFoundError):
            handlers.load(self.hero, "shapes", variant="game")

    def test_unregistered_and_base_handlers_raise(self):
        with self.assertRaises(NotImplementedError):
            handlers.save(self.hero, "weights", variant="game")
        handlers.register("postops", handlers.FileHandler())
        self.addCleanup(handlers.unregister, "postops")
        with self.assertRaises(NotImplementedError):
            handlers.save(self.hero, "postops", variant="game")


if __name__ == "__main__":
    unittest.main()
