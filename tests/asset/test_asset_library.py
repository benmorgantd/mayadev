"""bmaya.core.asset.library in plain Python: sources, listing, the index cache, search, masks and the file operations
(RigModules D51, design/library-browser.md).

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

from bmaya.core.asset import Asset, AssetIdError, Project, Registry, assetid, library, versions  # noqa: E402
from bmaya.core.asset.library import ANIMATION, POSE, FileInfo, LibraryError, Mask, MaskItem  # noqa: E402

HERO = "shooter\\main\\characters\\hero"
BIPED = "shooter\\main\\skeletons\\biped"


class LibraryBase(unittest.TestCase):
    """A projects root with the project shooter\\main, a skeleton asset and a hero that uses its skeleton, and the
    signed-in user fixed to "tester"."""

    def setUp(self):
        temp = tempfile.mkdtemp(prefix="bmaya_library_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.root = os.path.join(temp, "projects")
        for patcher in (mock.patch.dict(os.environ, {versions.VERSIONS_DIR_ENV: os.path.join(temp, "local_versions")}),
                        mock.patch.object(library, "login", return_value="tester")):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.project = Project.create(os.path.join(self.root, "shooter", "main"))
        self.biped = Asset.create(BIPED, "Skeleton", root=self.root)
        self.hero = Asset.create(HERO, "Character", skeleton=BIPED, root=self.root)

    def write(self, path, text="{}"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def source(self, key):
        return next(source for source in library.sources(self.hero) if source.key == key)

    def put(self, key, kind, name, suffix=None):
        """A file in a source's folder: <name>.controlpose.json unless a suffix is given."""
        folder = self.source(key).folders[kind]
        return self.write(os.path.join(folder, name + (suffix if suffix is not None else library.SUFFIX[kind])))


def entry(name="fist", kind=POSE, source=library.USER, **meta):
    """A LibraryEntry with the meta given, for search."""
    file = library.LibraryFile(f"C:/x/{name}.json", name, kind, source, source == library.USER, 0.0, False)
    return library.LibraryEntry(file, FileInfo(meta=meta))


class Sources(LibraryBase):

    def test_an_asset_has_approved_shared_and_user_sources_in_that_order(self):
        sources = library.sources(self.hero)
        self.assertEqual([source.key for source in sources], ["approved", "shared", "user"])
        self.assertEqual([source.writable for source in sources], [False, False, True])
        self.assertEqual(sources[0].folders, {POSE: self.hero.path("controlposes"), ANIMATION: self.hero.path("controlanims")})
        self.assertEqual(sources[1].folders, {POSE: self.biped.path("controlposes"), ANIMATION: self.biped.path("controlanims")})

    def test_the_user_source_is_below_the_projects_root_with_the_login_and_asset_id(self):
        user = library.user_source(self.hero)
        base = os.path.join(self.root, "user", "tester", "animlibrary", "shooter", "main", "characters", "hero")
        self.assertEqual(user.folders, {POSE: os.path.join(base, "controlposes"), ANIMATION: os.path.join(base, "controlanims")})

    def test_an_asset_that_uses_its_own_skeleton_has_no_shared_source(self):
        self.assertEqual([source.key for source in library.sources(self.biped)], ["approved", "user"])

    def test_an_asset_that_is_not_on_disk_still_has_its_user_library(self):
        ghost = Asset("shooter\\main\\characters\\ghost", self.root)
        self.assertEqual([source.key for source in library.sources(ghost)], ["user"])

    def test_the_registry_skips_the_user_folder_and_an_id_cannot_start_with_user(self):
        # A project whose folder is the projects root would walk into the user folder, so a stray asset.json there
        # is what the skip is for.
        top = Project.create(self.root, {"formatVersion": 2, "assetTypes": ["Other"], "fileTypes": {}})
        self.write(os.path.join(self.root, "user", "tester", "animlibrary", "asset.json"), "{}")
        registry = Registry(top, root=self.root)
        self.assertEqual(registry.errors, [])
        self.assertEqual(registry.ids(), [])
        for bad in ("user\\hero", "User\\main\\hero"):
            with self.assertRaises(AssetIdError):
                assetid.check(bad)
        assetid.check("shooter\\user\\hero")   # only a top-level folder is reserved

    def test_the_project_declares_the_vocabularies_and_a_studio_can_change_them(self):
        self.assertEqual(self.project.rig_regions, ["lowerBody", "upperBody", "head", "hands"])
        self.assertEqual(self.project.library_statuses, ["scratch", "review", "final"])
        data = {"formatVersion": 2, "rig": {"regions": ["face"]}, "library": {"statuses": ["wip"]}}
        project = Project.create(os.path.join(self.root, "other"), data)
        self.assertEqual((project.rig_regions, project.library_statuses), (["face"], ["wip"]))
        bare = Project.create(os.path.join(self.root, "bare"), {"formatVersion": 2})
        self.assertEqual((bare.rig_regions, bare.library_statuses), ([], []))


