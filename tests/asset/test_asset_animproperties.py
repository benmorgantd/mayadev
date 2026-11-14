"""bmaya.core.asset.animproperties in plain Python: the engine properties file of an exported clip (RigModules D42).

Run with tests/asset/run.bat, or: python -m unittest discover -s tests/asset -p "test_asset_*.py"
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.core.asset import animproperties  # noqa: E402
from bmaya.core.asset.animproperties import AnimCurve, AnimEvent, AnimProperties, AnimPropertiesError  # noqa: E402

FULL = {
    "formatVersion": 1,
    "loop": True,
    "rootMotion": True,
    "additive": "mesh",
    "events": [{"name": "footstep", "frame": 12.5}, {"name": "land", "frame": 30}],
    "curves": [{"name": "footLock_l", "keys": [[1, 0.0], [12, 1.0], [24.5, 0.25]]}],
}


class Properties(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def path(self, name="walk.animproperties.json"):
        return os.path.join(self.folder, name)

    def assertRefused(self, data, *contains):
        with self.assertRaises(AnimPropertiesError) as caught:
            AnimProperties.from_json(data)
        for text in contains:
            self.assertIn(text, str(caught.exception))

    def changed(self, **changes):
        return dict(FULL, **changes)

    def test_the_defaults_are_a_one_shot_clip_with_nothing_on_it(self):
        self.assertEqual(AnimProperties().to_json(), {
            "formatVersion": 1, "loop": False, "rootMotion": False, "additive": "none", "events": [], "curves": []})

    def test_a_full_file_reads_into_the_values_it_holds(self):
        properties = AnimProperties.from_json(FULL)
        self.assertEqual((properties.loop, properties.root_motion, properties.additive), (True, True, "mesh"))
        self.assertEqual(properties.events, (AnimEvent("footstep", 12.5), AnimEvent("land", 30.0)))
        self.assertEqual(properties.curves, (AnimCurve("footLock_l", ((1.0, 0.0), (12.0, 1.0), (24.5, 0.25))),))

    def test_write_then_read(self):
        properties = AnimProperties.from_json(FULL)
        animproperties.write(self.path(), properties)
        self.assertEqual(animproperties.read(self.path()), properties)

    def test_the_file_is_pretty_printed_json_with_the_documented_keys(self):
        animproperties.write(self.path(), AnimProperties.from_json(FULL))
        with open(self.path(), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("\n    ", text)
        self.assertEqual(sorted(json.loads(text)), ["additive", "curves", "events", "formatVersion", "loop", "rootMotion"])

    def test_the_path_is_beside_the_fbx(self):
        self.assertEqual(animproperties.get_path(os.path.join("exports", "walk", "walk.fbx")),
                         os.path.join("exports", "walk", "walk.animproperties.json"))

    def test_a_failed_write_keeps_the_old_file(self):
        animproperties.write(self.path(), AnimProperties(loop=True))
        with self.assertRaises(AttributeError):
            animproperties.write(self.path(), object())
        self.assertTrue(animproperties.read(self.path()).loop)

    def test_every_problem_is_reported_at_once(self):
        self.assertRefused(self.changed(loop="yes", additive="relative", events={}), "loop", "additive", "events")

    def test_a_format_version_this_build_does_not_read(self):
        self.assertRefused(self.changed(formatVersion=2), "formatVersion")

    def test_a_missing_key_and_an_unknown_key(self):
        data = dict(FULL)
        del data["rootMotion"]
        self.assertRefused(data, "rootMotion")
        self.assertRefused(self.changed(compression="lossy"), "unknown key 'compression'")

    def test_the_top_level_must_be_an_object(self):
        self.assertRefused([], "top level")

    def test_an_event_needs_a_name_and_a_numeric_frame(self):
        self.assertRefused(self.changed(events=[{"name": "", "frame": 1}]), "events[0].name")
        self.assertRefused(self.changed(events=[{"name": "a", "frame": "1"}]), "events[0].frame")
        self.assertRefused(self.changed(events=[{"name": "a", "frame": True}]), "events[0].frame")
        self.assertRefused(self.changed(events=[{"name": "a"}]), "events[0]")

    def test_a_curve_needs_a_unique_name_and_keys_in_increasing_frame_order(self):
        self.assertRefused(self.changed(curves=[{"name": "a", "keys": []}]), "curves[0].keys")
        self.assertRefused(self.changed(curves=[{"name": "a", "keys": [[1, 0], [1, 1]]}]), "increasing frame order")
        self.assertRefused(self.changed(curves=[{"name": "a", "keys": [[2, 0], [1, 1]]}]), "increasing frame order")
        self.assertRefused(self.changed(curves=[{"name": "a", "keys": [[1]]}]), "[frame, value]")
        self.assertRefused(self.changed(curves=[{"name": "a", "keys": [[1, 0]]}, {"name": "a", "keys": [[1, 0]]}]), "used twice")

    def test_nan_and_infinity_are_not_numbers(self):
        self.assertRefused(self.changed(events=[{"name": "a", "frame": float("nan")}]), "events[0].frame")
        self.assertRefused(self.changed(curves=[{"name": "a", "keys": [[1, float("inf")]]}]), "[frame, value]")

    def test_a_value_built_in_code_is_checked_too(self):
        with self.assertRaises(AnimPropertiesError):
            AnimProperties(additive="relative")

    def test_a_missing_file_and_a_file_that_is_not_json(self):
        with self.assertRaises(FileNotFoundError):
            animproperties.read(self.path("none.json"))
        with open(self.path(), "w", encoding="utf-8") as handle:
            handle.write("{")
        with self.assertRaises(AnimPropertiesError) as caught:
            animproperties.read(self.path())
        self.assertIn("not valid JSON", str(caught.exception))

    def test_a_file_error_names_the_file(self):
        with open(self.path(), "w", encoding="utf-8") as handle:
            json.dump(self.changed(loop=1), handle)
        with self.assertRaises(AnimPropertiesError) as caught:
            animproperties.read(self.path())
        self.assertIn("walk.animproperties.json", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
