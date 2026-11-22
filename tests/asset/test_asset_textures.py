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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.core.asset import textures  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
