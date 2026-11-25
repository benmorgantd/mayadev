"""bmaya.core.asset in plain Python: ids, projects, assets with their skeletons, rigs and looks, rig.json and
look.json, the registry, publishes, local versions, source control calls and handler dispatch.

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

from bmaya.core.asset import Asset, AssetError, AssetIdError, AssetLook, Project, ProjectError, Registry  # noqa: E402
from bmaya.core.asset import LookRecord, RecordError, RigRecord, RigRef, SkeletonRef  # noqa: E402
from bmaya.core.asset import assetid, handlers, publishes, records, sourcecontrol, versions  # noqa: E402
from bmaya.core.asset.project import (  # noqa: E402
    DEFAULT_PROJECT, FORMAT_VERSION, PROJECTS_ROOT_ENV, projects_root, update_project_data, write_json)

HERO = "shooter\\main\\characters\\hero"
VILLAIN = "shooter\\main\\characters\\villain"
DEFAULT = SkeletonRef("default")

# project.json as mayadev wrote it at format version 2, when a variant was a rig with its own model and weights.
VERSION_2_FILE_TYPES = {
    "skeleton": {"path": "skeleton/{name}_skeleton.ma"},
    "model": {"path": "variants/{variant}/model/{name}_{variant}_model.ma"},
    "textures": {"path": "variants/{variant}/textures", "folder": True},
    "shaders": {"path": "variants/{variant}/shaders", "folder": True},
    "template": {"path": "variants/{variant}/template.json"},
    "shapes": {"path": "variants/{variant}/shapes.json"},
    "weights": {"path": "variants/{variant}/weights", "folder": True},
    "postops": {"path": "variants/{variant}/postops.py"},
    "rig": {"path": "variants/{variant}/{name}_{variant}_rig.ma"},
    "publish": {"path": "variants/{variant}/publish", "folder": True},
    "controlposes": {"path": "controlposes", "folder": True},
    "controlanims": {"path": "controlanims", "folder": True},
    "exports": {"path": "exports", "folder": True},
    "sources": {"path": "sources", "folder": True},
}


class RecordingSourceControl(sourcecontrol.SourceControl):
    def __init__(self):
        self.calls = []

    def checkout(self, path):
        self.calls.append(("checkout", path))

    def add(self, path):
        self.calls.append(("add", path))


class DepotSourceControl(sourcecontrol.SourceControl):
    """A depot that holds look folders the workspace may not have. list_folders answers from `depot`, and sync copies a
    depot folder's files into the workspace (a name -> {relative file: text} map). A failing list or sync raises."""

    def __init__(self, depot=None):
        self.depot = depot or {}
        self.listing_fails = False
        self.sync_fails = False
        self.synced = []

    def list_folders(self, path):
        if self.listing_fails:
            raise ConnectionError("server down")
        return sorted(self.depot)

    def sync(self, path):
        if self.sync_fails:
            raise ConnectionError("server down")
        self.synced.append(path)
        for relative, text in self.depot[os.path.basename(path)].items():
            target = os.path.join(path, relative)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(text)


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

    def create(self, asset_id=HERO, asset_type="Character", skeletons=(), rigs=(), looks=()):
        """An asset with skeletons (an empty skeleton.json each), and rigs and looks on its "default" skeleton."""
        asset = Asset.create(asset_id, asset_type, root=self.root)
        for name in skeletons:
            self.write(asset.path("skeleton", name), "{}")
        for name in rigs:
            asset.add_rig(name, DEFAULT)
        for name in looks:
            asset.add_look(name, [DEFAULT])
        return asset

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
        found = Project.find(os.path.join(self.project.root, "characters", "hero", "rigs", "body"))
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
        # Step 1 adds the library folders at the asset's top level, and step 2 moves them to where they now belong.
        self.assertEqual(project.file_type("controlposes").relative_path("hero", "body"), os.path.join("rigs", "body", "controlposes"))
        self.assertEqual(project.file_type("controlanims").relative_path("hero", "body"), os.path.join("rigs", "body", "controlanims"))
        self.assertEqual(project.file_type("exports").relative_path("hero", "default"), os.path.join("skeletons", "default", "exports"))
        self.assertEqual(project.file_type("sources").relative_path("hero"), "sources")
        for key in ("controlposes", "controlanims", "exports", "sources"):
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

    def test_a_version_2_project_moves_to_skeletons_rigs_and_looks(self):
        old = {"formatVersion": 2, "assetTypes": ["Prop"], "fileTypes": json.loads(json.dumps(VERSION_2_FILE_TYPES)),
               "rig": {"regions": ["face"]}, "library": {"statuses": ["wip"]}}
        old["fileTypes"]["anims"] = {"folder": True, "path": "anims"}       # never a default: a studio's own
        root = self.old_project(old)
        project = Project(root)
        expected = dict(DEFAULT_PROJECT["fileTypes"], anims={"folder": True, "path": "anims"})
        saved = json.loads(self.read(os.path.join(root, "project.json")))
        self.assertEqual(saved["formatVersion"], 4)   # step 3 then adds the markers file, which is in the defaults too
        self.assertEqual(saved["fileTypes"], expected)
        self.assertNotIn("publish", project.file_types, "publishes are per rig and per look now")
        self.assertEqual(saved["rig"], {"regions": ["face"]})
        self.assertEqual(project.file_type("skeleton").relative_path("hero", "default"),
                         os.path.join("skeletons", "default", "skeleton.json"))
        self.assertEqual(project.file_type("model").relative_path("hero", "winter"),
                         os.path.join("looks", "winter", "model", "hero_winter_model.ma"))

    def test_a_version_2_path_a_studio_edited_is_kept_and_one_with_variant_fails_by_name(self):
        kept = {"formatVersion": 2, "assetTypes": ["Prop"], "fileTypes": {
            "shapes": {"path": "rigging/shapes.json"}, "template": {"path": "variants/{variant}/template.json"}}}
        project = Project(self.old_project(kept))
        self.assertEqual(project.file_type("shapes").relative_path("hero"), os.path.join("rigging", "shapes.json"))
        self.assertEqual(project.file_type("template").relative_path("hero", "body"), os.path.join("rigs", "body", "template.json"))

        edited = {"formatVersion": 2, "assetTypes": ["Prop"], "fileTypes": {
            "shapes": {"path": "variants/{variant}/control_shapes.json"}}}
        with self.assertRaises(ProjectError) as raised:
            Project(self.old_project(edited))
        message = str(raised.exception)
        for text in ("project.json", "'shapes'", "variants/{variant}/control_shapes.json", "{rig}"):
            self.assertIn(text, message)

    def test_a_version_3_project_gains_the_assets_markers_file(self):
        # RigModules D73: one markers file per asset, markers/markers.json. A studio's own markers path is kept.
        root = self.old_project({"formatVersion": 3, "assetTypes": ["Prop"], "fileTypes": {}})
        project = Project(root)
        self.assertEqual(project.file_type("markers").relative_path("hero"), os.path.join("markers", "markers.json"))
        self.assertIsNone(project.file_type("markers").owner, "the markers file belongs to the asset, not to a rig")
        self.assertEqual(json.loads(self.read(os.path.join(root, "project.json")))["formatVersion"], 4)

        own = Project(self.old_project({"formatVersion": 3, "assetTypes": ["Prop"], "fileTypes": {"markers": {"path": "rigging/points.json"}}}))
        self.assertEqual(own.file_type("markers").relative_path("hero"), os.path.join("rigging", "points.json"))

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
        # Written by hand from the layout in RigModules' design/rigs-and-looks.md, section 3.
        expected = {
            ("skeleton", "default"): ("skeletons", "default", "skeleton.json"),
            ("exports", "default"): ("skeletons", "default", "exports"),
            ("riginfo", "body"): ("rigs", "body", "rig.json"),
            ("template", "body"): ("rigs", "body", "template.json"),
            ("shapes", "body"): ("rigs", "body", "shapes.json"),
            ("postops", "body"): ("rigs", "body", "postops.py"),
            ("rig", "body"): ("rigs", "body", "hero_body_rig.ma"),
            ("rigpublish", "body"): ("rigs", "body", "publish"),
            ("controlposes", "body"): ("rigs", "body", "controlposes"),
            ("controlanims", "body"): ("rigs", "body", "controlanims"),
            ("lookinfo", "winter"): ("looks", "winter", "look.json"),
            ("model", "winter"): ("looks", "winter", "model", "hero_winter_model.ma"),
            ("textures", "winter"): ("looks", "winter", "textures"),
            ("shaders", "winter"): ("looks", "winter", "shaders"),
            ("weights", "winter"): ("looks", "winter", "weights"),
            ("lookpublish", "winter"): ("looks", "winter", "publish"),
            ("sources", None): ("sources",),
            ("markers", None): ("markers", "markers.json"),
        }
        self.assertEqual({key for key, _ in expected}, set(self.project.file_types))
        for (key, owner), parts in expected.items():
            self.assertEqual(self.project.file_type(key).relative_path("hero", owner), os.path.join(*parts), key)

    def test_a_file_type_belongs_to_a_skeleton_a_rig_a_look_or_the_asset(self):
        owners = {key: self.project.file_type(key).owner for key in ("skeleton", "exports", "shapes", "weights", "sources")}
        self.assertEqual(owners, {"skeleton": "skeleton", "exports": "skeleton", "shapes": "rig", "weights": "look", "sources": None})
        self.assertEqual(self.project.file_type("template").owner_parent(), "rigs")
        self.assertEqual(self.project.file_type("model").owner_parent(), "looks")
        self.assertEqual(self.project.file_type("skeleton").owner_parent(), "skeletons")
        with self.assertRaises(ProjectError):
            self.project.file_type("sources").owner_parent()

    def test_owner_rules(self):
        with self.assertRaises(ProjectError) as raised:
            self.project.file_type("shapes").relative_path("hero")            # belongs to a rig, none given
        self.assertIn("belongs to a rig", str(raised.exception))
        with self.assertRaises(ProjectError):
            self.project.file_type("sources").relative_path("hero", "body")   # asset level, an owner given
        for bad in ("bad/name", "Body", ""):
            with self.assertRaises(ProjectError):
                self.project.file_type("shapes").relative_path("hero", bad)
        with self.assertRaises(ProjectError):
            self.project.file_type("nope")

    def test_a_path_with_two_owners_or_an_unknown_field_fails_the_load(self):
        for path, text in (("rigs/{rig}/looks/{look}/x.json", "look and rig"), ("rigs/{rig}/{shot}.json", "shot")):
            root = self.old_project({"formatVersion": FORMAT_VERSION, "assetTypes": ["Prop"], "fileTypes": {"odd": {"path": path}}})
            with self.assertRaises(ProjectError) as raised:
                Project(root)
            self.assertIn(text, str(raised.exception))
            self.assertIn("'odd'", str(raised.exception))

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
        hero = self.create()
        self.assertTrue(hero.exists())
        self.assertEqual(json.loads(self.read(hero.info_path)), {"formatVersion": 2, "assetType": "Character"})
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
        with self.assertRaises(TypeError):
            Asset.create("shooter\\main\\props\\crate", "Prop", skeleton=HERO, root=self.root)   # asset.json names no skeleton now

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
        path = hero.path("shapes", "body")
        self.assertEqual(path, os.path.join(hero.folder, "rigs", "body", "shapes.json"))
        self.assertEqual(hero.path("weights", owner="winter"), os.path.join(hero.folder, "looks", "winter", "weights"))
        self.assertFalse(os.path.exists(hero.folder))
        self.assertFalse(hero.file_exists("shapes", "body"))

    def test_info_of_a_missing_asset_fails(self):
        with self.assertRaises(AssetError):
            Asset(HERO, root=self.root).info

    def test_from_path_finds_the_enclosing_asset(self):
        hero = self.create()
        inside = os.path.join(hero.folder, "looks", "default", "weights", "body.json")
        self.assertEqual(Asset.from_path(inside, root=self.root), hero)
        with self.assertRaises(AssetError):
            Asset.from_path(os.path.join(self.project.root, "props"), root=self.root)

    def test_a_version_1_asset_json_drops_its_skeleton_and_is_written_back(self):
        hero = Asset(HERO, root=self.root)
        self.write(hero.info_path, json.dumps({"formatVersion": 1, "assetType": "Character", "skeleton": VILLAIN}))
        self.assertEqual(hero.info, {"formatVersion": 2, "assetType": "Character"})
        self.assertEqual(json.loads(self.read(hero.info_path)), {"formatVersion": 2, "assetType": "Character"})
        self.assertFalse(hasattr(hero, "skeleton"))

    def test_a_version_1_asset_json_that_cannot_be_written_back_still_reads_updated(self):
        hero = Asset(HERO, root=self.root)
        self.write(hero.info_path, json.dumps({"formatVersion": 1, "assetType": "Character"}))
        with mock.patch("bmaya.core.asset.asset.write_json", side_effect=PermissionError("read-only")):
            self.assertEqual(hero.info["formatVersion"], 2)
        self.assertEqual(json.loads(self.read(hero.info_path))["formatVersion"], 1)

    def test_an_unknown_asset_json_version_fails(self):
        hero = Asset(HERO, root=self.root)
        self.write(hero.info_path, json.dumps({"formatVersion": 3, "assetType": "Character"}))
        with self.assertRaises(AssetError):
            hero.info

    def test_skeletons_rigs_and_looks_are_folders_with_their_file(self):
        hero = self.create()
        self.assertEqual((hero.skeletons, hero.rigs, hero.looks), ([], [], []))
        before = self.read(hero.info_path)
        self.write(hero.path("skeleton", "face"), "{}")
        self.write(hero.path("skeleton", "default"), "{}")
        hero.add_rig("body", DEFAULT)
        hero.add_rig("body_cine", DEFAULT, source=RigRef("body"))
        hero.add_look("winter", [DEFAULT])
        hero.add_look("default", [DEFAULT, SkeletonRef("face")])
        for folder in ("skeletons", "rigs", "looks"):
            os.makedirs(os.path.join(hero.folder, folder, "scratch"))        # no file inside: not one of them
        os.makedirs(os.path.join(hero.folder, "rigs", "Bad"))
        self.write(os.path.join(hero.folder, "rigs", "Bad", "rig.json"), "{}")   # not a valid name: not listed
        self.assertEqual(hero.skeletons, ["default", "face"])
        self.assertEqual(hero.rigs, ["body", "body_cine"])
        self.assertEqual(hero.looks, ["default", "winter"])
        self.assertEqual(self.read(hero.info_path), before, "adding a skeleton, a rig or a look edits nothing shared")

    LOOK_JSON = '{"formatVersion": 1, "skeletons": ["default"]}'

    def use_depot(self, depot):
        depot_control = DepotSourceControl(depot)
        sourcecontrol.set_current(depot_control)   # setUp registered the cleanup that restores the default
        return depot_control

    def test_all_looks_is_the_local_scan_without_a_source_control_listing(self):
        hero = self.create(looks=["winter", "default"])
        self.assertEqual(hero.all_looks(), [AssetLook("default", True), AssetLook("winter", True)])
        self.assertEqual(self.create(VILLAIN).all_looks(), [])

    def test_all_looks_lists_the_depots_looks_and_marks_the_unsynced_ones(self):
        hero = self.create(looks=["default"])
        self.use_depot({"default": {}, "winter": {}, "Bad Name": {}})
        self.assertEqual(hero.all_looks(), [AssetLook("default", True), AssetLook("winter", False)],
                         "an invalid folder name is not a look")
        self.assertEqual(hero.looks, ["default"], "looks stays the local scan")

    def test_a_look_folder_without_its_look_json_is_not_local(self):
        hero = self.create()
        self.use_depot({"winter": {}})
        os.makedirs(os.path.join(hero.folder, "looks", "winter", "weights"))   # half synced: no look.json
        self.assertEqual(hero.all_looks(), [AssetLook("winter", False)])

    def test_a_failing_listing_falls_back_to_the_local_scan_with_a_warning(self):
        hero = self.create(looks=["default"])
        depot = self.use_depot({"default": {}, "winter": {}})
        depot.listing_fails = True
        with mock.patch("bmaya.core.log.warning") as warning:
            self.assertEqual(hero.all_looks(), [AssetLook("default", True)])
        warning.assert_called_once()
        self.assertIn("server down", warning.call_args.args[0])

    def test_sync_look_brings_in_an_unsynced_look_and_leaves_a_local_one_alone(self):
        hero = self.create(looks=["default"])
        depot = self.use_depot({"default": {}, "winter": {"look.json": self.LOOK_JSON}})
        hero.sync_look("default")
        self.assertEqual(depot.synced, [], "a local look is not synced again")
        hero.sync_look("winter")
        self.assertEqual(depot.synced, [os.path.join(hero.folder, "looks", "winter")])
        self.assertEqual(hero.look("winter"), LookRecord((DEFAULT,)))
        self.assertEqual(hero.all_looks(), [AssetLook("default", True), AssetLook("winter", True)])

    def test_sync_look_failures_raise_asset_error(self):
        hero = self.create()
        depot = self.use_depot({"winter": {"look.json": self.LOOK_JSON}, "empty": {"x.txt": ""}})
        depot.sync_fails = True
        with self.assertRaisesRegex(AssetError, "Could not sync the look 'winter'.*server down"):
            hero.sync_look("winter")
        depot.sync_fails = False
        with self.assertRaisesRegex(AssetError, "no look.json after syncing"):
            hero.sync_look("empty")
        with self.assertRaisesRegex(AssetError, "not a look name"):
            hero.sync_look("Bad Name")

    def test_add_rig_and_add_look_write_their_file_and_tell_source_control(self):
        hero = self.create()
        self.source_control.calls.clear()
        record = hero.add_rig("body", DEFAULT)
        self.assertEqual(record, RigRecord(DEFAULT, None))
        self.assertEqual(json.loads(self.read(os.path.join(hero.folder, "rigs", "body", "rig.json"))),
                         {"formatVersion": 1, "skeleton": "default"})
        hero.add_look("default", [DEFAULT])
        self.assertEqual(json.loads(self.read(os.path.join(hero.folder, "looks", "default", "look.json"))),
                         {"formatVersion": 1, "skeletons": ["default"]})
        self.assertEqual(self.source_control.calls, [("add", hero.path("riginfo", "body")), ("add", hero.path("lookinfo", "default"))])
        self.assertEqual(hero.rig("body"), RigRecord(DEFAULT, None))
        self.assertEqual(hero.look("default"), LookRecord((DEFAULT,)))

    def test_add_checks(self):
        hero = self.create(rigs=["body"], looks=["default"])
        with self.assertRaises(AssetError):
            hero.add_rig("body", DEFAULT)                    # exists
        with self.assertRaises(AssetError):
            hero.add_look("default", [DEFAULT])              # exists
        with self.assertRaises(ProjectError):
            hero.add_rig("Body", DEFAULT)                    # uppercase
        with self.assertRaises(RecordError):
            hero.add_look("empty", [])                       # a look names a skeleton
        with self.assertRaises(AssetError):
            Asset(VILLAIN, root=self.root).add_rig("body", DEFAULT)   # no asset.json
        with self.assertRaises(AssetError) as raised:
            hero.rig("face")
        self.assertIn("body", str(raised.exception))
        with self.assertRaises(AssetError):
            hero.look("winter")

    def test_add_rig_writes_the_parent_and_parent_of_reads_it(self):
        hero = self.create(rigs=["body"])
        record = hero.add_rig("face", SkeletonRef("face"), parent=RigRef("body"))
        self.assertEqual(record.parent, RigRef("body"))
        self.assertEqual(json.loads(self.read(hero.path("riginfo", "face"))),
                         {"formatVersion": 1, "skeleton": "face", "parent": "body"})
        self.assertEqual(hero.parent_of("face"), (hero, "body"))
        self.assertIsNone(hero.parent_of("body"))
        villain = self.create(VILLAIN)
        villain.add_rig("hat", SkeletonRef("hat"), parent=RigRef("body", HERO))
        self.assertEqual(villain.parent_of("hat"), (hero, "body"), "a parent can be in another asset")

    def test_a_parent_needn_t_exist_when_the_rig_is_added(self):
        hero = self.create()
        hero.add_rig("face", SkeletonRef("face"), parent=RigRef("body"))   # built later, like a skeleton
        self.assertEqual(hero.parent_of("face"), (hero, "body"))

    def test_a_rig_can_not_attach_to_itself_or_to_its_own_attachment(self):
        hero = self.create()
        with self.assertRaisesRegex(AssetError, "can't attach to itself"):
            hero.add_rig("face", SkeletonRef("face"), parent=RigRef("face"))
        self.assertFalse(hero.file_exists("riginfo", "face"), "nothing is written for a refused rig")
        # The parents are added before the body, so the body closes the loop: body -> hat -> face -> body.
        hero.add_rig("face", SkeletonRef("face"), parent=RigRef("body"))
        hero.add_rig("hat", SkeletonRef("hat"), parent=RigRef("face"))
        with self.assertRaisesRegex(AssetError, "body.*hat.*face.*body|hat.*face.*body"):
            hero.add_rig("body", DEFAULT, parent=RigRef("hat"))
        self.assertFalse(hero.file_exists("riginfo", "body"))

    def test_a_parent_loop_through_another_asset_is_refused(self):
        hero = self.create()
        villain = self.create(VILLAIN)
        villain.add_rig("mask", SkeletonRef("mask"), parent=RigRef("body", HERO))
        with self.assertRaisesRegex(AssetError, "attach to itself"):
            hero.add_rig("body", DEFAULT, parent=RigRef("mask", VILLAIN))

    def test_a_rig_can_be_a_copy_and_an_attachment(self):
        hero = self.create(rigs=["body"])
        hero.add_rig("face", SkeletonRef("face"), source=RigRef("body"), parent=RigRef("body"))
        self.assertEqual(hero.rig("face"), RigRecord(SkeletonRef("face"), RigRef("body"), RigRef("body")))

    def test_a_rig_and_a_look_can_name_another_assets_skeleton(self):
        # NPCs share one skeleton with no copied skeleton file. A look-only asset has looks and nothing else.
        hero = self.create(skeletons=["default"], rigs=["body"])
        shared = SkeletonRef("default", asset=HERO)
        guards = self.create("shooter\\main\\npc\\guards", asset_type="Character")
        guards.add_look("captain", [shared])
        guards.add_rig("body", shared)
        self.assertEqual(json.loads(self.read(guards.path("lookinfo", "captain"))),
                         {"formatVersion": 1, "skeletons": [{"asset": HERO, "name": "default"}]})
        self.assertEqual(guards.resolve_skeleton(shared), (hero, "default"))
        self.assertEqual(guards.skeleton_of("body"), (hero, "default"))
        self.assertEqual(hero.skeleton_of("body"), (hero, "default"))
        self.assertEqual((guards.skeletons, guards.looks), ([], ["captain"]))

    def test_a_rig_wears_a_look_of_its_own_skeleton(self):
        hero = self.create(rigs=["body"], looks=["default"])
        hero.add_rig("face", SkeletonRef("face"))
        hero.add_look("head", [SkeletonRef("face")])
        hero.add_look("own_by_id", [SkeletonRef("default", asset=HERO)])      # the same skeleton, named in full
        hero.add_look("both", [SkeletonRef("face"), DEFAULT])
        self.assertTrue(hero.look_fits("default", "body"))
        self.assertTrue(hero.look_fits("own_by_id", "body"))
        self.assertTrue(hero.look_fits("both", "body"))
        self.assertFalse(hero.look_fits("head", "body"))
        self.assertTrue(hero.look_fits("head", "face"))


