# Module: NeckHead

### Pipeline Intent
Provides a module for creating neck head rigs in Maya, utilizing forward kinematics and twist controls.

### Technical Implementation
Utilizes the `FkTwist` class to create the rig's structure, allowing for precise control over joint placement and character deformation. Exposes automated build functionality through the `buildNeckHead` method.

### Overview
This module generates a neck head rigging solution that incorporates forward kinematics and twist controls. It provides a starting point for animators seeking to create realistic character poses and movements.

### Cross-Module Dependencies

* **Internal Framework Links:** FkTwist, maya.rigging.base.decorators
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: NeckHead
**Purpose:** A module for creating neck head rigs in Maya.
*Inherits from:* FkTwist.FkTwist

#### Methods

- `__init__(self, startJoint=None, endJoint=None, exclude=[], name='NeckHead1', character=None, parent=None, shapeType='cube', mirror=False, side='L', alignWorld=False, twistAxis='X', exponent=1)`:
  Initializes the NeckHead module with optional parameters for joint placement, mirroring, and more.
- `build(self):`
  Calls the internal `buildNeckHead` method to construct the rig's structure.

---

### 🏷️ `FUNCTION` :: buildNeckHead
**Signature:**
```python
def buildNeckHead(self):
```
#### Description:
Builds the neck head rig using forward kinematics and twist controls. Calculates start and end points, then applies constraints for twist control.

---

### No GLOBAL VARIABLES