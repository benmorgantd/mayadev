import os
import logging
from bmaya.core.batch.base_batch_framework import BaseBatchEnvironment, BaseBatchPackage

class MayaBatchEnvironment(BaseBatchEnvironment):
    """Subclass managing the standalone Maya environment and native logger integration."""
    
    def __init__(self, results_dir_name=None):
        super().__init__(log_dir_name=results_dir_name, folder_prefix="mayabatch_results")
        
        home_dir = os.path.expanduser("~")
        folder_name = os.path.basename(self.results_dir)
        
        self.results_dir = os.path.join(home_dir, "Documents", "maya", "logs", folder_name)
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            
        self.log_file = os.path.join(self.results_dir, "session_output.log")

    def __enter__(self):
        import maya.standalone
        maya.standalone.initialize()
        super().__enter__()
        return self

    def _initialize_logging(self):
        import bmaya.core.log as b_log
        logger = b_log.get_logger()
        
        self._file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        log_format = "[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d] %(message)s"
        formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
        self._file_handler.setFormatter(formatter)
        self._file_handler.setLevel(logging.DEBUG)
        
        logger.addHandler(self._file_handler)

    def __exit__(self, exc_type, exc_val, exc_tb):
        import maya.standalone
        try:
            if exc_type and exc_val:
                import bmaya.core.log as b_log
                b_log.error(f"Fatal environment layout exception encountered: {exc_val}")
                
            if self._file_handler:
                import bmaya.core.log as b_log
                b_log.get_logger().removeHandler(self._file_handler)
                self._file_handler.close()
        finally:
            maya.standalone.uninitialize()


class MayaStandaloneBatchPackage(BaseBatchPackage):
    """Subclass handling Maya scene loading mechanics."""
    
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