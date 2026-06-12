import os
import sys
import inspect
import subprocess

# Establish path roots immediately so mayapy can discover the framework structures
repo_root = os.environ.get("MAYADEV_ROOT")
if not repo_root:
    raise RuntimeError("Environment variable 'MAYADEV_ROOT' is not defined.")

scripts_path = os.path.abspath(os.path.join(repo_root, "py", "scripts"))
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

# Safe base framework import
from bmaya.maya.batch.maya_batch_framework import MayaStandaloneBatchPackage


class CodebaseDocGenerator(MayaStandaloneBatchPackage):
    """Dynamic codebase parser running inside standard headless Maya standalone environments.

    Inspects live class and function symbols to write matching static markdown sheets.
    """

    def __init__(self, file_list=None):
        super(CodebaseDocGenerator, self).__init__(file_list=file_list)

        self.source_root = os.path.join(repo_root, "py", "scripts", "bmaya")
        self.docs_root = os.path.join(repo_root, "py", "scripts", "docs")
        self.mkdocs_yaml = os.path.join(repo_root, "py", "scripts", "mkdocs.yml")

        self.discovered_api_pages = []

    def _prepare_item(self, item_path, idx, total):
        """Overrides the default scene file loader to process Python source files as raw paths."""
        from bmaya.core import log

        log.info(f"[{idx}/{total}] Processing script module definitions: {item_path}")
        return item_path

    def execute(self, item_path):
        """Introspects an active file item loaded within the mayapy environment pool."""
        from bmaya.core import log

        if (
            not item_path
            or not item_path.endswith(".py")
            or os.path.basename(item_path) == "__init__.py"
        ):
            return True, "Skipped initialization/non-python file"

        # Calculate module dot-notation paths relative to package structure
        relative_path = os.path.relpath(item_path, self.source_root)
        module_name_str = "bmaya." + os.path.splitext(relative_path)[0].replace(
            os.sep, "."
        )

        try:
            # Force target module import or reload inside the live session context
            if module_name_str in sys.modules:
                import importlib

                mod_obj = importlib.reload(sys.modules[module_name_str])
            else:
                mod_obj = __import__(module_name_str, fromlist=[""])
        except Exception as err:
            log.error(
                f"Execution module import breakdown on {module_name_str}: {str(err)}"
            )
            return False, f"ImportError: {str(err)}"

        module_doc = inspect.getdoc(mod_obj) or "No module documentation provided."

        md_output = [
            f"# Reference Component: `{module_name_str}`",
            "",
            "## Module Level Context",
            module_doc,
            "",
            "---",
            "## Object Taxonomy Reference",
            "",
        ]

        # Scan members belonging directly to this specific module space
        for member_name, member_obj in inspect.getmembers(mod_obj):
            if (
                inspect.isclass(member_obj)
                and member_obj.__module__ == mod_obj.__name__
            ):
                md_output.extend(self._parse_class_symbols(member_name, member_obj))
            elif (
                inspect.isfunction(member_obj)
                and member_obj.__module__ == mod_obj.__name__
            ):
                md_output.extend(
                    self._parse_function_symbols(
                        member_name, member_obj, heading_str="###"
                    )
                )

        # Target dynamic parallel writing location
        output_rel_md = os.path.splitext(relative_path)[0] + ".md"
        target_md_file = os.path.join(self.docs_root, "rigging", output_rel_md)

        os.makedirs(os.path.dirname(target_md_file), exist_ok=True)

        with open(target_md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(md_output))

        # Capture complete web-relative navigation target string (Fixes the 404 targets)
        web_relative_nav = ("rigging/" + output_rel_md).replace(os.sep, "/")
        self.discovered_api_pages.append(web_relative_nav)

        return True, f"Successfully built reference page: {target_md_file}"

    def _parse_class_symbols(self, class_name, class_obj):
        """Extracts docstrings and child tracking metrics for code classes."""
        class_doc = inspect.getdoc(class_obj) or "No class descriptions detailed."
        lines = [
            f"### 🏷️ `CLASS` :: **{class_name}**",
            "",
            "**Description Summary:**",
            class_doc,
            "",
            "#### Methods & Interceptors",
            "",
        ]

        for method_name, method_obj in inspect.getmembers(
            class_obj, predicate=inspect.isfunction
        ):
            # Filter internal private functions but keep explicit tracking core handlers
            if method_name.startswith("_") and not method_name.startswith("__"):
                if method_name != "_register_core":
                    continue
            if (
                method_name.startswith("__")
                and method_name.endswith("__")
                and method_name != "__init__"
            ):
                continue

            lines.extend(
                self._parse_function_symbols(
                    method_name, method_obj, heading_str="####"
                )
            )
            lines.append("")

        lines.append("\n---")
        return lines

    def _parse_function_symbols(self, func_name, func_obj, heading_str):
        """Extracts parameters, runtime signatures, and Google docstring data layout blocks."""
        try:
            func_sig = inspect.signature(func_obj)
        except (ValueError, TypeError):
            func_sig = "(...)"

        func_doc = (
            inspect.getdoc(func_obj)
            or "No functional arguments or usage blocks specified."
        )

        lines = [
            f"{heading_str} 🛠️ `{func_name}{func_sig}`",
            "",
            "```text",
            func_doc,
            "```",
            "",
        ]
        return lines

    def post_suite_callback(self):
        """Runs automatically after all modules have been processed to sync the nav index and launch server."""
        from bmaya.core import log

        log.info("Updating navigation maps inside mkdocs.yml...")

        # Find all handwritten user manual files inside docs/guides/
        guide_pages = []
        guides_dir = os.path.join(self.docs_root, "guides")
        if os.path.exists(guides_dir):
            for root, _, files in os.walk(guides_dir):
                for file in files:
                    if file.endswith(".md"):
                        full_p = os.path.join(root, file)
                        rel_p = os.path.relpath(full_p, self.docs_root)
                        guide_pages.append(rel_p.replace(os.sep, "/"))

        guide_pages.sort()
        self.discovered_api_pages.sort()

        nav_lines = ["nav:", "  - Home: index.md"]

        if guide_pages:
            nav_lines.append("  - Manual Guides:")
            for page in guide_pages:
                label = (
                    os.path.basename(page).replace(".md", "").replace("_", " ").title()
                )
                nav_lines.append(f"      - {label}: {page}")

        if self.discovered_api_pages:
            nav_lines.append("  - API Reference:")
            categories = {}
            for page in self.discovered_api_pages:
                parts = page.split("/")  # ['rigging', 'core', 'eventsregistry.md']
                if len(parts) > 2:
                    cat = parts[1].title()
                    categories.setdefault(cat, []).append(page)
                else:
                    categories.setdefault("General", []).append(page)

            for cat_name, pages in sorted(categories.items()):
                nav_lines.append(f"      - {cat_name}:")
                for page in pages:
                    label = (
                        os.path.splitext(os.path.basename(page))[0]
                        .replace("_", " ")
                        .title()
                    )
                    nav_lines.append(f"          - {label}: {page}")

        if os.path.exists(self.mkdocs_yaml):
            cleaned_base_lines = []
            with open(self.mkdocs_yaml, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("nav:"):
                        break
                    cleaned_base_lines.append(line.rstrip())

            final_yaml_content = (
                "\n".join(cleaned_base_lines) + "\n" + "\n".join(nav_lines) + "\n"
            )

            with open(self.mkdocs_yaml, "w", encoding="utf-8") as f:
                f.write(final_yaml_content)
            log.info(f"Successfully updated configuration maps: {self.mkdocs_yaml}")

        # Kick off background hidden web server
        self._start_background_docs_server()

    def _start_background_docs_server(self):
        """Assembles and fires a windowless VBScript layer to host the documentation server."""
        from bmaya.core import log

        log.info("Initializing background documentation web server hosting...")

        yaml_working_dir = os.path.abspath(os.path.join(self.docs_root, ".."))
        temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
        vbs_script_path = os.path.join(temp_dir, "launch_mkdocs_hidden.vbs")

        # Compile windowless script allocation lines
        vbs_lines = [
            'Set WshShell = CreateObject("WScript.Shell")',
            f'WshShell.CurrentDirectory = "{yaml_working_dir}"',
            'WshShell.Run "cmd.exe /c mkdocs serve", 0, false',
        ]

        try:
            with open(vbs_script_path, "w", encoding="utf-8") as f:
                f.write("\n".join(vbs_lines))

            # Trigger script quietly via background process stream
            subprocess.Popen(["wscript.exe", vbs_script_path], shell=True)
            log.info(
                "MkDocs hosting active. Preview available locally at: http://127.0.0.1:8000"
            )
        except Exception as err:
            log.error(
                f"Failed to cleanly initialize background web service container: {str(err)}"
            )


if __name__ == "__main__":
    from bmaya.maya.batch.runner import run_batch_test

    target_files = []

    # Gather package source directories dynamically
    target_src = os.path.join(repo_root, "py", "scripts", "bmaya")
    for root, _, files in os.walk(target_src):
        for f in files:
            # Gather production files, ignoring documentation or framework managers
            if (
                f.endswith(".py")
                and f != "run_doc_generation.py"
                and "batch" not in root
            ):
                target_files.append(os.path.join(root, f))

    # Execute via your centralized bootstrap framework runner context
    run_batch_test(CodebaseDocGenerator, file_list=target_files)
