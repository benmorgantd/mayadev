import os
import sys
from bmaya.core.batch.base_batch_framework import BaseBatchEnvironment, BaseBatchPackage


class StreamTee(object):
    """Intercepts and mirrors standard stream writes to both the terminal and a log file."""
    
    def __init__(self, original_stream, file_object):
        self.original_stream = original_stream
        self.file_object = file_object

    def write(self, data):
        # Handle cases where data might be passed as bytes or empty strings safely
        if data:
            self.original_stream.write(data)
            self.file_object.write(data)
            # Optional: flush frequently so logs write out in real-time
            self.file_object.flush()

    def flush(self):
        self.original_stream.flush()
        self.file_object.flush()


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
        
        self._file_stream = None
        self._orig_stdout = None
        self._orig_stderr = None

    def __enter__(self):
        # 1. Flag batch context before modules configure logging handlers
        os.environ["BMAYA_BATCH_MODE"] = "1"
        
        import maya.standalone
        
        # 2. Wake up the engine core
        maya.standalone.initialize()
        
        # 3. Open the file stream
        self._file_stream = open(self.log_file, "w", encoding="utf-8")
        
        # 4. Wrap active streams AFTER Maya initialization to prevent Maya from wiping them
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        
        sys.stdout = StreamTee(self._orig_stdout, self._file_stream)
        sys.stderr = StreamTee(self._orig_stderr, self._file_stream)
        
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
            
            # 5. Restore original terminal streams and close the file handle cleanly
            if self._orig_stdout:
                sys.stdout = self._orig_stdout
            if self._orig_stderr:
                sys.stderr = self._orig_stderr
                
            if self._file_stream:
                self._file_stream.flush()
                self._file_stream.close()
                
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