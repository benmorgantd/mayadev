# Module: component

### Pipeline Intent
Provides the foundation for production components, including asset ID management, file handling, and versioning. Acts as a base class for individual component files that make up an asset.

### Technical Implementation
Utilizes dictionaries to store type extensions for each component type. Handles unimplemented logic for loading, saving, and referencing, which must be defined by specific component types.

### Overview
The `Component` class serves as a base class for various production components in the pipeline. It manages the necessary file paths and extensions based on the component's type. This class is designed to provide a standard interface for all components to interact with the asset hierarchy.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.asset`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Component`
**Purpose:** Base class for production Components that handles logic for asset Id, file management, and versioning.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the component with an asset and a component type.
- `@property type(self)`: Returns the component's type.
- `@property extension(self)`: Returns the component's type-specific file extension.
- `@property relativePath(self)`: Returns the component's relative path within the rig directory.
- `@property fullPath(self)`: Returns the component's full path, including its parent asset's root directory and the component's relative path.

#### Properties
* `componentType`: The type of the component (e.g., 'mesh', 'skeleton', etc.).
* `type`: The type of the component.
* `extension`: The file extension specific to the component's type.
* `relativePath`: The component's relative path within the rig directory.
* `fullPath`: The component's full path, including its parent asset's root directory and the component's relative path.

#### Functions
- `save(self)`: Raises a `NotImplementedError` for unimplemented save logic.
- `load(self)`: Raises a `NotImplementedError` for unimplemented load logic.
- `reference(self)`: Raises a `NotImplementedError` for unimplemented reference logic.