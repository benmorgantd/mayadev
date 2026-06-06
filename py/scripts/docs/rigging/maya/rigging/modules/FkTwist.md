# Module: FkTwist

### Pipeline Intent
Provides a mechanism to create FK (Forward Kinematics) twist joints in character rigging pipelines. This module is designed to manage the construction of twist controls and drives for animators.

### Technical Implementation
FkTwist builds upon the existing FkChain module, inheriting its core functionality. It then extends this foundation by introducing a novel way to create twist joints that allow for smooth and controlled animations.

### Overview
The FkTwist module is responsible for creating and managing FK twist joints in a character rigging pipeline. It utilizes the FkChain module as its base, and provides additional functionality for constructing twist controls and drives.

### Cross-Module Dependencies
* **Internal Framework Links:** `FkChain`, `bmaya.maya.rigging.base.decorators`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: FkTwist

**Purpose:** A module for creating and managing FK twist joints in character rigging pipelines.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, exclude=[], name='FkTwist1', character=None, parent=None, shapeType='cube', mirror=False, side='L', alignWorld=False, twistAxis='X', exponent=1)`: Initializes the FkTwist module with the provided parameters.
- `build(self):` Builds the FK twist joints and controls for the given character rig.

#### Properties
- `twistAxis`: The axis of rotation for the twist joint (default: 'X').
- `exponent`: A value controlling the smoothness of the twist animation (default: 1).
- `modType`: The type of the module ('FkTwist').

---

### 🏷️ `FUNCTION` :: build
**Signature:**
```python
def build(self):
```
#### Description:
Builds the FK twist joints and controls for the given character rig.

---

### 🏷️ `FUNCTION` :: setupTwist
**Signature:**
```python
def setupTwist(self):
```
#### Description:
Sets up the twist from the start of the chain by creating offset groups to drive the twist controls.

---

### Documentation Drift

None.