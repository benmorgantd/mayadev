import os

try:
    import mayalaunch  # RigModules' python folder, put on PYTHONPATH by RigModules.mod
except ImportError as import_error:
    raise ImportError("mayalaunch comes from RigModules (its python folder): put it on PYTHONPATH.") from import_error
from bmaya.core.batch.base_batch_framework import BaseBatchEnvironment, BaseBatchPackage


class MayaBatchEnvironment(BaseBatchEnvironment):
    """Subclass managing the standalone Maya environment and native logger integration."""
    
    DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), "Documents", "maya", "mayabatch_logs")

    def __init__(self, results_dir_name=None, root_dir=None):
        super().__init__(log_dir_name=results_dir_name, folder_prefix="mayabatch_results", root_dir=root_dir)

        self._redirect = None

    def __enter__(self):
        # Output goes to the log at the OS level (Maya's C++ output) and the Python level (prevents WinError 6
        # on sys.stdout.flush). mayalaunch owns that and Maya's start and stop (it is shared with RigModules).
        self._redirect = mayalaunch.Redirect(self.log_file, python_streams=True, mode="w")
        # The batch runs the user's userSetup.py: bmaya.core.log is initialized by this environment itself.
        mayalaunch.start_standalone(skip_usersetup=False)
        super().__enter__()
        return self

    def _initialize_logging(self):
        import bmaya.core.log as b_log
        b_log.init_logger()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type and exc_val:
                import bmaya.core.log as b_log
                b_log.error(f"Fatal environment layout exception encountered: {exc_val}")
        finally:
            super().__exit__(exc_type, exc_val, exc_tb)
            mayalaunch.stop_standalone()
            self._redirect.stop()


class MayaStandaloneBatchPackage(BaseBatchPackage):
    """Subclass implementing automated asset canvas loading actions for Maya."""
    
    def _prepare_item(self, item_path, idx, total):
        import maya.cmds as cmds
        import bmaya.core.log as b_log
        
        if item_path is None:
            b_log.info(f"[{idx}/{total}] Initializing blank testing scene canvas...")
            cmds.file(new=True, force=True)
            return "Blank_Scene_Execution"
            
        b_log.info(f"[{idx}/{total}] Loading scene file targets: {item_path}")
        cmds.file(item_path, open=True, force=True)
        return item_path