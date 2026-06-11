Here is the Markdown documentation for the `constants` module:

# Module: constants
### Pipeline Intent
Constants module providing a collection of pre-defined values and strings used throughout the pipeline.

### Technical Implementation
The `constants` module contains a set of predefined constants, including asset types, joint and control suffixes, axis names, and layout control names. These values are used to facilitate consistent naming conventions and simplify code maintenance.

### Overview
This module provides a centralized location for storing frequently used constants that can be accessed throughout the pipeline.

## API Taxonomy Reference

### 🏷️ `GLOBAL VARIABLE` :: `ASSET_TYPES`
**Type:** List[str]
**Value/Purpose:** Possible asset types, e.g., "prop", "environment", "character", and "head".

### 🏷️ `GLOBAL VARIABLE` :: `COUNT_START`
**Type:** int
**Value/Purpose:** The starting integer value for joints and controls.

### 🏷️ `GLOBAL VARIABLE` :: `SIDE_NAMES`
**Type:** Dict[str, str]
**Value/Purpose:** A dictionary mapping side names to abbreviations (e.g., "left" -> "L", "right" -> "R", etc.).

### 🏷️ `GLOBAL VARIABLE` :: `JOINT_SUFFIX`
**Type:** str
**Value/Purpose:** The suffix used for joint names.

### 🏷️ `GLOBAL VARIABLE` :: `DOWN_AXIS`
**Type:** str
**Value/Purpose:** The name of the down axis (e.g., "X").

### 🏷️ `GLOBAL VARIABLE` :: `SPINE_UP_AXIS`
**Type:** str
**Value/Purpose:** The name of the spine up axis (e.g., "Y").

### 🏷️ `GLOBAL VARIABLE` :: `UP_AXIS`
**Type:** str
**Value/Purpose:** The name of the up axis (e.g., "Y").

### 🏷️ `GLOBAL VARIABLE` :: `ROOT_JOINT`
**Type:** str
**Value/Purpose:** The full path to the root joint.

### 🏷️ `GLOBAL VARIABLE` :: `CTRL_SUFFIX`
**Type:** str
**Value/Purpose:** The suffix used for control names.

### 🏷️ `GLOBAL VARIABLE` :: `TOP_LAYOUT_CONTROL` and `BOTTOM_LAYOUT_CONTROL`
**Type:** str
**Value/Purpose:** Full path to the top and bottom layout controls, respectively.

### 🏷️ `GLOBAL VARIABLE` :: `MESH_SUFFIX`
**Type:** str
**Value/Purpose:** The suffix used for mesh names.

### 🏷️ `GLOBAL VARIABLE` :: `UNIT_VECTORS`
**Type:** Dict[str, List[int]]
**Value/Purpose:** A dictionary mapping axis names to their corresponding unit vectors.

### 🏷️ `GLOBAL VARIABLE` :: `LAYOUT_CONTROL_COUNT`
**Type:** int
**Value/Purpose:** The number of layout control names.

### 🏷️ `GLOBAL VARIABLE` :: `MODULE_SUFFIX`
**Type:** str
**Value/Purpose:** The suffix used for module names.