class Listing(LibraryBase):

    def test_files_are_listed_by_name_with_their_source_and_kind(self):
        self.put("user", POSE, "wave")
        self.put("user", POSE, "Idle")
        self.put("approved", POSE, "t_pose")
        self.put("user", ANIMATION, "walk")
        user = library.list_files(self.source("user"), POSE)
        self.assertEqual([(item.name, item.source, item.writable, item.legacy) for item in user],
                         [("Idle", "user", True, False), ("wave", "user", True, False)])
        self.assertEqual([item.name for item in library.list_files(self.source("approved"), POSE)], ["t_pose"])
        self.assertEqual([item.name for item in library.list_files(self.source("user"), ANIMATION)], ["walk"])
        self.assertEqual(library.list_files(self.source("shared"), POSE), [], "a folder that doesn't exist holds none")

    def test_a_legacy_json_is_listed_and_the_suffixed_file_wins_a_name(self):
        self.put("approved", POSE, "old", suffix=".json")
        self.put("approved", POSE, "both", suffix=".json")
        self.put("approved", POSE, "both")
        self.put("approved", ANIMATION, "elsewhere", suffix=".controlanim.json")
        listed = {item.name: item for item in library.list_files(self.source("approved"), POSE)}
        self.assertEqual(sorted(listed), ["both", "old"], "another kind's file is not listed")
        self.assertTrue(listed["old"].legacy)
        self.assertFalse(listed["both"].legacy)

    def test_a_pose_folder_with_an_animation_file_lists_only_poses_and_other_files_are_ignored(self):
        self.put("user", POSE, "a")
        self.put("user", POSE, "b", suffix=".controlanim.json")
        self.put("user", POSE, "c", suffix=".png")
        self.put("user", POSE, "d", suffix=".txt")
        self.assertEqual([item.name for item in library.list_files(self.source("user"), POSE)], ["a"])

    def test_free_name_takes_the_first_unused_number_counting_legacy_files(self):
        user = self.source("user")
        self.assertEqual(library.free_name(user, POSE), "pose_001")
        self.put("user", POSE, "pose_001")
        self.put("user", POSE, "pose_002", suffix=".json")
        self.assertEqual(library.free_name(user, POSE), "pose_003")
        self.assertEqual(library.free_name(user, POSE, "hand"), "hand_001")

    def test_names_that_cannot_be_file_names_are_refused(self):
        for bad in ("", "a/b", "_x", "a.b", None):
            with self.assertRaises(LibraryError, msg=repr(bad)):
                library.check_name(bad)
        self.assertEqual(library.check_name("fist 01-b"), "fist 01-b")

    def test_find_file_prefers_the_suffixed_file(self):
        folder = self.source("user").folders[POSE]
        self.assertIsNone(library.find_file(folder, POSE, "x"))
        legacy = self.put("user", POSE, "x", suffix=".json")
        self.assertEqual(library.find_file(folder, POSE, "x"), legacy)
        new = self.put("user", POSE, "x")
        self.assertEqual(library.find_file(folder, POSE, "x"), new)


