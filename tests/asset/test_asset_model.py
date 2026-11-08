"""bmaya.asset in plain Python: ids, projects, assets, the registry, local versions and handler dispatch.

Run with tests/asset/run.bat, or: python -m unittest discover -s tests/asset -p "test_asset_*.py"
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.asset import Asset, AssetError, AssetIdError, Project, ProjectError, Registry, assetid, handlers, versions  # noqa: E402
from bmaya.asset.project import DEFAULT_PROJECT, PROJECTS_ROOT_ENV, projects_root  # noqa: E402

HERO = "shooter|main|characters|hero"


class TempRoot(unittest.TestCase):
    """A projects root with one project, shooter|main, using the default project.json."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bmaya_asset_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.project = Project.create(os.path.join(self.root, "shooter", "main"))

    def create(self, asset_id=HERO, asset_type="Character", **kwargs):
        return Asset.create(asset_id, asset_type, root=self.root, **kwargs)

    def write(self, path, text="x"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()


class AssetIds(unittest.TestCase):

    def test_valid_ids_any_depth(self):
        for asset_id in ["hero", "shooter|hero", HERO, "a_1|B2|c"]:
            self.assertTrue(assetid.is_valid(asset_id), asset_id)

    def test_invalid_ids(self):
        for asset_id in ["", "|hero", "hero|", "a||b", "shooter/hero", "main chars|hero", "hero\n", "h-ero", None, 5]:
            self.assertFalse(assetid.is_valid(asset_id), repr(asset_id))
        with self.assertRaises(AssetIdError):
            assetid.check("a||b")

    def test_name_is_the_last_token(self):
        self.assertEqual(assetid.name(HERO), "hero")
        self.assertEqual(assetid.name("hero"), "hero")

    def test_ids_compare_without_case(self):
        self.assertTrue(assetid.equals(HERO, HERO.upper()))
        self.assertFalse(assetid.equals(HERO, "shooter|main|characters|villain"))

    def test_relative_path_round_trip(self):
        relative = assetid.to_relative_path(HERO)
        self.assertEqual(relative, os.path.join("shooter", "main", "characters", "hero"))
        self.assertEqual(assetid.from_relative_path(relative), HERO)
        with self.assertRaises(AssetIdError):
            assetid.from_relative_path(os.path.join("..", "outside"))


class Projects(TempRoot):

    def test_create_writes_the_default_project(self):
        with open(os.path.join(self.project.root, "project.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), DEFAULT_PROJECT)
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

    def test_file_type_paths(self):
        shapes = self.project.file_type("shapes")
        self.assertTrue(shapes.per_variant)
        self.assertEqual(shapes.relative_path("hero", "game"), os.path.join("variants", "game", "shapes.json"))
        self.assertEqual(self.project.file_type("skeleton").relative_path("hero"),
                         os.path.join("skeleton", "hero_skeleton.ma"))

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

    def test_create_writes_asset_json_without_the_id(self):
        hero = self.create(rigs=["game", "cine"])
        self.assertTrue(hero.exists())
        self.assertEqual(json.loads(self.read(hero.info_path)),
                         {"formatVersion": 1, "assetType": "Character", "rigs": ["game", "cine"]})
        self.assertEqual(hero.rigs, ["game", "cine"])
        self.assertEqual(hero.project.root, self.project.root)

    def test_create_checks(self):
        self.create()
        with self.assertRaises(AssetError):
            self.create()                                                    # already exists
        with self.assertRaises(ProjectError):
            self.create("shooter|main|props|crate", asset_type="Crate")      # not a project asset type
        with self.assertRaises(ProjectError):
            Asset.create("loose|crate", "Prop", root=self.root)              # no project.json above
        with self.assertRaises(AssetError):
            self.create("shooter|main|props|crate", rigs=["game", "game"])
        with self.assertRaises(AssetIdError):
            self.create("shooter|main|props|crate", skeleton="bad||id")

    def test_assets_never_nest(self):
        self.create()
        with self.assertRaises(AssetError):
            self.create(HERO + "|sword", asset_type="Weapon")
        self.create("shooter|main|props|crate|lid", asset_type="Prop")
        with self.assertRaises(AssetError):
            self.create("shooter|main|props|crate", asset_type="Prop")
        with self.assertRaises(AssetError):
            self.create("shooter|main", asset_type="Prop")                    # the project folder itself

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
        villain = self.create("shooter|main|characters|villain", skeleton=HERO)
        self.assertEqual(villain.skeleton, HERO)

    def test_add_rig(self):
        hero = self.create(rigs=["game"])
        hero.add_rig("cine")
        self.assertEqual(hero.rigs, ["game", "cine"])
        with self.assertRaises(AssetError):
            hero.add_rig("game")

    def test_record_publish(self):
        hero = self.create(rigs=["game"])
        self.assertEqual(hero.latest_publish("game"), 0)
        hero.record_publish("game", 3)
        self.assertEqual(hero.latest_publish("game"), 3)
        with self.assertRaises(AssetError):
            hero.record_publish("game", 3)       # not newer
        with self.assertRaises(AssetError):
            hero.record_publish("cine", 1)       # no such variant


class Registries(TempRoot):

    def registry(self):
        return Registry(self.project, root=self.root)

    def test_writes_keep_the_registry_current(self):
        hero = self.create(rigs=["game"])
        self.assertEqual(self.registry().get(HERO)["rigs"], ["game"])
        hero.add_rig("cine")
        hero.record_publish("game", 2)
        entry = self.registry().get(HERO.upper())
        self.assertEqual(entry["rigs"], ["game", "cine"])
        self.assertEqual(self.registry().latest_publish(HERO, "game"), 2)
        self.assertEqual(self.registry().latest_publish(HERO, "cine"), 0)

    def test_rebuild_finds_assets_at_any_depth(self):
        self.create()
        self.create("shooter|main|props|crate", asset_type="Prop")
        self.create("shooter|main|env|forest|rocks|boulder", asset_type="Environment")
        os.remove(os.path.join(self.project.root, "registry.json"))
        registry = self.registry()   # rebuilds when registry.json is missing
        self.assertEqual(registry.ids(), ["shooter|main|characters|hero", "shooter|main|env|forest|rocks|boulder",
                                          "shooter|main|props|crate"])
        self.assertEqual(registry.errors, [])

    def test_find_by_type_and_skeleton(self):
        self.create("shooter|main|skeletons|biped", asset_type="Skeleton")
        self.create(skeleton="shooter|main|skeletons|biped")
        self.create("shooter|main|characters|villain", skeleton="shooter|main|skeletons|biped")
        self.create("shooter|main|characters|dog")
        registry = self.registry()
        self.assertEqual(registry.find(asset_type="Character"),
                         ["shooter|main|characters|dog", HERO, "shooter|main|characters|villain"])
        self.assertEqual(registry.find(skeleton="SHOOTER|main|skeletons|biped"),
                         [HERO, "shooter|main|characters|villain", "shooter|main|skeletons|biped"])
        self.assertEqual(registry.find(asset_type="Character", skeleton="shooter|main|characters|dog"),
                         ["shooter|main|characters|dog"])

    def test_files_lists_what_exists(self):
        hero = self.create(rigs=["game"])
        self.write(hero.path("skeleton"))
        self.write(hero.path("shapes", "game"))
        os.makedirs(hero.path("weights", "game"))
        self.assertEqual(self.registry().rebuild().get(HERO)["files"],
                         ["skeleton/hero_skeleton.ma", "variants/game/shapes.json", "variants/game/weights"])

    def test_rebuild_reports_nested_assets(self):
        hero = self.create()
        nested = os.path.join(hero.folder, "sword")
        self.write(os.path.join(nested, "asset.json"), json.dumps({"formatVersion": 1, "assetType": "Weapon", "rigs": []}))
        registry = self.registry().rebuild()
        self.assertEqual(registry.ids(), [HERO])
        self.assertEqual(len(registry.errors), 1)
        self.assertIn("never nest", registry.errors[0])

    def test_rebuild_skips_other_projects(self):
        self.create()
        dlc = Project.create(os.path.join(self.project.root, "dlc"))
        Asset.create("shooter|main|dlc|props|crate", "Prop", root=self.root)
        self.assertEqual(self.registry().rebuild().ids(), [HERO])
        self.assertEqual(Registry(dlc, root=self.root).ids(), ["shooter|main|dlc|props|crate"])

    def test_rebuild_reports_unreadable_assets(self):
        self.create()
        self.write(os.path.join(self.project.root, "props", "broken", "asset.json"), "{not json")
        registry = self.registry().rebuild()
        self.assertEqual(registry.ids(), [HERO])
        self.assertEqual(len(registry.errors), 1)

    def test_unknown_asset(self):
        self.assertIsNone(self.registry().get(HERO))
        with self.assertRaises(ProjectError):
            self.registry().latest_publish(HERO, "game")


class Versions(TempRoot):

    def test_nothing_to_version(self):
        self.assertIsNone(versions.version(os.path.join(self.root, "missing.json")))

    def test_numbers_count_up_from_the_highest(self):
        path = os.path.join(self.root, "shapes.json")
        for text in ("one", "two", "three"):
            self.write(path, text)
            versions.version(path)
        found = versions.list_versions(path)
        self.assertEqual([number for number, _ in found], [1, 2, 3])
        self.assertEqual(os.path.basename(found[0][1]), "shapes.v001.json")
        self.assertEqual(self.read(found[1][1]), "two")
        os.remove(found[1][1])
        self.assertTrue(versions.version(path).endswith("shapes.v004.json"), "a deleted number is never reused")

    def test_folders_are_copied_whole(self):
        folder = os.path.join(self.root, "weights")
        self.write(os.path.join(folder, "body.json"), "w")
        copy = versions.version(folder)
        self.assertEqual(os.path.basename(copy), "weights.v001")
        self.assertEqual(self.read(os.path.join(copy, "body.json")), "w")

    def test_other_files_in_the_versions_folder_are_ignored(self):
        path = os.path.join(self.root, "shapes.json")
        self.write(path)
        self.write(os.path.join(self.root, "versions", "shapes_old.json"))
        self.write(os.path.join(self.root, "versions", "other.v009.json"))
        self.assertTrue(versions.version(path).endswith("shapes.v001.json"))


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
        self.hero = self.create(rigs=["game"])

    def test_save_makes_folders_and_versions_the_old_file(self):
        path = handlers.save(self.hero, "shapes", variant="game", text="first", rig_root="hero:rigRootModule1")
        self.assertEqual(path, self.hero.path("shapes", "game"))
        self.assertEqual(versions.list_versions(path), [])
        handlers.save(self.hero, "shapes", variant="game", text="second")
        self.assertEqual(self.read(path), "second")
        self.assertEqual(self.read(versions.list_versions(path)[0][1]), "first")
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