class Records(TempRoot):

    def path(self, name="rig.json"):
        return os.path.join(self.root, name)

    def test_rig_round_trip_in_both_reference_forms(self):
        for record, data in (
            (RigRecord(DEFAULT), {"formatVersion": 1, "skeleton": "default"}),
            (RigRecord(DEFAULT, RigRef("body")), {"formatVersion": 1, "skeleton": "default", "source": "body"}),
            (RigRecord(SkeletonRef("default", HERO), RigRef("body", HERO)),
             {"formatVersion": 1, "skeleton": {"asset": HERO, "name": "default"}, "source": {"asset": HERO, "rig": "body"}}),
        ):
            records.write_rig(self.path(), record)
            self.assertEqual(json.loads(self.read(self.path())), data)
            self.assertEqual(records.read_rig(self.path()), record)

    def test_rig_parent_round_trip_and_old_files_read_as_before(self):
        for record, data in (
            (RigRecord(SkeletonRef("face"), parent=RigRef("body")),
             {"formatVersion": 1, "skeleton": "face", "parent": "body"}),
            (RigRecord(SkeletonRef("prop"), parent=RigRef("body", HERO)),
             {"formatVersion": 1, "skeleton": "prop", "parent": {"asset": HERO, "rig": "body"}}),
            (RigRecord(SkeletonRef("face"), RigRef("face_old"), RigRef("body")),
             {"formatVersion": 1, "skeleton": "face", "source": "face_old", "parent": "body"}),
        ):
            records.write_rig(self.path(), record)
            self.assertEqual(json.loads(self.read(self.path())), data)
            self.assertEqual(records.read_rig(self.path()), record)
        self.write(self.path(), json.dumps({"formatVersion": 1, "skeleton": "default"}))
        self.assertEqual(records.read_rig(self.path()), RigRecord(DEFAULT, None, None), "no parent key: no parent")

    def test_look_round_trip(self):
        record = LookRecord((DEFAULT, SkeletonRef("face", HERO)))
        records.write_look(self.path("look.json"), record)
        self.assertEqual(json.loads(self.read(self.path("look.json"))),
                         {"formatVersion": 1, "skeletons": ["default", {"asset": HERO, "name": "face"}]})
        self.assertEqual(records.read_look(self.path("look.json")), record)

    def test_bad_rig_files_name_the_file(self):
        bad = {
            "not json": "{nope",
            "wrong version": {"formatVersion": 2, "skeleton": "default"},
            "no skeleton": {"formatVersion": 1},
            "unknown key": {"formatVersion": 1, "skeleton": "default", "variant": "body"},
            "parent by the wrong key": {"formatVersion": 1, "skeleton": "default", "parent": {"asset": HERO, "name": "body"}},
            "joined parent": {"formatVersion": 1, "skeleton": "default", "parent": HERO + "\\body"},
            "joined string": {"formatVersion": 1, "skeleton": HERO + "\\default"},
            "uppercase name": {"formatVersion": 1, "skeleton": "Default"},
            "half a reference": {"formatVersion": 1, "skeleton": {"asset": HERO}},
            "bad asset id": {"formatVersion": 1, "skeleton": {"asset": "Shooter\\hero", "name": "default"}},
            "source by the wrong key": {"formatVersion": 1, "skeleton": "default", "source": {"asset": HERO, "name": "body"}},
        }
        for label, data in bad.items():
            with self.subTest(label):
                self.write(self.path(), data if isinstance(data, str) else json.dumps(data))
                with self.assertRaises(RecordError) as raised:
                    records.read_rig(self.path())
                self.assertIn("rig.json", str(raised.exception))

    def test_bad_look_files(self):
        for data in ({"formatVersion": 1, "skeletons": "default"}, {"formatVersion": 1, "skeletons": []},
                     {"formatVersion": 1, "skeletons": [5]}, {"formatVersion": 1}):
            self.write(self.path("look.json"), json.dumps(data))
            with self.assertRaises(RecordError):
                records.read_look(self.path("look.json"))

    def test_references_check_their_names(self):
        for make in (lambda: SkeletonRef("Body"), lambda: SkeletonRef("body", "Bad\\id"), lambda: RigRef(""), lambda: RigRef("a b")):
            with self.assertRaises((RecordError, AssetIdError)):
                make()


