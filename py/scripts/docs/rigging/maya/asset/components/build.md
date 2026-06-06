# Module: build

### Pipeline Intent
Provides the foundation for building character rig performance files. This module is responsible for managing the structure and organization of the rig.

### Technical Implementation
 Utilizes Python's built-in `os` module to handle file paths and directory generation. This class inherits from the base `Component` class, allowing it to leverage common functionality across various asset components.

### Overview
The Build component serves as a JSON file that contains the rig structure. It provides a mechanism for defining and organizing character rigs in a standardized manner.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.component`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Build`
**Purpose:** Manages the structure and organization of character rig performance files.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Build object with the given asset and component type.

---

### 🏷️ `FUNCTION` :: `relativePath`
**Signature:**
```python
@property
def relativePath(self):
```
#### Returns
- A string representing the path to the rig file in the format `/rig/components/animRig.ma`. The path is constructed using the `os.path.join` function, taking into account the asset's type and extension.