class FileOperations(LibraryBase):

    def item(self, key="user", kind=POSE, name="fist", suffix=None):
        self.put(key, kind, name, suffix)
        return next(item for item in library.list_files(self.source(key), kind) if item.name == name)

    def test_rename_moves_the_file_and_its_thumbnail(self):
        item = self.item()
        thumbnail = self.put("user", POSE, "fist", suffix=".png")
        renamed = library.rename_file(item, "clench")
        folder = self.source("user").folders[POSE]
        self.assertEqual(sorted(os.listdir(folder)), ["clench.controlpose.json", "clench.png"])
        self.assertEqual((renamed.name, renamed.path), ("clench", os.path.join(folder, "clench.controlpose.json")))
        self.assertFalse(os.path.exists(thumbnail))

    def test_renaming_a_legacy_file_gives_it_the_suffix(self):
        renamed = library.rename_file(self.item(suffix=".json"), "fist")
        self.assertEqual(os.path.basename(renamed.path), "fist.controlpose.json")
        self.assertFalse(renamed.legacy)

    def test_rename_refuses_a_taken_name_and_a_read_only_source_and_changes_nothing(self):
        item = self.item()
        self.put("user", POSE, "taken", suffix=".json")
        with self.assertRaisesRegex(LibraryError, "already a pose called 'taken'"):
            library.rename_file(item, "taken")
        with self.assertRaisesRegex(LibraryError, "approved library, which can't be changed"):
            library.rename_file(self.item("approved"), "other")
        with self.assertRaises(LibraryError):
            library.rename_file(item, "a/b")
        self.assertTrue(os.path.isfile(item.path))

    def test_a_name_can_change_case_only(self):
        renamed = library.rename_file(self.item(name="fist"), "Fist")
        self.assertEqual(renamed.name, "Fist")

    def test_delete_keeps_a_local_version_and_removes_the_thumbnail(self):
        item = self.item()
        self.put("user", POSE, "fist", suffix=".png")
        library.delete_file(item, self.root)
        self.assertEqual(os.listdir(self.source("user").folders[POSE]), [])
        self.assertEqual(len(versions.list_versions(item.path, self.root)), 1)

    def test_delete_refuses_a_read_only_source(self):
        item = self.item("approved")
        with self.assertRaises(LibraryError):
            library.delete_file(item, self.root)
        self.assertTrue(os.path.isfile(item.path))

    def test_copy_to_user_copies_and_never_overwrites(self):
        item = self.item("shared", name="t_pose")
        user = self.source("user")
        target = library.copy_to_user(item, user)
        self.assertEqual(target, os.path.join(user.folders[POSE], "t_pose.controlpose.json"))
        self.assertTrue(os.path.isfile(item.path))
        with self.assertRaisesRegex(LibraryError, "already has"):
            library.copy_to_user(item, user)


