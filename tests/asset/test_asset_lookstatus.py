"""bmaya.core.asset.lookstatus in plain Python: the report cmds.setRigLook returns (RigModules D70), as data.

Run with tests/asset/run.bat, or: python -m unittest discover -s tests/asset -p "test_asset_*.py"
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "py", "scripts"))

from bmaya.core.asset.lookstatus import FOLDED, LOADED, RIGID, LookStatus, MeshStatus  # noqa: E402

REPORT = {"lookRoot": "hero:lookRoot", "skeletonStale": False, "meshes": [
    {"meshId": "a", "meshName": "body_geo", "result": "loaded", "reasons": [], "staleSkeleton": False},
    {"meshId": "b", "meshName": "wrist_geo", "result": "folded",
     "reasons": ["[Left, wristTwist] is not a joint of the rig, so its weight went to [Left, wrist]"], "staleSkeleton": True},
    {"meshId": "c", "meshName": "hat_geo", "result": "rigid", "reasons": ["the mesh's topology changed"], "staleSkeleton": False}]}


class Parse(unittest.TestCase):

    def test_reads_what_set_rig_look_returns(self):
        status = LookStatus.parse(json.dumps(REPORT))
        self.assertEqual(status.look_root, "hero:lookRoot")
        self.assertEqual([(m.mesh_id, m.result) for m in status.meshes], [("a", LOADED), ("b", FOLDED), ("c", RIGID)])
        self.assertEqual(status.meshes[1].reasons, ("[Left, wristTwist] is not a joint of the rig, so its weight went to [Left, wrist]",))

    def test_a_report_that_is_not_one_is_a_value_error(self):
        for text in ("hero:lookRoot", "{}", json.dumps({"lookRoot": "x"}), "[1]"):
            with self.assertRaises(ValueError, msg=text):
                LookStatus.parse(text)


class Reading(unittest.TestCase):

    def setUp(self):
        self.status = LookStatus.parse(json.dumps(REPORT))

    def test_a_mesh_needs_a_save_when_it_is_not_loaded_or_is_stale(self):
        self.assertEqual([m.needs_save for m in self.status.meshes], [False, True, True])
        stale_only = MeshStatus("d", "d_geo", LOADED, (), True)
        self.assertTrue(stale_only.needs_save)
        self.assertEqual(stale_only.text, "saved from another skeleton")

    def test_text_joins_the_reasons_then_the_stale_mark(self):
        self.assertEqual(self.status.meshes[1].text,
                         "[Left, wristTwist] is not a joint of the rig, so its weight went to [Left, wrist]; saved from another skeleton")
        self.assertEqual(self.status.meshes[0].text, "")

    def test_summary_counts_each_result_and_the_stale_files(self):
        self.assertEqual(self.status.summary, "3 mesh(es): 1 loaded, 1 folded, 1 rigid, 1 stale")

    def test_the_look_needs_a_save_while_any_mesh_does(self):
        self.assertTrue(self.status.needs_save)
        self.assertFalse(self.status.saved({"b", "c"}).needs_save)

    def test_saved_meshes_read_as_loaded_and_the_others_are_untouched(self):
        after = self.status.saved({"c"})
        self.assertEqual([(m.result, m.reasons, m.stale_skeleton) for m in after.meshes],
                         [(LOADED, (), False), (FOLDED, self.status.meshes[1].reasons, True), (LOADED, (), False)])
        self.assertEqual(self.status.meshes[2].result, RIGID, "the status is immutable")

    def test_a_stale_look_skeleton_stays_until_the_next_build(self):
        status = LookStatus("x", True, ())
        self.assertTrue(status.needs_save)
        self.assertTrue(status.saved({"a"}).skeleton_stale)


if __name__ == "__main__":
    unittest.main()
