import os
import sys
from bmaya.core.batch.base_batch_framework import BaseBatchEnvironment, BaseBatchPackage


class MayaBatchEnvironment(BaseBatchEnvironment):
    """Subclass managing the standalone Maya environment and native logger integration."""
    
    def __init__(self, results_dir_name=None):
        super().__init__(log_dir_name=results_dir_name, folder_prefix="mayabatch_results")
        
        home_dir = os.path.expanduser("~")
        folder_name = os.path.basename(self.results_dir)
        
        self.results_dir = os.path.join(home_dir, "Documents", "maya", "mayabatch_logs", folder_name)
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            
        self.log_file = os.path.join(self.results_dir, "session_output.log")
        
        self._log_file_handle = None
        self._saved_stdout_fd = None
        self._saved_stderr_fd = None
        self._orig_stdout = None
        self._orig_stderr = None

    def __enter__(self):
        os.environ["BMAYA_BATCH_MODE"] = "1"
        
        # 1. Open the physical file handle
        self._log_file_handle = open(self.log_file, "w", encoding="utf-8")
        file_fd = self._log_file_handle.fileno()
        
        # 2. Save original low-level OS file descriptors (1=stdout, 2=stderr)
        self._saved_stdout_fd = os.dup(1)
        self._saved_stderr_fd = os.dup(2)
        
        # 3. Save original high-level Python stream objects
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        
        # 4. Redirect at the OS level (captures raw C++ engine noise)
        os.dup2(file_fd, 1)
        os.dup2(file_fd, 2)
        
        # 5. Redirect at the Python level (prevents WinError 6 on sys.stdout.flush)
        sys.stdout = self._log_file_handle
        sys.stderr = self._log_file_handle
        
        import maya.standalone
        maya.standalone.initialize()
        
        super().__enter__()
        return self

    def _initialize_logging(self):
        import bmaya.core.log as b_log
        b_log.init_logger()

    def __exit__(self, exc_type, exc_val, exc_tb):
        import maya.standalone
        try:
            if exc_type and exc_val:
                import bmaya.core.log as b_log
                b_log.error(f"Fatal environment layout exception encountered: {exc_val}")
        finally:
            super().__exit__(exc_type, exc_val, exc_tb)
            maya.standalone.uninitialize()
            
            # 6. Restore high-level Python objects
            if self._orig_stdout:
                sys.stdout = self._orig_stdout
            if self._orig_stderr:
                sys.stderr = self._orig_stderr
                
            # 7. Restore low-level OS handles
            if self._saved_stdout_fd is not None:
                os.dup2(self._saved_stdout_fd, 1)
                os.close(self._saved_stdout_fd)
            if self._saved_stderr_fd is not None:
                os.dup2(self._saved_stderr_fd, 2)
                os.close(self._saved_stderr_fd)
                
            # 8. Close the file handle completely
            if self._log_file_handle:
                self._log_file_handle.close()
                
            if "BMAYA_BATCH_MODE" in os.environ:
                del os.environ["BMAYA_BATCH_MODE"]


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