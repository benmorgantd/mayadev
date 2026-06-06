# Module: animRig

### Pipeline Intent
Provides a base class for production Animation Rigs that encapsulates logic for asset Id, file management, and versioning. This class is specific to Maya and serves as a foundation for building animation rigs.

### Technical Implementation
The `AnimRig` class inherits from the `MayaComponent` class and utilizes the standard library `os` module to generate relative paths for rig files.

### Overview
This module defines a base class for animating rigs in Maya, handling various aspects of file management and asset identification. It serves as a starting point for creating custom animation rigs.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.mayaComponent`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: AnimRig
**Purpose:** Base class for production Animation Rigs that handles logic for asset Id, file management, and versioning.
**Inherits from:** `bmaya.maya.asset.components.mayaComponent`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the anim rig with provided asset and component type.

---

### 🏷️ `FUNCTION` :: relativePath
**Signature:**
```python
@property
def relativePath(self):
```
#### Returns
- A string representing the relative path for the animation rig file (e.g., `/rig/animRig.ma`)

---

### Documentation Drift

* None found.