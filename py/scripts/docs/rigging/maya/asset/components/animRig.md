# Module: animRig

### Pipeline Intent
Base class for production Animation Rigs that handles logic for asset Id, file management, and versioning.

### Technical Implementation
This module is designed to handle the initialization of Animation Rigs in Maya, ensuring proper asset ID, file management, and version control. The `AnimRig` class inherits from `MayaComponent`, allowing it to leverage the base class's functionality.

### Overview
The `animRig` module provides a foundation for creating production-ready Animation Rigs in Maya, enabling efficient organization and management of assets.

### Cross-Module Dependencies
* **Internal Framework Links:** mayaComponent (from .mayaComponent)
* **External Dependencies:** os

## API Taxonomy Reference

### 🏷️ `CLASS` :: AnimRig
**Purpose:** Base class for production Animation Rigs that handles logic for asset Id, file management, and versioning.

#### Methods
- `__init__(self, asset, component_type)`: Initializes the Animation Rig with provided asset and component type.
- `relative_path(self)`: Returns the relative path of the animation rig file based on its type and extension.

---

Note: As there are no other classes or functions in this module, there is nothing else to document.