class Publishes(TempRoot):

    def setUp(self):
        super().setUp()
        self.hero = self.create(rigs=["body"], looks=["winter"])

    def test_ids_sort_in_time_order(self):
        early = publishes.make_id("bmorgan", datetime.datetime(2026, 11, 8, 9, 5, 1, tzinfo=datetime.timezone.utc))
        late = publishes.make_id("alice", datetime.datetime(2026, 11, 8, 14, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(early, "20261108T090501Z_bmorgan")
        self.assertLess(early, late)
        self.assertEqual(publishes.make_id("Ben Morgan.2", datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)),
                         "20260101T000000Z_Ben_Morgan_2")

    def test_create_adds_a_folder_and_edits_nothing(self):
        before = self.read(self.hero.info_path)
        folder = publishes.create(self.hero, "rig", "body", {"pluginVersion": "0.1"}, user="bmorgan")
        publish_id = os.path.basename(folder)
        self.assertEqual(os.path.dirname(folder), os.path.join(self.hero.folder, "rigs", "body", "publish"))
        self.assertEqual(self.read(self.hero.info_path), before)
        self.assertEqual(publishes.latest(self.hero, "rig", "body"), publish_id)
        record = publishes.info(self.hero, "rig", "body", publish_id)
        self.assertEqual(record, {"formatVersion": 1, "id": publish_id, "user": "bmorgan", "pluginVersion": "0.1"})
        self.assertIn(("add", os.path.join(folder, "publish.json")), self.source_control.calls)

    def test_a_rig_and_a_look_publish_separately(self):
        rig_folder = publishes.create(self.hero, "rig", "body", user="bmorgan")
        self.assertIsNone(publishes.latest(self.hero, "look", "winter"))
        look_folder = publishes.create(self.hero, "look", "winter", user="alice")
        self.assertEqual(os.path.dirname(look_folder), os.path.join(self.hero.folder, "looks", "winter", "publish"))
        self.assertEqual(publishes.list_ids(self.hero, "look", "winter"), [os.path.basename(look_folder)])
        self.assertEqual(publishes.list_ids(self.hero, "rig", "body"), [os.path.basename(rig_folder)])

    def test_latest_is_the_newest_id(self):
        base = self.hero.path("rigpublish", "body")
        for publish_id in ("20261108T090000Z_bmorgan", "20261109T080000Z_alice", "20261108T120000Z_alice"):
            self.write(os.path.join(base, publish_id, "publish.json"), "{}")
        os.makedirs(os.path.join(base, "not_a_publish"))
        os.makedirs(os.path.join(base, "20261110T000000Z_halfwritten"))   # no publish.json yet
        self.assertEqual(publishes.list_ids(self.hero, "rig", "body"),
                         ["20261108T090000Z_bmorgan", "20261108T120000Z_alice", "20261109T080000Z_alice"])
        self.assertEqual(publishes.latest(self.hero, "rig", "body"), "20261109T080000Z_alice")

    def test_create_checks(self):
        self.assertIsNone(publishes.latest(self.hero, "rig", "body"))
        with self.assertRaises(AssetError):
            publishes.create(self.hero, "rig", "cine")       # not a rig
        with self.assertRaises(AssetError):
            publishes.create(self.hero, "look", "body")      # a rig's name is not a look
        with self.assertRaises(AssetError):
            publishes.create(self.hero, "variant", "body")   # not a kind
        fixed = datetime.datetime(2026, 11, 8, tzinfo=datetime.timezone.utc)
        with mock.patch.object(publishes, "make_id", return_value=publishes.make_id("bmorgan", fixed)):
            publishes.create(self.hero, "rig", "body")
            with self.assertRaises(AssetError):
                publishes.create(self.hero, "rig", "body")   # same second, same user


class Registries(TempRoot):

    def test_writes_nothing(self):
        self.create(rigs=["body"])
        self.registry().refresh()
        written = [name for _, _, files in os.walk(self.root) for name in files]
        self.assertEqual(sorted(written), ["asset.json", "project.json", "rig.json"])

    def test_scan_finds_assets_at_any_depth(self):
        self.create()
        self.create("shooter\\main\\props\\crate", asset_type="Prop")
        self.create("shooter\\main\\env\\forest\\rocks\\boulder", asset_type="Environment")
        registry = self.registry()
        self.assertEqual(registry.ids(), ["shooter\\main\\characters\\hero", "shooter\\main\\env\\forest\\rocks\\boulder",
                                          "shooter\\main\\props\\crate"])
        self.assertEqual(registry.errors, [])

    def test_entries(self):
        hero = self.create(skeletons=["default"], rigs=["body"], looks=["winter"])
        hero.add_rig("body_cine", DEFAULT, source=RigRef("body"))
        rig_folder = publishes.create(hero, "rig", "body", user="bmorgan")
        look_folder = publishes.create(hero, "look", "winter", user="bmorgan")
        entry = self.registry().get(HERO)
        self.assertEqual(entry, {
            "assetType": "Character",
            "skeletons": ["default"],
            "rigs": {"body": {"skeleton": DEFAULT, "source": None, "latestPublish": os.path.basename(rig_folder)},
                     "body_cine": {"skeleton": DEFAULT, "source": RigRef("body"), "latestPublish": None}},
            "looks": {"winter": {"skeletons": (DEFAULT,), "latestPublish": os.path.basename(look_folder)}},
        })
        self.assertEqual(self.registry().latest_publish(HERO, "rig", "body"), os.path.basename(rig_folder))
        self.assertEqual(self.registry().latest_publish(HERO, "look", "winter"), os.path.basename(look_folder))
        self.assertIsNone(self.registry().latest_publish(HERO, "rig", "body_cine"))
        self.assertIsNone(self.registry().latest_publish(HERO, "look", "body"), "a rig's name is not a look")
        with self.assertRaises(ProjectError):
            self.registry().latest_publish(HERO, "variant", "body")

    def test_find_by_type_and_skeleton(self):
        # biped holds the skeleton. hero has a rig on it, guards only looks on it, and dog has its own skeleton.
        biped = "shooter\\main\\skeletons\\biped"
        guards = "shooter\\main\\npc\\guards"
        dog = "shooter\\main\\characters\\dog"
        shared = SkeletonRef("default", asset=biped)
        self.create(biped, asset_type="Skeleton", skeletons=["default"])
        self.create().add_rig("body", shared)
        self.create(guards).add_look("captain", [shared])
        self.create(dog, skeletons=["default"], rigs=["body"])
        registry = self.registry()
        self.assertEqual(registry.find(asset_type="Character"), [dog, HERO, guards])
        self.assertEqual(registry.find(skeleton=(biped, "default")), [HERO, guards, biped])
        self.assertEqual(registry.find(asset_type="Character", skeleton=(dog, "default")), [dog])
        self.assertEqual(registry.find(skeleton=(biped, "face")), [])

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
            self.registry().latest_publish(HERO, "rig", "body")


class Versions(TempRoot):

    def path(self, name="shapes.json"):
        return os.path.join(self.root, "shooter", "main", "characters", "hero", name)

    def test_nothing_to_version(self):
        self.assertIsNone(versions.version(self.path("missing.json"), self.root))

    def test_version_if_changed_skips_a_file_that_is_the_newest_copy(self):
        self.assertIsNone(versions.version_if_changed(self.path("missing.json"), self.root))
        self.write(self.path(), "one")
        self.assertTrue(versions.version_if_changed(self.path(), self.root).endswith("shapes.v001.json"))
        self.assertIsNone(versions.version_if_changed(self.path(), self.root), "unchanged since the newest copy")
        self.write(self.path(), "two")
        self.assertTrue(versions.version_if_changed(self.path(), self.root).endswith("shapes.v002.json"))
        self.write(self.path(), "one")
        self.assertTrue(versions.version_if_changed(self.path(), self.root).endswith("shapes.v003.json"),
                        "only the newest copy counts: going back to an older state is a change")

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

    def test_restore_copies_a_version_back_dated_now(self):
        self.write(self.path(), "one")
        copy = versions.version(self.path(), self.root)
        os.utime(copy, (1_000_000_000, 1_000_000_000))
        self.write(self.path(), "two")
        self.assertEqual(versions.restore(self.path(), self.root, 1), self.path())
        self.assertEqual(self.read(self.path()), "one")
        self.assertGreater(os.path.getmtime(self.path()), 1_000_000_000, "a restore is dated like a save")
        self.assertEqual(len(versions.list_versions(self.path(), self.root)), 1, "restore alone keeps no version")

    def test_restore_brings_back_a_deleted_file(self):
        self.write(self.path(), "one")
        versions.version(self.path(), self.root)
        os.remove(self.path())
        versions.restore(self.path(), self.root, 1)
        self.assertEqual(self.read(self.path()), "one")

    def test_restore_replaces_a_folder_whole(self):
        folder = self.path("weights")
        self.write(os.path.join(folder, "body.json"), "old")
        versions.version(folder, self.root)
        self.write(os.path.join(folder, "body.json"), "new")
        self.write(os.path.join(folder, "prop.json"), "added later")
        versions.restore(folder, self.root, 1)
        self.assertEqual(sorted(os.listdir(folder)), ["body.json"])
        self.assertEqual(self.read(os.path.join(folder, "body.json")), "old")

    def test_restore_of_a_missing_version_names_the_ones_there_are(self):
        self.write(self.path(), "one")
        versions.version(self.path(), self.root)
        versions.version(self.path(), self.root)
        with self.assertRaisesRegex(ValueError, "no local version 7. It has: 1, 2"):
            versions.restore(self.path(), self.root, 7)
        self.assertEqual(self.read(self.path()), "one")


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
        self.hero = self.create(rigs=["body"])
        self.source_control.calls.clear()

    def test_save_makes_folders_versions_and_tells_source_control(self):
        path = handlers.save(self.hero, "shapes", "body", text="first", rig_root="hero:rigRootModule1")
        self.assertEqual(path, self.hero.path("shapes", "body"))
        self.assertEqual(versions.list_versions(path, self.root), [])
        self.assertEqual(self.source_control.calls, [("add", path)])

        handlers.save(self.hero, "shapes", owner="body", text="second")
        self.assertEqual(self.read(path), "second")
        self.assertEqual(self.read(versions.list_versions(path, self.root)[0][1]), "first")
        self.assertEqual(self.source_control.calls, [("add", path), ("checkout", path)])
        self.assertEqual(self.handler.calls[0][2], {"owner": "body", "text": "first", "rig_root": "hero:rigRootModule1"})

    def test_restore_keeps_the_replaced_file_as_a_version_and_checks_it_out(self):
        path = handlers.save(self.hero, "shapes", "body", text="first")
        handlers.save(self.hero, "shapes", "body", text="second")   # version 1 is "first"
        self.source_control.calls.clear()
        self.assertEqual(handlers.restore(self.hero, "shapes", "body", 1), path)
        self.assertEqual(self.read(path), "first")
        found = versions.list_versions(path, self.root)
        self.assertEqual([number for number, _ in found], [1, 2])
        self.assertEqual(self.read(found[1][1]), "second", "the replaced file is version 2, so the restore is undoable")
        self.assertEqual(self.source_control.calls, [("checkout", path)])

    def test_save_restore_and_load_emit_changed_with_the_file_type_and_a_failure_does_not(self):
        seen = []
        handlers.changed.connect(seen.append)
        self.addCleanup(handlers.changed.disconnect, seen.append)
        handlers.save(self.hero, "shapes", "body", text="first")
        handlers.save(self.hero, "shapes", "body", text="second")
        handlers.restore(self.hero, "shapes", "body", 1)
        handlers.load(self.hero, "shapes", "body")
        self.assertEqual(seen, ["shapes"] * 4)
        with self.assertRaises(ValueError):
            handlers.restore(self.hero, "shapes", "body", 9)
        with self.assertRaises(FileNotFoundError):
            handlers.load(self.hero, "shapes", "missing")
        self.assertEqual(len(seen), 4)

    def test_restore_of_an_unknown_version_changes_nothing(self):
        path = handlers.save(self.hero, "shapes", "body", text="first")
        handlers.save(self.hero, "shapes", "body", text="second")
        self.source_control.calls.clear()
        with self.assertRaises(ValueError):
            handlers.restore(self.hero, "shapes", "body", 5)
        self.assertEqual((self.read(path), len(versions.list_versions(path, self.root)), self.source_control.calls),
                         ("second", 1, []))

    def test_load_returns_the_handler_result(self):
        handlers.save(self.hero, "shapes", "body", text="data")
        self.assertEqual(handlers.load(self.hero, "shapes", "body"), "data")

    def test_load_of_a_missing_file_fails(self):
        with self.assertRaises(FileNotFoundError):
            handlers.load(self.hero, "shapes", "body")

    def test_unregistered_and_base_handlers_raise(self):
        with self.assertRaises(NotImplementedError):
            handlers.save(self.hero, "weights", "default")
        handlers.register("postops", handlers.FileHandler())
        self.addCleanup(handlers.unregister, "postops")
        with self.assertRaises(NotImplementedError):
            handlers.save(self.hero, "postops", "body")


if __name__ == "__main__":
    unittest.main()
