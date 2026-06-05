# Module: SingleJoint

### Pipeline Intent
Provides a single joint control module for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The SingleJoint module generates a single joint control on a given joint, allowing for precise animation of character rigs. It also provides optional offset controls for fine-tuning the joint's movement.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.base`, `bmaya3.rigging.shapes`, `bmaya3.core.nameUtils`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `SingleJoint`
**Purpose:** Module for generating a single joint control on a given joint.

#### Methods
- `__init__(self, startJoint=None, name='singleJoint1', character=None, parent=None, shapeType='cube', mirror=False, side='L', alignWorld=None, addOffsetControl=False, offsetShapeType='cube')`: Initializes the SingleJoint module.
- `build(self)`: Builds a single joint control on the given joint.

---

### 🏷️ `FUNCTION` :: `wrapBuild`
**Signature:**
```python
@wrapBuild
def build(self):
```
#### Arguments
* self (SingleJoint): The SingleJoint module instance.

#### Returns
* None

---

### 🏷️ `GLOBAL VARIABLE` :: None

Note: There are no global variables defined in this file.