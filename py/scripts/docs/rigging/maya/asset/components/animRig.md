# Module: animRig

### Pipeline Intent
Provides base functionality for production Animation Rigs in Maya, handling asset ID, file management, and versioning.

### Technical Implementation
Imports the `MayaComponent` class from `bmaya.maya.asset.components.component` to leverage its initialization and type management capabilities.

### Overview
This module serves as a foundation for creating Animation Rig assets in Maya. It provides a basic structure for organizing and managing animation rig files, ensuring consistency across projects.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.component`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `AnimRig`
**Purpose:** Base class for production Animation Rigs that handles logic for asset Id, file management, and versioning.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the AnimRig object with the provided asset ID and component type.

---

### 🏷️ `FUNCTION` :: `relativePath`
**Signature:**
```python
@property
def relativePath(self):
```
#### Description
Returns the relative file path for the Animation Rig, which is a combination of the 'rig' directory and the rig's type and extension.

#### Returns
- `str`: The relative file path as a string.