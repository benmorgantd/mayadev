import os
import sys

def run_batch_test(test_class, file_list=None, config_path=None):
    """Bootstraps the environment and executes a class-based batch test suite.
    
    Args:
        test_class (BaseBatchPackage): The uninstantiated test class to run.
        file_list (list, optional): List of file paths to process.
        config_path (str, optional): Path to a json config file for picking up runs.
    """
    repo_root = os.environ.get("MAYADEV_ROOT")
    if not repo_root:
        raise RuntimeError("Environment variable 'MAYADEV_ROOT' is not defined.")

    scripts_path = os.path.abspath(os.path.join(repo_root, "py", "scripts"))
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)

    # Dynamic imports now that paths are safely initialized
    from .maya_batch_framework import MayaBatchEnvironment

    # Instantiate the test class
    if config_path and os.path.exists(config_path):
        batch_package = test_class.from_json(config_path)
    else:
        batch_package = test_class(file_list=file_list)

    env_manager = MayaBatchEnvironment()
    with env_manager:
        batch_package.run_suite(environment=env_manager)