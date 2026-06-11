# Module: mayaComponent

### Pipeline Intent
A MayaComponent is a type of Component that is specific to Maya. It contains the file handling logic for components that are Maya files.

### Technical Implementation
The `MayaComponent` class inherits from the `Component` class and provides methods for saving, loading, and referencing Maya-specific component files.

### Overview
This module is responsible for managing Maya-specific component files, including saving, loading, and referencing them. It extends the base `Component` class with file handling logic tailored to Maya's file formats.

### Cross-Module Dependencies
* **Internal Framework Links:** `component.py`, `fileUtils.py`
* **External Dependencies:** `maya.cmds`, `OpenMaya`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `MayaComponent`
**Purpose:** A MayaComponent is a type of Component that is specific to Maya. It contains the file handling logic for components that are Maya files.

*Inherits from:* `Component`

#### Methods
- `__init__(self, asset, component_type)`: Initializes the MayaComponent with an asset and component type.
- `save(self)`: Saves the MayaComponent file to disk.
- `load(self)`: Loads the MayaComponent file from disk.
- `reference(self)`: References the MayaComponent file in Maya.

---

Note: The `global_variables` section is empty since there are no global variables defined in this module.