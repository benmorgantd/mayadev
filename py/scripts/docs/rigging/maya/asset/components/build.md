# Module: build

### Pipeline Intent
Provides a structural foundation for the animRig performance file. A json-based Build component defines the rig structure.

### Technical Implementation
Utilizes inheritance from the `Component` class to establish the Build component's properties and behaviors. Utilizes the standard library `os` module for path manipulation.

### Overview
The Build component serves as a centralized container for defining the rig structure, enabling efficient management of performance files across various scenes and projects.

### Cross-Module Dependencies
* **Internal Framework Links:** [None mentioned in this file]
* **External Dependencies:** [Maya.cmds, OpenMaya]

## API Taxonomy Reference

### 🏷️ `CLASS` :: Build
**Purpose:** Defines the Build component for the animRig performance file.
*Inherits from:* `Component`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Build component with provided asset and component type.

---

### 🏷️ `PROPERTY` :: relativePath
**Signature:**
```python
@property
def relativePath(self):
```
#### Description:
Returns the relative path for the animRig performance file, constructed using the rig directory and the type extension.

---

### 🏷️ `GLOBAL VARIABLE` :: None

Note: No global variables are defined in this file.