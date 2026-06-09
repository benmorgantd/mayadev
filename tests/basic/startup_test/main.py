import os
from bmaya.maya.batch.runner import run_batch_test
from bmaya.maya.batch.maya_batch_framework import MayaStandaloneBatchPackage

class TestMayaStartup(MayaStandaloneBatchPackage):
    """Class-based test layout to verify node conditions across files."""

    def execute(self, item_path):
        """Your explicit test logic here."""
        import maya.cmds as cmds
        import bmaya.core.log
        
        bmaya.core.log.info("Maya startup complete!")
        return True, "Maya startup complete"


if __name__ == '__main__':
    # Define files to process, or keep empty to trigger the 1-blank-scene fallback loop
    target_files = []
    
    # Execute via the centralized bootstrap framework runner
    run_batch_test(TestMayaStartup, file_list=target_files)