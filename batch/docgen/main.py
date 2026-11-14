import os
import sys
import ast
import inspect
import subprocess

repo_root = os.environ.get("MAYADEV_ROOT")
"""
# Establish path roots immediately so mayapy can discover the framework structures
repo_root = os.environ.get("MAYADEV_ROOT")
if not repo_root:
    raise RuntimeError("Environment variable 'MAYADEV_ROOT' is not defined.")

scripts_path = os.path.abspath(os.path.join(repo_root, "py", "scripts"))
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)
"""
from bmaya.maya.batch.maya_batch_framework import MayaStandaloneBatchPackage


class CodebaseDocGenerator(MayaStandaloneBatchPackage):
    """Dynamic and static hybrid codebase documentation generator.

    Runs within a single clean context pass to evaluate modules natively when possible,
    falling back to static AST syntax processing for legacy Python 2 files or uninstalled packages.
    """

    def __init__(self, file_list=None):
        super(CodebaseDocGenerator, self).__init__(file_list=[])

        self.source_root = os.path.join(repo_root, "py", "scripts", "bmaya")
        self.docs_root = os.path.join(repo_root, "py", "scripts", "docs")
        self.mkdocs_yaml = os.path.join(repo_root, "py", "scripts", "mkdocs.yml")
        self.discovered_api_pages = []

    def execute(self, item_path):
        """Executes once inside the clean standalone session to process the entire codebase."""
        from bmaya.core import log

        log.warning("The mkdocs site is deprecated: the maintained docs are the top-level docs/ folder. "
                    "This generator only refreshes the API reference.")
        log.info("Starting monolithic hybrid codebase documentation generation pass...")

        for root, _, files in os.walk(self.source_root):
            for f in files:
                if (
                    not f.endswith(".py")
                    or f == "__init__.py"
                    or "batch" in root
                    or f == "run_doc_generation.py"
                ):
                    continue

                full_file_path = os.path.join(root, f)
                self._process_python_module(full_file_path)

        self._update_navigation_map()
        self._start_background_docs_server()

        return True, "Codebase documentation generation complete!"

    def _process_python_module(self, file_path):
        """Introspects Python modules dynamically inside Maya, falling back to static AST parsing on failure."""
        from bmaya.core import log

        log.info(f"Processing {file_path}")

        relative_path = os.path.relpath(file_path, self.source_root)
        module_parts = os.path.splitext(relative_path)[0].split(os.sep)
        module_name_str = "bmaya." + ".".join(module_parts)

        md_output = []
        parsed_successfully = False

        # --- PHASE 1: Try Dynamic Introspection ---
        try:
            if module_name_str in sys.modules:
                import importlib

                mod_obj = importlib.reload(sys.modules[module_name_str])
            else:
                mod_obj = __import__(module_name_str, fromlist=[""])

            module_doc = inspect.getdoc(mod_obj) or "No module documentation provided."
            md_output = [
                f"# Reference Component: `{module_name_str}`",
                "",
                "## Module Level Context",
                module_doc,
                "",
                "---",
                "## Object Taxonomy Reference (Dynamic Introspection)",
                "",
            ]

            # 1. Append live global constants first
            md_output.extend(self._parse_live_globals(mod_obj))

            # 2. Append classes and functions
            for member_name, member_obj in inspect.getmembers(mod_obj):
                if (
                    inspect.isclass(member_obj)
                    and member_obj.__module__ == mod_obj.__name__
                ):
                    md_output.extend(self._parse_live_class(member_name, member_obj))
                elif (
                    inspect.isfunction(member_obj)
                    and member_obj.__module__ == mod_obj.__name__
                ):
                    md_output.extend(
                        self._parse_live_function(
                            member_name, member_obj, heading_str="###"
                        )
                    )

            parsed_successfully = True

        except Exception as err:
            log.warning(
                f"Dynamic import bypass triggered for {module_name_str}: {str(err)}. Falling back to static AST parser."
            )

        # --- PHASE 2: Fallback to Pure Static AST Parsing ---
        if not parsed_successfully:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source_code = f.read()

                root_node = ast.parse(source_code, filename=file_path)
                module_doc = (
                    ast.get_docstring(root_node) or "No module documentation provided."
                )

                md_output = [
                    f"# Reference Component: `{module_name_str}`",
                    "",
                    "## Module Level Context",
                    module_doc,
                    "",
                    "---",
                    "## Object Taxonomy Reference (Static Fallback)",
                    "",
                ]

                # 1. Append global variable blocks first
                md_output.extend(self._parse_ast_globals(root_node))

                # 2. Proceed with standard structural loops
                for node in root_node.body:
                    if isinstance(node, ast.ClassDef):
                        md_output.extend(self._parse_ast_class(node))
                    elif isinstance(node, ast.FunctionDef):
                        md_output.extend(
                            self._parse_ast_function(node, heading_str="###")
                        )

                parsed_successfully = True
            except Exception as ast_err:
                log.error(
                    f"Static parsing failure on file layout {file_path}: {str(ast_err)}"
                )

        # --- PHASE 3: Save file under mirrored path configuration ---
        if md_output and parsed_successfully:
            output_rel_md = os.path.splitext(relative_path)[0] + ".md"
            target_md_file = os.path.join(self.docs_root, output_rel_md)

            os.makedirs(os.path.dirname(target_md_file), exist_ok=True)

            with open(target_md_file, "w", encoding="utf-8") as f:
                f.write("\n".join(md_output))

            web_relative_nav = output_rel_md.replace(os.sep, "/")
            self.discovered_api_pages.append(web_relative_nav)

    # ==============================================================================
    # Live Inspection Parsers
    # ==============================================================================
    def _parse_live_globals(self, mod_obj):
        """Extracts values from loaded top-level module attributes with table sanitization."""
        global_vars = []
        for name, obj in inspect.getmembers(mod_obj):
            if (
                name.startswith("__")
                or inspect.ismodule(obj)
                or inspect.isclass(obj)
                or inspect.isroutine(obj)
            ):
                continue

            val_str = repr(obj).replace("|", "\\|").replace("\n", " ")
            if len(val_str) > 120:
                val_str = val_str[:117] + "..."

            global_vars.append(f"| `{name}` | `{val_str}` | Runtime Extracted Value |")

        if not global_vars:
            return []

        return (
            [
                "### ⚙️ Global Constants & Configurations",
                "",
                "| Constant Name | Live Runtime Value | Type / Category |",
                "| :--- | :--- | :--- |",
            ]
            + global_vars
            + ["", "---"]
        )

    def _parse_live_class(self, class_name, class_obj):
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
            if (
                method_name.startswith("_")
                and not method_name.startswith("__")
                and method_name != "_register_core"
            ):
                continue
            if (
                method_name.startswith("__")
                and method_name.endswith("__")
                and method_name != "__init__"
            ):
                continue
            lines.extend(
                self._parse_live_function(method_name, method_obj, heading_str="####")
            )
            lines.append("")
        lines.append("\n---")
        return lines

    def _parse_live_function(self, func_name, func_obj, heading_str):
        try:
            func_sig = inspect.signature(func_obj)
        except (ValueError, TypeError):
            func_sig = "(...)"
        func_doc = (
            inspect.getdoc(func_obj)
            or "No functional arguments or usage blocks specified."
        )
        return [
            f"{heading_str} 🛠️ `{func_name}{func_sig}`",
            "",
            "```text",
            func_doc,
            "```",
            "",
        ]

    # ==============================================================================
    # Static AST Fallback Parsers
    # ==============================================================================
    def _parse_ast_class(self, node):
        class_doc = ast.get_docstring(node) or "No class descriptions detailed."
        lines = [
            f"### 🏷️ `CLASS` :: **{node.name}**",
            "",
            "**Description Summary:**",
            class_doc,
            "",
            "#### Methods & Interceptors",
            "",
        ]
        for sub_node in node.body:
            if isinstance(sub_node, ast.FunctionDef):
                if (
                    sub_node.name.startswith("_")
                    and not sub_node.name.startswith("__")
                    and sub_node.name != "_register_core"
                ):
                    continue
                if (
                    sub_node.name.startswith("__")
                    and sub_node.name.endswith("__")
                    and sub_node.name != "__init__"
                ):
                    continue
                lines.extend(self._parse_ast_function(sub_node, heading_str="####"))
                lines.append("")
        lines.append("\n---")
        return lines

    def _parse_ast_function(self, node, heading_str):
        arg_names = [a.arg for a in node.args.args]
        if node.args.vararg:
            arg_names.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            arg_names.append(f"**{node.args.kwarg.arg}")
        sig_str = f"({', '.join(arg_names)})"
        func_doc = (
            ast.get_docstring(node)
            or "No functional arguments or usage blocks specified."
        )
        return [
            f"{heading_str} 🛠️ `{node.name}{sig_str}`",
            "",
            "```text",
            func_doc,
            "```",
            "",
        ]

    def _parse_ast_globals(self, root_node):
        """Scans the module root for top-level variable definitions with table sanitization."""
        global_vars = []

        for node in root_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        val_snippet = "Calculated at Runtime"
                        if isinstance(node.value, ast.Constant):
                            val_snippet = repr(node.value.value)
                        elif isinstance(node.value, ast.List):
                            val_snippet = "List Definition"
                        elif isinstance(node.value, ast.Dict):
                            val_snippet = "Dictionary Mapping"
                        elif isinstance(node.value, ast.JoinedStr):
                            val_snippet = "Formatted String Literal"

                        val_snippet = val_snippet.replace("|", "\\|").replace("\n", " ")
                        global_vars.append(
                            f"| `{target.id}` | {val_snippet} | Static Configuration Variable |"
                        )

        if not global_vars:
            return []

        return (
            [
                "### ⚙️ Global Constants & Mappings",
                "",
                "| Constant Name | Default Value / Type | Definition Type |",
                "| :--- | :--- | :--- |",
            ]
            + global_vars
            + ["", "---"]
        )

    # ==============================================================================
    # Navigation and Infrastructure Assembly
    # ==============================================================================
    def _update_navigation_map(self):
        """Gathers layout pages and compiles a completely deduplicated structural tree."""
        from bmaya.core import log

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

            # Construct a pristine recursive navigation tree dictionary mapping
            api_tree = {}
            for page in self.discovered_api_pages:
                parts = page.split("/")
                current_level = api_tree
                for part in parts[:-1]:
                    current_level = current_level.setdefault(part, {})
                current_level[parts[-1]] = page

            # Format the dictionary map recursively into clean nested YAML blocks
            def format_nav_level(tree, indent_count=6):
                lines = []
                spacing = " " * indent_count
                for key, value in sorted(tree.items()):
                    label = os.path.splitext(key)[0].replace("_", " ").title()
                    if isinstance(value, dict):
                        lines.append(f"{spacing}- {label}:")
                        lines.extend(format_nav_level(value, indent_count + 4))
                    else:
                        lines.append(f"{spacing}- {label}: {value}")
                return lines

            nav_lines.extend(format_nav_level(api_tree))

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

    def _start_background_docs_server(self):
        """Assembles and fires a windowless VBScript layer to host the documentation server."""
        from bmaya.core import log

        yaml_working_dir = os.path.abspath(os.path.join(self.docs_root, ".."))
        temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
        vbs_script_path = os.path.join(temp_dir, "launch_mkdocs_hidden.vbs")

        vbs_lines = [
            'Set WshShell = CreateObject("WScript.Shell")',
            f'WshShell.CurrentDirectory = "{yaml_working_dir}"',
            'WshShell.Run "cmd.exe /c python -m mkdocs serve", 0, false',
        ]

        try:
            with open(vbs_script_path, "w", encoding="utf-8") as f:
                f.write("\n".join(vbs_lines))

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

    run_batch_test(CodebaseDocGenerator, file_list=[])
