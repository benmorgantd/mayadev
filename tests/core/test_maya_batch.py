"""The batch framework end to end: a job runs in its own mayapy (started through mayalaunch, the same launcher
RigModules uses), and the results folder holds what the docs say it does.

A separate process, because MayaBatchEnvironment uninitializes Maya on exit and the other Maya tests share this
process. Needs mayapy; skips without one. Run with tests/core/run.bat.
"""
import os
import sys
import tempfile
import textwrap
import unittest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "py", "scripts"))
sys.path.insert(0, SCRIPTS)

try:
    import mayalaunch  # RigModules' python folder, on PYTHONPATH (RigModules.mod)
except ImportError:
    mayalaunch = None

JOB = textwrap.dedent('''
    import sys
    sys.path.insert(0, {scripts!r})
    from bmaya.maya.batch.maya_batch_framework import MayaBatchEnvironment, MayaStandaloneBatchPackage

    class Job(MayaStandaloneBatchPackage):
        def execute(self, item_path):
            import maya.cmds as cmds
            print("raw stdout line")
            if item_path == "bad":
                raise RuntimeError("expected failure")
            return cmds.about(batch=True), "ok"

    env = MayaBatchEnvironment(root_dir={root!r}, results_dir_name="run")
    with env:
        Job(file_list=[]).run_suite(env, open_report=False)
''')


class MayaBatchTests(unittest.TestCase):
    def setUp(self):
        if mayalaunch is None:
            self.skipTest("RigModules' python folder is not on PYTHONPATH")
        try:
            mayalaunch.mayapy_exe()
        except FileNotFoundError:
            self.skipTest("no Maya install")

    def test_job_runs_in_its_own_mayapy_and_writes_the_results_folder(self):
        with tempfile.TemporaryDirectory() as root:
            script = os.path.join(root, "job.py")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write(JOB.format(scripts=SCRIPTS, root=root))
            result = mayalaunch.run_mayapy(script, env=mayalaunch.child_environment(work_dir=root), timeout=240)
            self.assertFalse(result.timed_out)
            results = os.path.join(root, "run")
            for name in ("report_summary.md", "succeeded_files.txt", "failed_files.txt", "session_output.log"):
                self.assertTrue(os.path.isfile(os.path.join(results, name)), name)
            with open(os.path.join(results, "succeeded_files.txt"), encoding="utf-8") as handle:
                self.assertEqual(handle.read().strip(), "Blank_Scene_Execution")
            with open(os.path.join(results, "session_output.log"), encoding="utf-8") as handle:
                self.assertIn("raw stdout line", handle.read())


class BaseEnvironmentTests(unittest.TestCase):
    def test_root_dir_is_used(self):
        from bmaya.core.batch.base_batch_framework import BaseBatchEnvironment
        with tempfile.TemporaryDirectory() as root:
            env = BaseBatchEnvironment(log_dir_name="x", root_dir=root)
            self.assertEqual(env.results_dir, os.path.join(root, "x"))
            self.assertTrue(os.path.isdir(env.results_dir))

    def test_report_is_not_opened_when_told_not_to(self):
        from bmaya.core.batch.base_batch_framework import BaseBatchEnvironment, BaseBatchPackage

        opened = []

        class Job(BaseBatchPackage):
            def execute(self, item_path):
                return True, "ok"

            def _open_report(self, file_path):
                opened.append(file_path)

        with tempfile.TemporaryDirectory() as root:
            for flag, expected in ((False, 0), (True, 1)):
                opened.clear()
                env = BaseBatchEnvironment(log_dir_name="run%s" % flag, root_dir=root)
                with env:
                    Job().run_suite(env, open_report=flag)
                self.assertEqual(len(opened), expected)


if __name__ == "__main__":
    unittest.main()
