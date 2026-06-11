# Module: log

### Pipeline Intent
The `log` module provides a centralized logging mechanism for the bmaya framework. It allows for flexible configuration and output formatting, with options for both interactive UI and headless batch execution.

### Technical Implementation
This module imports necessary libraries such as `os`, `sys`, `logging`, and `maya.api.OpenMaya`. The `_LOGGER` global variable is initialized to None. A custom log handler class, `MayaLogHandler`, is defined to redirect logging records to native Maya GUI elements. The `init_logger()` function initializes and configures the master bmaya logger, setting its level to DEBUG. It also defines a formatter and adds handlers for interactive UI or headless batch execution. The `_LOGGER` variable is made globally accessible.

### Overview
The `log` module serves as a bridge between Python's built-in logging system and Maya's native GUI elements, enabling the framework to handle log messages in a way that is consistent with its overall architecture.

### Cross-Module Dependencies

* **Internal Framework Links:** None
* **External Dependencies:**
	+ `os`
	+ `sys`
	+ `logging`
	+ `maya.api.OpenMaya`
	+ `bmaya.maya.constants`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `MayaLogHandler`
**Purpose:** Redirects standard Python logging records to native Maya GUI elements.

*Inherits from:* `logging.Handler`

#### Methods
- `emit(self, record)`: Format and redirect the log message to Maya GUI elements.