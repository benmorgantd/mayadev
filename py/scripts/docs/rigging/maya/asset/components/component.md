# Module: component

### Pipeline Intent
Provides a base class for production Components that handles logic for asset Id, file management, and versioning.

### Technical Implementation
Exposes type extensions for each component type using a dictionary. Handles the unimplemented logic for loading and saving and referencing, which must be defined by each specific component type.

### Overview
This module serves as a foundation for creating different types of components in the production pipeline. It handles file management and versioning for each component type, providing a starting point for developers to build upon.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.asset`, `bmaya.core.util.fileUtils`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Component`
**Purpose:** Base class for production Components that handles logic for asset Id, file management, and versioning.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Component instance with an asset and a component type.
- `get_type(self)`: Returns the component type.
- `get_extension(self)`: Returns the file extension associated with the component type.
- `get_relative_path(self)`: Returns the relative path for the component (e.g., `/rig/components`).
- `get_full_path(self)`: Returns the full path to the component's directory, including the asset root directory.
- `save(self)`: Raises a NotImplementedError as this method is not implemented.
- `load(self)`: Raises a NotImplementedError as this method is not implemented.
- `reference(self)`: Raises a NotImplementedError as this method is not implemented.

---

**Documentation Drift**

* None found.