# Module: cvs

### Pipeline Intent
Provides the Cvs class, a component that manages CV (Control Vertex) shape data for rig controls as a JSON file. This component handles loading and saving of CV shape data using the `shapeio` module.

### Technical Implementation
Exposes the Cvs class, inheriting from the `Component` class, which loads and saves CV shape data using the `shapeio` module.

### Overview
The Cvs class serves as a json file containing the cv shape data for the controls on a rig. It encapsulates the logic for loading and saving CVS files, utilizing the `shapeio` module to handle the actual operations.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.shapes.shapeio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Cvs`
**Purpose:** Manages CV shape data for rig controls as a JSON file.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Cvs class with the given asset and component type.
- `@property relativePath(self)`: Returns the relative path of the CVS file, based on the type and extension.
- `load(self)`: Loads CV shape data using the `shapeio` module.
- `save(self)`: Saves CV shape data using the `shapeio` module.

---

No documentation drift detected.