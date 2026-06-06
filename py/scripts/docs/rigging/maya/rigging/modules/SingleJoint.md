# Module: SingleJoint


### Pipeline Intent
Provides a module for creating single joint controls with optional offset control. This module is used in the character rigging pipeline to create and manage joints.


### Technical Implementation
Exposes the build method which creates a single joint control on the given joint. It also includes an option to add an offset control.


### Overview
The SingleJoint module provides a way to create a single joint control with optional offset control, used in character rigging for creating and managing joints.


### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.base`, `bmaya.maya.rigging.shapes`, `bmaya.util`
* **External Dependencies:** None


## API Taxonomy Reference

### 🏷️ `CLASS` :: SingleJoint
**Purpose:** A module for creating single joint controls with optional offset control.


#### Methods
- `__init__(self, startJoint=None, name='singleJoint1', character=None,
                 parent=None, shapeType='cube',
                 mirror=False, side='L', alignWorld=None,
                 addOffsetControl=False, offsetShapeType='cube')`: Initializes the SingleJoint module.
- `build(self)`: Builds a single joint control on the given joint.

---

### 🏷️ `FUNCTION` :: `nameUtils.findControlName`
**Signature:**
```python
def findControlName(jnt_driver):
```

#### Returns
- return_type: Description of what this function returns.

---

### 🏷️ `GLOBAL VARIABLE` :: None

Note: No global variables were found in the provided code.