class IndexCache(LibraryBase):

    def reader(self):
        calls = []

        def read(paths, context):
            calls.append((list(paths), context))
            return [FileInfo(meta={"tags": [os.path.basename(path)]}, control_count=len(calls)) for path in paths]

        return read, calls

    def files(self):
        return library.list_files(self.source("user"), POSE)

    def test_only_new_or_changed_files_are_read_again_and_in_one_call(self):
        read, calls = self.reader()
        index = library.Index(read)
        self.put("user", POSE, "a")
        self.put("user", POSE, "b")
        first = index.entries(self.files())
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0][0]), 2)
        self.assertEqual([e.tags for e in first], [["a.controlpose.json"], ["b.controlpose.json"]])

        index.entries(self.files())
        self.assertEqual(len(calls), 1, "nothing changed: nothing read")

        self.put("user", POSE, "c")
        path = self.put("user", POSE, "a")
        os.utime(path, (1, os.path.getmtime(path) + 10))
        index.entries(self.files())
        self.assertEqual(sorted(os.path.basename(p) for p in calls[1][0]), ["a.controlpose.json", "c.controlpose.json"])

    def test_a_different_context_reads_everything_again_and_forget_drops_a_file(self):
        read, calls = self.reader()
        index = library.Index(read)
        self.put("user", POSE, "a")
        index.entries(self.files(), "rigA")
        index.entries(self.files(), "rigA")
        index.entries(self.files(), "rigB")
        self.assertEqual([context for _paths, context in calls], ["rigA", "rigB"])
        index.forget(self.files()[0].path)
        index.entries(self.files(), "rigB")
        self.assertEqual(len(calls), 3)

    def test_a_reader_that_returns_the_wrong_number_of_results_is_an_error(self):
        index = library.Index(lambda paths, context: [])
        self.put("user", POSE, "a")
        with self.assertRaisesRegex(LibraryError, "0 results for 1 files"):
            index.entries(self.files())

    def test_an_entry_reads_its_fields_from_the_meta(self):
        meta = {"tags": ["hands", 3, "fist"], "rigRegions": ["hands"], "description": "Clenched", "author": "bm"}
        found = entry(**meta)
        self.assertEqual((found.tags, found.regions, found.description, found.meta("author"), found.meta("status")),
                         (["hands", "fist"], ["hands"], "Clenched", "bm", ""))


class Search(unittest.TestCase):

    def test_a_query_splits_into_words_and_terms(self):
        query = library.parse_query('hand tag:fist template:Human tag:"hard hit" "two words" nothing:here')
        self.assertEqual(query.words, ("hand", "two words", "nothing:here"))
        self.assertEqual(query.terms, (("tag", "fist"), ("template", "Human"), ("tag", "hard hit")))
        self.assertEqual(library.parse_query("  "), library.Query())
        self.assertEqual(library.parse_query("TAG:Fist").terms, (("tag", "Fist"),))
        self.assertEqual(library.parse_query("tag:").words, ("tag:",), "a term with no value is a word")

    def test_format_term_quotes_a_value_with_a_space_and_parse_reads_it_back(self):
        for field, value in (("tag", "fist"), ("tag", "hard hit")):
            self.assertEqual(library.parse_query(library.format_term(field, value)).terms, ((field, value),))

    def test_free_words_match_the_name_tags_and_description_and_every_word_must(self):
        found = entry("fist_angry", tags=["hands", "Anger"], description="Clenched right hand")
        for text in ("fist", "ANGRY", "hands", "anger", "clenched", "fist clenched hands"):
            self.assertTrue(library.matches(found, library.parse_query(text)), text)
        for text in ("fist missing", "leg"):
            self.assertFalse(library.matches(found, library.parse_query(text)), text)
        self.assertTrue(library.matches(found, library.parse_query("")))

    def test_terms_match_their_field(self):
        found = entry("a", kind=ANIMATION, source=library.APPROVED, tags=["fist", "angry"], template="Human", skeletonId="Biped",
                      author="bmorgan", category="Expressions", assetId="shooter\\hero", status="final", rigRegions=["hands", "head"])
        for text in ("tag:fis", "tag:ANGRY", "template:hum", "skeleton:biped", "by:bmorgan", "by:morg",
                     "category:express", "asset:hero", "source:approved", "kind:animation", "status:final",
                     "region:hands", "region:head", "tag:fist tag:angry"):
            self.assertTrue(library.matches(found, library.parse_query(text)), text)
        for text in ("tag:leg", "template:Dog", "by:other", "source:user", "kind:pose", "status:fin", "region:hand",
                     "source:appr", "tag:fist tag:leg", "region:legs"):
            self.assertFalse(library.matches(found, library.parse_query(text)), text)

    def test_an_entry_with_no_meta_matches_a_word_in_its_name_only(self):
        bare = entry("idle")
        self.assertTrue(library.matches(bare, library.parse_query("idle")))
        self.assertFalse(library.matches(bare, library.parse_query("tag:idle")))

    def test_filter_sorts_by_name_ignoring_case(self):
        entries = [entry("b"), entry("A"), entry("c", tags=["x"])]
        self.assertEqual([e.name for e in library.filter_entries(entries, library.Query())], ["A", "b", "c"])
        self.assertEqual([e.name for e in library.filter_entries(entries, library.parse_query("tag:x"))], ["c"])


