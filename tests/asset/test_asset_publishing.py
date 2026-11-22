"""bmaya.core.asset.publishing in plain Python: the publish gates and the publish step (RigModules D70).

Run with tests/asset/run.bat, or: python -m unittest discover -s tests/asset -p "test_asset_*.py"
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.core.asset import AssetError, publishes, publishing  # noqa: E402
from bmaya.core.asset.lookstatus import LookStatus, MeshStatus  # noqa: E402
from test_asset_model import TempRoot  # noqa: E402

REST = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def joint(usage, parent=None, rest_y=0.0, name=None, rotate_order="xyz"):
    rest = list(REST)
    rest[13] = rest_y
    return {"markup": ["Center", usage], "name": name or f"{usage}_00_M_JNT", "parent": ["Center", parent] if parent else None,
            "rotateOrder": rotate_order, "restLocal": rest, "export": True, "skin": True}


def skeleton(*joints):
    return {"joints": list(joints)}


BASE = skeleton(joint("a"), joint("b", "a", 2.0), joint("c", "b", 2.0))


class BreakingChanges(unittest.TestCase):

    def changes(self, working):
        return publishing.breaking_skeleton_changes(BASE, working)

    def test_the_same_skeleton_and_a_bigger_one_break_nothing(self):
        self.assertEqual(self.changes(BASE), [])
        self.assertEqual(self.changes(skeleton(*BASE["joints"], joint("d", "c", 2.0))), [])

    def test_a_removed_joint(self):
        self.assertEqual(self.changes(skeleton(joint("a"), joint("b", "a", 2.0))), ["[Center, c] was removed"])

    def test_a_changed_parent(self):
        changes = self.changes(skeleton(joint("a"), joint("b", "a", 2.0), joint("c", "a", 2.0)))
        self.assertEqual(changes, ["[Center, c] has another parent ([Center, b] became [Center, a])"])

    def test_a_changed_name_and_rotate_order(self):
        changes = self.changes(skeleton(joint("a"), joint("b", "a", 2.0, name="spine"), joint("c", "b", 2.0, rotate_order="zyx")))
        self.assertEqual(changes, ["[Center, b] was renamed (b_00_M_JNT became spine)", "[Center, c] has another rotate order"])

    def test_a_changed_rest_but_not_float_noise(self):
        self.assertEqual(self.changes(skeleton(joint("a"), joint("b", "a", 2.0 + 1e-6), joint("c", "b", 2.0))), [])
        self.assertEqual(self.changes(skeleton(joint("a"), joint("b", "a", 2.5), joint("c", "b", 2.0))),
                         ["[Center, b] has another rest"])

    def test_a_joint_given_another_markup_is_a_removal(self):
        changes = self.changes(skeleton(joint("a"), joint("b", "a", 2.0), joint("c2", "b", 2.0)))
        self.assertEqual(changes, ["[Center, c] was removed"])


class LookBlockers(unittest.TestCase):

    def status(self, *meshes, skeleton_stale=False):
        return LookStatus("hero:lookRoot", skeleton_stale, tuple(meshes))

    def test_a_loaded_current_look_has_no_blockers(self):
        status = self.status(MeshStatus("a", "body_geo", "loaded", (), False))
        self.assertEqual(publishing.look_blockers(status, "winter", "winter"), [])

    def test_folded_rigid_and_stale_meshes_block(self):
        status = self.status(MeshStatus("a", "wrist_geo", "folded", ("a joint is gone",), False),
                             MeshStatus("b", "hat_geo", "rigid", ("the topology changed",), False),
                             MeshStatus("c", "body_geo", "loaded", (), True), skeleton_stale=True)
        self.assertEqual(publishing.look_blockers(status, "winter", "winter"), [
            "wrist_geo was folded: a joint is gone", "hat_geo was rigid: the topology changed",
            "body_geo's weight file was saved from another skeleton.", "The look's skeleton file is not the rig's."])

    def test_the_rig_must_wear_the_look_and_have_a_status(self):
        self.assertIn("wears 'summer', not 'winter'", publishing.look_blockers(self.status(), "summer", "winter")[0])
        self.assertIn("wears no look", publishing.look_blockers(None, None, "winter")[0])
        self.assertIn("not applied in this session", publishing.look_blockers(None, "winter", "winter")[0])


class RigPublish(TempRoot):

    def setUp(self):
        super().setUp()
        self.asset = self.create(skeletons=["default"], rigs=["body"])
        self.save_skeleton(BASE)

    def save_skeleton(self, data):
        self.write(self.asset.path("skeleton", "default"), json.dumps(data))

    def test_a_rig_with_no_publish_is_a_draft_and_is_never_refused(self):
        self.save_skeleton(skeleton(joint("a")))
        self.assertEqual(publishing.rig_breaking_changes(self.asset, "body"), [])
        folder = publishing.publish_rig(self.asset, "body", user="bmorgan")
        self.assertEqual(sorted(os.listdir(folder)), ["publish.json", "rig.json", "skeleton.json"])
        record = publishes.info(self.asset, "rig", "body", os.path.basename(folder))
        self.assertEqual(record["inputs"], ["rig.json", "skeleton.json"])
        self.assertNotIn("breakingChanges", record)
        self.assertIn(("add", os.path.join(folder, "skeleton.json")), self.source_control.calls)

    def test_a_rig_with_no_skeleton_saved_cannot_be_published(self):
        os.remove(self.asset.path("skeleton", "default"))
        with self.assertRaisesRegex(AssetError, "no saved skeleton"):
            publishing.publish_rig(self.asset, "body")
        self.assertIsNone(publishes.latest(self.asset, "rig", "body"))

    def test_a_skeleton_that_only_grew_publishes_again(self):
        publishing.publish_rig(self.asset, "body", user="a")
        self.save_skeleton(skeleton(*BASE["joints"], joint("d", "c", 2.0)))
        self.assertEqual(publishing.rig_breaking_changes(self.asset, "body"), [])
        folder = publishing.publish_rig(self.asset, "body", user="b")
        self.assertEqual(len(publishes.list_ids(self.asset, "rig", "body")), 2)
        with open(os.path.join(folder, "skeleton.json"), encoding="utf-8") as handle:
            self.assertEqual(len(json.load(handle)["joints"]), 4)

    def test_a_breaking_skeleton_needs_acknowledging_and_is_recorded(self):
        first = publishing.publish_rig(self.asset, "body", user="a")
        self.save_skeleton(skeleton(joint("a"), joint("b", "a", 2.0)))
        with self.assertRaisesRegex(AssetError, r"breaks the last publish.*\[Center, c\] was removed"):
            publishing.publish_rig(self.asset, "body", user="b")
        self.assertEqual(publishes.list_ids(self.asset, "rig", "body"), [os.path.basename(first)], "nothing was written")
        folder = publishing.publish_rig(self.asset, "body", acknowledged=True, user="b")
        record = publishes.info(self.asset, "rig", "body", os.path.basename(folder))
        self.assertEqual(record["breakingChanges"], ["[Center, c] was removed"])

    def test_the_baseline_is_the_latest_publish_not_the_first(self):
        publishing.publish_rig(self.asset, "body", user="a")
        self.save_skeleton(skeleton(joint("a"), joint("b", "a", 2.0)))
        publishing.publish_rig(self.asset, "body", acknowledged=True, user="b")
        self.assertEqual(publishing.rig_breaking_changes(self.asset, "body"), [], "the removal is the new baseline")

    def test_saving_a_skeleton_names_the_rigs_it_breaks(self):
        self.assertEqual(publishing.skeleton_breaking_changes(self.asset, "default"), {})
        publishing.publish_rig(self.asset, "body", user="a")
        self.save_skeleton(skeleton(joint("a")))
        self.assertEqual(publishing.skeleton_breaking_changes(self.asset, "default"),
                         {"body": ["[Center, b] was removed", "[Center, c] was removed"]})


class LookPublish(TempRoot):

    def setUp(self):
        super().setUp()
        self.asset = self.create(skeletons=["default"], looks=["winter"])
        self.write(self.asset.path("model", "winter"), "model")
        self.write(os.path.join(self.asset.path("weights", "winter"), "body_geo.json"), "{}")
        self.write(os.path.join(self.asset.path("textures", "winter"), "textures.json"), "{}")

    def test_the_publish_holds_copies_of_the_look_files(self):
        folder = publishing.publish_look(self.asset, "winter", {"rig": "body"}, user="bmorgan")
        self.assertEqual(sorted(os.listdir(folder)), ["look.json", "model", "publish.json", "textures", "weights"])
        self.assertTrue(os.path.isfile(os.path.join(folder, "weights", "body_geo.json")))
        record = publishes.info(self.asset, "look", "winter", os.path.basename(folder))
        self.assertEqual(record["rig"], "body")
        self.assertEqual(len(record["inputs"]), 4)
        self.assertTrue({"look.json", "textures", "weights"} <= set(record["inputs"]))
        self.assertEqual(publishes.latest(self.asset, "look", "winter"), os.path.basename(folder))


if __name__ == "__main__":
    unittest.main()
