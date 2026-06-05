# Module: cvs

### Pipeline Intent
Provides a json-based component for storing cv shape data for controls on a rig, handling loading and saving operations using the `shapeio` module.

### Technical Implementation
Combines inheritance from the `Component` class with Python properties to manage file paths. Utilizes `os.path.join` for constructing relative file paths based on asset type and extension.

### Overview
The Cvs class is designed to encapsulate cv shape data for controls in a rig, utilizing json files as storage containers. It inherits from the Component class and provides methods for loading and saving cv shape data using the shapeio module.

### Cross-Module Dependencies
* **Internal Framework Links:** `component` (from `bmaya3.maya.rigging.component`), `shapeio` (from `bmaya3.maya.rigging.shapes.shapeio`)
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: Cvs
**Purpose:** Encapsulates cv shape data for controls in a rig, utilizing json files as storage containers.
*Inherits from:* `Component`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Cvs instance with an asset and component type.
    *Arguments:*
        - `asset`: The asset this cv belongs to.
        - `componentType`: The type of this cv (e.g., "FK" or "IK").
    *Returns:* None

- `@property relativePath(self)`: Returns the relative file path for this cv, constructed using the asset's component type and extension.

    *Returns:*
        - A string representing the relative file path (e.g., "/rig/components/cvs.json")

- `load(self)`: Loads cv shape data from a json file at the specified full path.
    *Arguments:* None
    *Returns:* None

- `save(self)`: Saves cv shape data to a json file at the specified full path.
    *Arguments:* None
    *Returns:* None