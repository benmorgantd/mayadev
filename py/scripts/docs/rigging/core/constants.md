# Module: constants

### Pipeline Intent
Provides a centralized repository for the Maya pipeline's core constants, maintaining consistency and reusability across various modules.

### Technical Implementation
The `constants` module exposes a collection of pre-defined values, dictionaries, and templates essential to the maya asset creation process. These constants are designed to simplify code organization and improve maintainability by encapsulating frequently used values.

### Overview
This module serves as a single source of truth for common pipeline constants, facilitating easy access and reuse throughout the project.

### Cross-Module Dependencies
* **Internal Framework Links:** [bmaya.core.util.fileUtils], [bmaya.maya.asset.components.animRig], [bmaya.maya.rigging.buildio]

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

---

### 🏷️ `FUNCTION` :: N/A

---

### 🏷️ `GLOBAL VARIABLE` ::
- **Type:** Various (list, dict, str)
- **Value/Purpose:**
	+ `ASSET_TYPES`: A list of possible asset types for the pipeline.
	+ `COUNT_START`, `ROOT_JOINT`, and `LAYOUT_CONTROL_COUNT`: Integer values used for naming conventions in the Maya scene.
	+ `SIDE_NAMES`: A dictionary mapping side names to abbreviations (e.g., 'left' to 'L').
	+ `JOINT_SUFFIX` and `CTRL_SUFFIX`: String values used as suffixes for joint and control node names.
	+ `DOWN_AXIS`, `SPINE_UP_AXIS`, and `UP_AXIS`: Axis names used in the Maya scene.
	+ `TOP_LAYOUT_CONTROL` and `BOTTOM_LAYOUT_CONTROL`: Unique string identifiers for the top and bottom layout controls.
	+ `MESH_SUFFIX`: A string suffix used for mesh node naming.
	+ `REQUIRED_PLUGINS`: A list of required plugins for the pipeline.
	+ `UNIT_VECTORS`: A dictionary containing unit vectors (X, Y, Z) as lists.
	+ `POSTOPS_TEMPLATE`: A template string for post-operations scripting in Maya.
	+ `MODULE_SUFFIX`: A string suffix used to identify module-specific nodes.

---

Please note that this documentation is based on the provided code and might not be exhaustive or up-to-date.