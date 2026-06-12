"""Framework for launching batch scripts over a list of files, which also handles log output and organization."""

import os
import sys
import json
import inspect
import shutil
import traceback
import logging
import subprocess
from datetime import datetime


class BaseBatchEnvironment:
    """Pure Python context manager handling filesystem initialization and basic logging."""

    def __init__(
        self, log_dir_name: str | None = None, folder_prefix: str = "batch_results"
    ) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = log_dir_name or f"{folder_prefix}_{timestamp}"

        home_dir = os.path.expanduser("~")
        self.results_dir = os.path.join(
            home_dir, "Documents", "batch", "logs", folder_name
        )

        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

        self.log_file = os.path.join(self.results_dir, "session_output.log")
        self._file_handler = None

    def __enter__(self) -> "BaseBatchEnvironment":
        self._initialize_logging()
        return self

    def _initialize_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        self._file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "[%(asctime)s][%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        self._file_handler.setFormatter(formatter)
        logger.addHandler(self._file_handler)

    def close_logging(self):
        """Explicitly shutdown and remove the file handler to allow reading/releasing the log."""
        if self._file_handler:
            logger = logging.getLogger()
            logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_logging()


class BaseBatchPackage:
    """Ancestor class for all file-batching operations and test cases."""

    def __init__(
        self, file_list: list | None = None, config_source_path: str | None = None
    ):
        self.file_list = file_list or []
        self.config_source_path = config_source_path
        self.succeeded = []
        self.failed = []

    @classmethod
    def from_json(cls, json_path: str) -> "BaseBatchPackage":
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Configuration profile missing: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(file_list=data.get("file_list", []), config_source_path=json_path)

    def execute(self, item_path: str | None) -> tuple[bool, str]:
        """Core execution hook. Must be overridden by individual test classes.

        Returns:
            tuple: (bool success, str message)
        """
        raise NotImplementedError("Subclasses must implement the execute method.")

    def run_suite(self, environment: BaseBatchEnvironment) -> None:
        self._write_manifest(environment.results_dir)

        processing_queue = self.file_list if self.file_list else [None]
        total_items = len(processing_queue)

        for idx, item_path in enumerate(processing_queue, 1):
            try:
                current_id = self._prepare_item(item_path, idx, total_items)
            except Exception as prep_err:
                fallback_id = item_path if item_path else "Blank_Execution"
                print(f"Environment preparation crash: {prep_err}")
                self.failed.append(
                    (fallback_id, f"Environment preparation crash: {prep_err}")
                )
                continue

            try:
                success, message = self.execute(item_path)
                if success:
                    self.succeeded.append(current_id)
                else:
                    self.failed.append((current_id, message))
            except Exception as script_err:
                err_msg = (
                    f"Unhandled Exception during execution:\n{traceback.format_exc()}"
                )
                print(err_msg)
                self.failed.append((current_id, err_msg))

        self._write_output_artifacts(environment.results_dir)

        # Flush and close logging early so the markdown builder can safely read the log file
        environment.close_logging()

        summary_file = self._write_summary_markdown(
            environment.results_dir, environment.log_file
        )

        # Automatically show report on completion
        self._open_report(summary_file)

    def _prepare_item(self, item_path: str | None, idx: int, total: int) -> str:
        if item_path is None:
            return "Blank_Execution"
        return item_path

    def _write_manifest(self, output_dir: str) -> None:
        try:
            script_file = inspect.getfile(self.__class__)
            shutil.copy(script_file, os.path.join(output_dir, "executed_script.py"))
        except Exception:
            with open(
                os.path.join(output_dir, "executed_script.py"), "w", encoding="utf-8"
            ) as sf:
                sf.write(inspect.getsource(self.__class__))

        manifest_data = {
            "test_class": self.__class__.__name__,
            "file_list": self.file_list,
            "original_config_source": self.config_source_path,
            "timestamp": datetime.now().isoformat(),
        }

        with open(
            os.path.join(output_dir, "batch_config.json"), "w", encoding="utf-8"
        ) as mf:
            json.dump(manifest_data, mf, indent=4)

    def _write_output_artifacts(self, output_dir: str) -> None:
        with open(
            os.path.join(output_dir, "processed_files.txt"), "w", encoding="utf-8"
        ) as f:
            if self.file_list:
                f.writelines(f"{p}\n" for p in self.file_list)
            else:
                f.write("Blank_Scene_Execution\n")

        with open(
            os.path.join(output_dir, "succeeded_files.txt"), "w", encoding="utf-8"
        ) as f:
            f.writelines(f"{p}\n" for p in self.succeeded)

        with open(
            os.path.join(output_dir, "failed_files.txt"), "w", encoding="utf-8"
        ) as f:
            for path, error in self.failed:
                f.write(f"ENTRY: {path}\nEXCEPTION:\n{error}\n{'-'*40}\n")

    def _write_summary_markdown(self, output_dir: str, log_file_path: str) -> str:
        """Generates a comprehensive Markdown report summarizing the batch operation."""
        total_count = len(self.file_list) if self.file_list else 1
        success_count = len(self.succeeded)
        failed_count = len(self.failed)

        overall_status = "🟢 PASSED" if failed_count == 0 else "🔴 FAILED"

        md_lines = [
            f"# 📊 Batch Execution Summary ({overall_status})",
            f"**Engine Class:** `{self.__class__.__name__}`  ",
            f"**Date/Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Config Source:** `{self.config_source_path or 'Direct Execution'}`",
            "",
            "## 📈 Status Breakdown",
            f"- 📦 **Total Processed:** {total_count}",
            f"- ✅ **Succeeded:** {success_count} / {total_count}",
            f"- ❌ **Failed:** {failed_count} / {total_count}",
            "",
        ]

        # Succeeded Section
        md_lines.append("## ✅ Succeeded Items")
        if self.succeeded:
            for item in self.succeeded:
                md_lines.append(f"- 🟢 `{item}`")
        else:
            md_lines.append("*No items completed successfully.*")
        md_lines.append("")

        # Failed Section
        md_lines.append("## ❌ Failed Items")
        if self.failed:
            for idx, (path, error) in enumerate(self.failed, 1):
                md_lines.extend(
                    [
                        f"### {idx}. Target: `{path}`",
                        "```text",
                        f"{error.strip()}",
                        "```",
                        "",
                    ]
                )
        else:
            md_lines.append("*No failures encountered.*")
        md_lines.append("")

        # Embedded Session Log Section
        md_lines.append("## 📜 Session Log Output")
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, "r", encoding="utf-8") as lf:
                    log_content = lf.read().strip()

                if log_content:
                    md_lines.extend(["```text", log_content, "```"])
                else:
                    md_lines.append("*Log file was empty.*")
            except Exception as log_read_err:
                md_lines.append(f"⚠️ *Failed to read log contents:* `{log_read_err}`")
        else:
            md_lines.append("⚠️ *Log file not found.*")

        summary_path = os.path.join(output_dir, "report_summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        return summary_path

    def _open_report(self, file_path: str) -> None:
        """Cross-platform utility to open the generated file in the default OS application."""
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
        except Exception as e:
            print(f"Failed to automatically open the report file: {e}")
