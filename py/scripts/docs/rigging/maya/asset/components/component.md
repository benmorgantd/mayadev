Here is the Markdown documentation for the `component` module:
# Module: component

### Pipeline Intent
Base class for production Components that handles logic for asset Id, file management, and versioning. Components are the individual files that make up an asset.

### Technical Implementation
The `Component` class provides a base implementation for handling the type extensions, file paths, and method calls for various components (e.g., mesh, skeleton, CVS, animRig, weights, build, components, postops, facePoses). It uses dictionaries to store type extensions and relative/absolute file paths.

### Overview
The `Component` class is a base class that provides a common interface for all production Components. It includes properties for the component's type, extension, relative path, and full path. It also defines methods for saving, loading, and referencing components, which must be implemented by each specific component type.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.Asset`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Component`
**Purpose:** Base class for production Components that handles logic for asset Id, file management, and versioning.

#### Methods
- `__init__(self, asset, component_type)`: Initializes the Component with an asset and a component type.
- `type(self) -> str`: Returns the component's type.
- `extension(self) -> str`: Returns the component's extension (based on its type).
- `relative_path(self) -> str`: Returns the component's relative path.
- `full_path(self) -> str`: Returns the component's full path.
- `save(self) -> None`: Raises a NotImplementedError, as this method must be implemented by each specific component type.
- `load(self) -> None`: Raises a NotImplementedError, as this method must be implemented by each specific component type.
- `reference(self) -> None`: Raises a NotImplementedError, as this method must be implemented by each specific component type.

### 🏷️ `GLOBAL VARIABLE` :: `TYPE_EXTENSIONS`
- **Type:** dict
- **Value/Purpose:** Dictionary mapping component types to their corresponding extensions.