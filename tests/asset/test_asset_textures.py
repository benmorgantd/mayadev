"""bmaya.core.asset.textures in plain Python: the textures.json sidecar, which says what image goes on which mesh and what
it is for.

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

from bmaya.core.asset import Asset, Project, textures, versions  # noqa: E402
from bmaya.core.asset.textures import Material, MeshEntry, TextureMap, TexturesError  # noqa: E402


def sample():
    return TextureMap(
        {"gun_mat": Material("standardSurface", {"baseColor": "gun_albedo.png", "normal": "gun_normal.png"}),
         "belt_mat": Material("standardSurface", {"baseColor": "sub/belt.png"})},
        {"id_gun": MeshEntry("gun_geo", "gun_mat"), "id_clip": MeshEntry("clip_geo", "gun_mat"),
         "id_belt": MeshEntry("belt_geo", "belt_mat")})


class TexturesFile(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="bmaya_textures_")
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.path = textures.get_path(self.folder)

    def write_raw(self, data):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def test_the_sidecar_is_textures_json_in_the_folder(self):
        self.assertEqual(self.path, os.path.join(self.folder, "textures.json"))

    def test_a_map_round_trips_and_the_file_is_sorted(self):
        textures.write(self.path, sample())
        self.assertEqual(textures.read(self.path), sample())
        with open(self.path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertLess(text.index("belt_mat"), text.index("gun_mat"))
        self.assertTrue(text.endswith("\n"))

    def test_meshes_that_share_a_material_and_the_files_of_the_map(self):
        texture_map = sample()
        self.assertEqual(texture_map.materials_of(["id_gun", "id_clip"]), ["gun_mat"])
        self.assertEqual(texture_map.materials_of(["id_belt", "missing"]), ["belt_mat"])
        self.assertEqual(texture_map.files(), ["gun_albedo.png", "gun_normal.png", "sub/belt.png"])

    def test_missing_files_lists_what_is_not_in_the_folder(self):
        os.makedirs(os.path.join(self.folder, "sub"))
        for name in ("gun_albedo.png", os.path.join("sub", "belt.png")):
            with open(os.path.join(self.folder, name), "wb"):
                pass
        self.assertEqual(textures.missing_files(sample(), self.folder), ["gun_normal.png"])

    def test_every_slot_of_the_shader_has_a_colour_space(self):
        self.assertEqual({slot: space for slot, space in textures.SHADERS["standardSurface"].items()},
                         {"baseColor": "sRGB", "emission": "sRGB", "normal": "Raw", "roughness": "Raw",
                          "metalness": "Raw", "opacity": "Raw"})

    def test_an_unknown_shader_or_slot_is_refused_with_the_known_ones(self):
        for material, message in ((Material("lambert", {}), "lambert"),
                                  (Material("standardSurface", {"specular": "a.png"}), "slot 'specular'")):
            with self.assertRaisesRegex(TexturesError, message):
                textures.write(self.path, TextureMap({"m": material}, {}))
        self.assertFalse(os.path.exists(self.path), "nothing is written for a map that is refused")

    def test_a_file_must_be_a_plain_relative_path(self):
        for bad in ("C:/maps/a.png", "/maps/a.png", "..\\a.png", "../a.png", "sub\\a.png", "", None):
            with self.assertRaisesRegex(TexturesError, "baseColor"):
                textures.write(self.path, TextureMap({"m": Material("standardSurface", {"baseColor": bad})}, {}))

    def test_a_mesh_must_name_a_material_the_file_has(self):
        with self.assertRaisesRegex(TexturesError, "gun_geo.*'nope'"):
            textures.write(self.path, TextureMap({}, {"id": MeshEntry("gun_geo", "nope")}))

    def test_reading_refuses_what_is_not_a_textures_file(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        with self.assertRaises(TexturesError):
            textures.read(self.path)
        for data, message in (([], "not a textures file"), ({"formatVersion": 2}, "not a textures file"),
                              ({"formatVersion": 1, "extra": 1}, "keys this version doesn't know"),
                              ({"formatVersion": 1, "materials": {"m": {}}}, "malformed"),
                              ({"formatVersion": 1, "meshes": {"id": {"meshName": "a"}}}, "malformed"),
                              ({"formatVersion": 1, "meshes": {"id": {"meshName": "a", "material": "m"}}}, "'m'")):
            self.write_raw(data)
            with self.assertRaisesRegex(TexturesError, message):
                textures.read(self.path)

    def test_a_missing_file_is_a_textures_error(self):
        with self.assertRaises(TexturesError):
            textures.read(os.path.join(self.folder, "nope.json"))

    def test_an_empty_map_is_valid(self):
        textures.write(self.path, TextureMap())
        self.assertEqual(textures.read(self.path), TextureMap())


class ImportImages(unittest.TestCase):

    def setUp(self):
        temp = tempfile.mkdtemp(prefix="bmaya_textures_import_")
        self.addCleanup(shutil.rmtree, temp, True)
        self.temp = temp
        self.root = os.path.join(temp, "projects")
        patcher = mock.patch.dict(os.environ, {"RIGGING_PROJECT_DIR": self.root,
                                               "BMAYA_VERSIONS_DIR": os.path.join(temp, "versions")})
        patcher.start()
        self.addCleanup(patcher.stop)
        Project.create(os.path.join(self.root, "shooter", "main"))
        self.hero = Asset.create("shooter\\main\\characters\\hero", "Character")
        self.folder = self.hero.path("textures", "default")
        self.scans = os.path.join(temp, "scans")
        os.makedirs(self.scans)

    def image(self, name, folder=None, data=b"x"):
        path = os.path.join(folder or self.scans, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def names(self):
        return sorted(os.listdir(self.folder))

    def test_the_convention_names_asset_look_and_kind(self):
        self.assertEqual(textures.file_name("hero", "default", "body", "albedo", ".PNG"), "hero_default_body_albedo.png")
        self.assertEqual(textures.material_name("hero", "default", "body"), "hero_default_body")
        self.assertEqual(textures.FILE_SLOTS["rough"], "roughness")

    def test_images_are_copied_in_under_the_convention_and_mapped(self):
        sources = {"albedo": self.image("skin_BC.PNG"), "normal": self.image("skin_N.tga"), "rough": self.image("skin_R.png")}
        texture_map = textures.import_images(self.hero, "default", "body", sources, {"id1": "body_geo", "id2": "head_geo"})
        self.assertEqual(self.names(), ["hero_default_body_albedo.png", "hero_default_body_normal.tga", "hero_default_body_rough.png"])
        self.assertEqual(sorted(os.listdir(self.scans)), ["skin_BC.PNG", "skin_N.tga", "skin_R.png"], "copied, not moved")
        self.assertEqual(texture_map.materials, {"hero_default_body": textures.Material("standardSurface", {
            "baseColor": "hero_default_body_albedo.png", "normal": "hero_default_body_normal.tga",
            "roughness": "hero_default_body_rough.png"})})
        self.assertEqual(texture_map.meshes, {"id1": MeshEntry("body_geo", "hero_default_body"),
                                              "id2": MeshEntry("head_geo", "hero_default_body")})
        self.assertFalse(os.path.exists(textures.get_path(self.folder)), "the map is returned, not written")

    def test_an_image_already_in_the_folder_is_copied_and_the_original_stays(self):
        os.makedirs(self.folder)
        source = self.image("skin.png", self.folder, data=b"mine")
        textures.import_images(self.hero, "default", "body", {"albedo": source}, {})
        self.assertEqual(self.names(), ["hero_default_body_albedo.png", "skin.png"])
        with open(source, "rb") as handle:
            self.assertEqual(handle.read(), b"mine")

    def test_the_originals_are_never_deleted_by_an_import_or_a_re_import(self):
        a, n = self.image("a.png"), self.image("n.png")
        textures.import_images(self.hero, "default", "body", {"albedo": a, "normal": n}, {})
        textures.import_images(self.hero, "default", "body", {"albedo": self.image("a.tga")}, {})
        self.assertEqual(sorted(os.listdir(self.scans)), ["a.png", "a.tga", "n.png"])

    def test_importing_again_keeps_the_old_image_as_a_version_and_the_other_slots(self):
        first = textures.import_images(self.hero, "default", "body", {"albedo": self.image("a.png", data=b"one"),
                                                              "normal": self.image("n.png")}, {"id1": "body_geo"})
        textures.write(textures.get_path(self.folder), first)
        again = textures.import_images(self.hero, "default", "body", {"albedo": self.image("a2.png", data=b"two")}, {"id2": "head_geo"})
        with open(os.path.join(self.folder, "hero_default_body_albedo.png"), "rb") as handle:
            self.assertEqual(handle.read(), b"two")
        copies = versions.list_versions(os.path.join(self.folder, "hero_default_body_albedo.png"), self.hero.root)
        self.assertEqual(len(copies), 1)
        with open(copies[0][1], "rb") as handle:
            self.assertEqual(handle.read(), b"one")
        self.assertEqual(again.materials["hero_default_body"].slots["normal"], "hero_default_body_normal.png", "kept")
        self.assertEqual(sorted(again.meshes), ["id1", "id2"], "the earlier mesh stays mapped")

    def test_another_extension_replaces_the_old_file_of_that_kind(self):
        textures.import_images(self.hero, "default", "body", {"albedo": self.image("a.png")}, {})
        again = textures.import_images(self.hero, "default", "body", {"albedo": self.image("a.tga")}, {})
        self.assertEqual(self.names(), ["hero_default_body_albedo.tga"])
        self.assertEqual(again.materials["hero_default_body"].slots["baseColor"], "hero_default_body_albedo.tga")
        self.assertEqual(len(versions.list_versions(os.path.join(self.folder, "hero_default_body_albedo.png"), self.hero.root)), 1)

    def test_each_look_has_its_own_names(self):
        textures.import_images(self.hero, "winter", "body", {"albedo": self.image("a.png")}, {})
        self.assertEqual(os.listdir(self.hero.path("textures", "winter")), ["hero_winter_body_albedo.png"])

    def test_a_second_material_leaves_the_first_alone_and_a_shared_mesh_moves(self):
        body = textures.import_images(self.hero, "default", "body", {"albedo": self.image("b.png")},
                                      {"id_body": "body_geo", "id_gun": "gun_geo"})
        textures.write(textures.get_path(self.folder), body)
        both = textures.import_images(self.hero, "default", "head", {"albedo": self.image("h.png", data=b"head")},
                                      {"id_head": "head_geo"})
        self.assertEqual(sorted(both.materials), ["hero_default_body", "hero_default_head"])
        self.assertEqual(both.materials["hero_default_body"].slots, {"baseColor": "hero_default_body_albedo.png"})
        self.assertEqual({i: e.material for i, e in both.meshes.items()},
                         {"id_body": "hero_default_body", "id_gun": "hero_default_body", "id_head": "hero_default_head"})
        self.assertEqual(self.names(), ["hero_default_body_albedo.png", "hero_default_head_albedo.png", "textures.json"])

    def test_a_material_no_mesh_wears_any_more_is_dropped_but_its_images_stay(self):
        body = textures.import_images(self.hero, "default", "body", {"albedo": self.image("b.png")}, {"id_a": "a_geo"})
        textures.write(textures.get_path(self.folder), body)
        moved = textures.import_images(self.hero, "default", "prop", {"albedo": self.image("p.png")}, {"id_a": "a_geo"})
        self.assertEqual(sorted(moved.materials), ["hero_default_prop"])
        self.assertIn("hero_default_body_albedo.png", self.names())

    def test_the_material_part_must_be_a_plain_name(self):
        for part in ("", "my body", "1body", "a_b", "a/b", None):
            with self.assertRaisesRegex(TexturesError, "not a material name"):
                textures.import_images(self.hero, "default", part, {"albedo": self.image("a.png")}, {})
        self.assertFalse(os.path.exists(self.folder))

    def test_nothing_is_touched_when_one_image_is_wrong(self):
        for sources, message in (({"albedo": self.image("a.png"), "shine": self.image("s.png")}, "not an image kind"),
                                 ({"albedo": os.path.join(self.scans, "missing.png")}, "not a file"),
                                 ({"albedo": self.image("notes.txt")}, "not an image type"),
                                 ({}, "at least one")):
            with self.assertRaisesRegex(TexturesError, message):
                textures.import_images(self.hero, "default", "body", sources, {})
        self.assertFalse(os.path.exists(self.folder), "no folder is made for a refused import")

    def test_an_invalid_textures_file_stops_the_import_before_a_file_is_copied(self):
        os.makedirs(self.folder)
        with open(textures.get_path(self.folder), "w", encoding="utf-8") as handle:
            handle.write("{not json")
        with self.assertRaises(TexturesError):
            textures.import_images(self.hero, "default", "body", {"albedo": self.image("a.png")}, {})
        self.assertEqual(self.names(), ["textures.json"])


if __name__ == "__main__":
    unittest.main()