class Masks(LibraryBase):

    def test_an_item_with_a_field_left_out_matches_anything_in_it(self):
        mask = Mask("Hands", (MaskItem(module_type="FkChain", side="Left"), MaskItem(usage="thumb")))
        self.assertTrue(mask.matches("FkChain", "Left", "index"))
        self.assertTrue(mask.matches("Aim", "Right", "thumb"))
        self.assertFalse(mask.matches("FkChain", "Right", "index"))
        self.assertFalse(Mask("None", ()).matches("FkChain", "Left", "x"))

    def test_masks_round_trip_through_a_file_with_only_the_fields_given(self):
        path = os.path.join(self.root, "masks.json")
        masks = [Mask("Hands", (MaskItem(module_type="FkChain", side="Left"), MaskItem(usage="thumb"))), Mask("All", ())]
        library.write_masks(path, masks)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["masks"][0]["items"], [{"moduleType": "FkChain", "side": "Left"}, {"usage": "thumb"}])
        self.assertEqual(library.read_masks(path, library.USER), [dataclass_with(mask, library.USER) for mask in masks])
        self.assertEqual(library.read_masks(os.path.join(self.root, "none.json"), library.USER), [])

    def test_a_file_that_is_not_a_masks_file_is_refused_with_its_path(self):
        path = os.path.join(self.root, "masks.json")
        for text in ("not json", "{}", '{"formatVersion": 1, "masks": [{"name": ""}]}',
                     '{"formatVersion": 1, "masks": [{"name": "x", "items": [{"colour": "red"}]}]}',
                     '{"formatVersion": 1, "masks": [{"name": "x", "items": [{"side": 3}]}]}'):
            self.write(path, text)
            with self.assertRaisesRegex(LibraryError, "masks.json"):
                library.read_masks(path, library.USER)
        with self.assertRaises(LibraryError):
            library.write_masks(path, [Mask("a", ()), Mask("A", ())])

    def test_a_masks_file_sits_beside_the_library_folders(self):
        self.assertEqual(library.masks_path(self.source("approved")), os.path.join(self.hero.folder, "masks.json"))
        self.assertEqual(os.path.dirname(library.masks_path(self.source("user"))),
                         os.path.dirname(self.source("user").folders[POSE]))

    def test_saved_masks_are_the_teams_then_the_users_with_a_user_mask_replacing_a_team_one(self):
        library.write_masks(library.masks_path(self.source("approved")), [
            Mask("Hands", (MaskItem(usage="hand"),)), Mask("Legs", (MaskItem(usage="leg"),))])
        library.save_mask(self.hero, Mask("hands", (MaskItem(side="Left"),)))
        library.save_mask(self.hero, Mask("Face", (MaskItem(usage="jaw"),)))
        saved = library.saved_masks(self.hero)
        self.assertEqual([(mask.name, mask.source) for mask in saved],
                         [("Face", "user"), ("hands", "user"), ("Legs", "team")])

    def test_saving_a_mask_again_replaces_it_and_delete_removes_only_your_own(self):
        library.save_mask(self.hero, Mask("Face", (MaskItem(usage="jaw"),)))
        library.save_mask(self.hero, Mask("face", (MaskItem(usage="brow"),)))
        self.assertEqual([mask.items for mask in library.saved_masks(self.hero)], [(MaskItem(usage="brow"),)])
        library.delete_mask(self.hero, "FACE")
        self.assertEqual(library.saved_masks(self.hero), [])
        with self.assertRaisesRegex(LibraryError, "no saved mask"):
            library.delete_mask(self.hero, "Face")


def dataclass_with(mask, source):
    import dataclasses
    return dataclasses.replace(mask, source=source)


if __name__ == "__main__":
    unittest.main()
