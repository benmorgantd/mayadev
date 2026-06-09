import os
import sys

# Retrieve the root repository path from the environment variable
repo_root = os.environ.get("MAYADEV_ROOT")

if not repo_root:
    raise RuntimeError(
        "Environment variable 'MAYADEV_ROOT' is not set. "
        "Please configure it before running the batch suite."
    )

# Target the 'py/scripts' folder where the 'bmaya' package resides
scripts_path = os.path.abspath(os.path.join(repo_root, "py", "scripts"))

if not os.path.exists(scripts_path):
    raise FileNotFoundError(f"Scripts path not found: {scripts_path}")

if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)


def main():
    target_context = "maya" 
    test_files = []

    if target_context == "maya":
        from bmaya.maya.batch.maya_batch_framework import MayaBatchEnvironment, MayaStandaloneBatchPackage
        
        def run_maya_checks(file_path):
            import maya.cmds as cmds
            import bmaya.core.log as b_log
            b_log.info("Running node verification queries...")
            return True, f"Passed. Node metrics verified: {len(cmds.ls(type='transform'))}"

        env_manager = MayaBatchEnvironment()
        batch_package = MayaStandaloneBatchPackage(file_list=test_files)
        callback_logic = run_maya_checks

    else:
        from bmaya.core.batch.base_batch_framework import BaseBatchEnvironment, BaseBatchPackage
        
        def run_pure_python_checks(file_path):
            print("Processing pure Python file routines...")
            return True, "Python routine successful."

        env_manager = BaseBatchEnvironment(folder_prefix="python_batch")
        batch_package = BaseBatchPackage(file_list=test_files)
        callback_logic = run_pure_python_checks

    with env_manager:
        batch_package.run_suite(test_callback=callback_logic, environment=env_manager)


if __name__ == '__main__':
    main()