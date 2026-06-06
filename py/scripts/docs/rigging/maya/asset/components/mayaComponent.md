# Module: mayaComponent

### Pipeline Intent
Provides file handling logic for Maya files within the component-based asset management framework.

### Technical Implementation
Utilizes Python's built-in `os` module for directory operations and Maya-specific commands through `maya.cmds`. Leverages the `fileUtils` utility from `bmaya.core.util` to manage versioning of component files.

### Overview
The `MayaComponent` class extends the base `Component` class, providing specialized methods for saving, loading, and referencing Maya file assets. This module serves as a foundation for handling Maya-specific components within the broader asset management system.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.core.util.fileUtils`, `component`
* **External Dependencies:** `maya.cmds`, `may.OpenMaya`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `MayaComponent`
**Purpose:** MayaComponent is a type of Component that handles file operations for Maya files.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the MayaComponent with an asset and component type.
- `save(self)`: Saves the Maya file to disk, incrementing its version number using `fileUtils`.
- `load(self)`: Loads the Maya file from disk.
- `reference(self)`: References the Maya file in Maya, setting its namespace to the file's name.

---

I hope this meets your requirements! Let me know if you need any further adjustments.