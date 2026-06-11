# Module: maya_batch_framework
### Pipeline Intent
Automate Maya batch processing by providing a standalone environment and native logger integration for managing batch tasks.

### Technical Implementation
This module extends the base batch framework from `bmaya.core.batch.base_batch_framework` to provide a Maya-specific implementation. The core features include:

* A `MayaBatchEnvironment` class that manages the standalone Maya environment and integrates native logging.
* A `MayaStandaloneBatchPackage` class that implements automated asset canvas loading actions for Maya.

### Overview
This module provides the foundation for automating batch processing tasks within Maya, enabling users to create and manage standalone environments, logs, and scenes. The classes included in this module are designed to be extensible and can be used as a starting point for building more complex batch processing workflows.

### Cross-Module Dependencies
* **Internal Framework Links:**
	+ `bmaya.core.batch.base_batch_framework` (base class inheritance)
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `MayaBatchEnvironment`
**Purpose:** Manage the standalone Maya environment and native logger integration.

#### Methods
- `__init__(self, results_dir_name=None)`: Initializes the batch environment with optional results directory name.
- `__enter__(self)`: Enters the batch mode, setting up logging, file handles, and original stdout/stderr streams.
- `_initialize_logging(self)`: Initializes the native logger for the batch environment.
- `__exit__(self, exc_type, exc_val, exc_tb)`: Exits the batch mode, restoring original stdout/stderr streams and closing log file handle.

### 🏷️ `CLASS` :: `MayaStandaloneBatchPackage`
**Purpose:** Implement automated asset canvas loading actions for Maya.

#### Methods
- `_prepare_item(self, item_path, idx, total)`: Prepares an item by either initializing a blank testing scene or loading a scene file.