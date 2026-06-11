Here is the documentation for the `runner` module:

# Module: runner
## Pipeline Intent
Bootstraps the environment and executes a class-based batch test suite.

## Technical Implementation
The `run_batch_test` function takes in three parameters: `test_class`, `file_list`, and `config_path`. It initializes the environment by setting up the `MAYADEV_ROOT` environment variable, then checks if it's defined. If not, it raises a `RuntimeError`.

It then imports the `MayaBatchEnvironment` class from the `maya_batch_framework` module, and instantiates the test class using either the `from_json` method (if a config file exists) or by passing in a list of files to process.

Finally, it sets up an environment manager with the instantiated test package and runs the suite within that environment.

## Overview
The `runner` module provides a way to execute a batch test suite using a class-based approach. It can be configured to run tests based on a JSON config file or by passing in a list of files to process.

## Cross-Module Dependencies
* **Internal Framework Links:** `maya_batch_framework`
* **External Dependencies:** None

### 🏷️ `FUNCTION` :: `run_batch_test`

**Signature:**
```python
def run_batch_test(test_class, file_list=None, config_path=None):
```
#### Arguments
- test_class (BaseBatchPackage): The uninstantiated test class to run.
- file_list (list, optional): List of file paths to process.
- config_path (str, optional): Path to a json config file for picking up runs.

#### Returns
None

### 🏷️ `GLOBAL VARIABLE` :: None