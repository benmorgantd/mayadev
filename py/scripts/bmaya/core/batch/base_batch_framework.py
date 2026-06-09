import os
import sys
import json
import inspect
import shutil
import traceback
import logging
from datetime import datetime

class BaseBatchEnvironment:
    """Pure Python context manager handling filesystem initialization and basic logging."""
    
    def __init__(self, log_dir_name=None, folder_prefix="batch_results"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = log_dir_name or f"{folder_prefix}_{timestamp}"
        
        home_dir = os.path.expanduser("~")
        self.results_dir = os.path.join(home_dir, "Documents", "batch", "logs", folder_name)
        
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            
        self.log_file = os.path.join(self.results_dir, "session_output.log")
        self._file_handler = None

    def __enter__(self):
        self._initialize_logging()
        return self

    def _initialize_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        self._file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        self._file_handler.setFormatter(formatter)
        logger.addHandler(self._file_handler)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file_handler:
            logger = logging.getLogger()
            logger.removeHandler(self._file_handler)
            self._file_handler.close()


class BaseBatchPackage:
    """Ancestor class for all file-batching operations and test cases."""
    
    def __init__(self, file_list=None, config_source_path=None):
        self.file_list = file_list or []
        self.config_source_path = config_source_path
        self.succeeded = []
        self.failed = []

    @classmethod
    def from_json(cls, json_path):
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Configuration profile missing: {json_path}")
            
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return cls(file_list=data.get("file_list", []), config_source_path=json_path)

    def execute(self, item_path):
        """Core execution hook. Must be overridden by individual test classes.
        
        Returns:
            tuple: (bool success, str message)
        """
        raise NotImplementedError("Subclasses must implement the execute method.")

    def run_suite(self, environment):
        self._write_manifest(environment.results_dir)
        
        processing_queue = self.file_list if self.file_list else [None]
        total_items = len(processing_queue)
        
        for idx, item_path in enumerate(processing_queue, 1):
            try:
                current_id = self._prepare_item(item_path, idx, total_items)
            except Exception as prep_err:
                fallback_id = item_path if item_path else "Blank_Execution"
                self.failed.append((fallback_id, f"Environment preparation crash: {prep_err}"))
                continue

            try:
                # The class now routes directly into its own instance execution method
                success, message = self.execute(item_path)
                if success:
                    self.succeeded.append(current_id)
                else:
                    self.failed.append((current_id, message))
            except Exception as script_err:
                err_msg = f"Unhandled Exception during execution:\n{traceback.format_exc()}"
                self.failed.append((current_id, err_msg))

        self._write_output_artifacts(environment.results_dir)

    def _prepare_item(self, item_path, idx, total):
        if item_path is None:
            return "Blank_Execution"
        return item_path

    def _write_manifest(self, output_dir):
        try:
            script_file = inspect.getfile(self.__class__)
            shutil.copy(script_file, os.path.join(output_dir, "executed_script.py"))
        except Exception:
            with open(os.path.join(output_dir, "executed_script.py"), "w", encoding="utf-8") as sf:
                sf.write(inspect.getsource(self.__class__))

        manifest_data = {
            "test_class": self.__class__.__name__,
            "file_list": self.file_list,
            "original_config_source": self.config_source_path,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(os.path.join(output_dir, "batch_config.json"), "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf, indent=4)

    def _write_output_artifacts(self, output_dir):
        with open(os.path.join(output_dir, "processed_files.txt"), "w", encoding="utf-8") as f:
            if self.file_list:
                f.writelines(f"{p}\n" for p in self.file_list)
            else:
                f.write("Blank_Scene_Execution\n")

        with open(os.path.join(output_dir, "succeeded_files.txt"), "w", encoding="utf-8") as f:
            f.writelines(f"{p}\n" for p in self.succeeded)

        with open(os.path.join(output_dir, "failed_files.txt"), "w", encoding="utf-8") as f:
            for path, error in self.failed:
                f.write(f"ENTRY: {path}\nEXCEPTION:\n{error}\n{'-'*40}\n")