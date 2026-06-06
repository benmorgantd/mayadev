Here is the Markdown documentation for the file:

# Module: Leg

### Pipeline Intent
Provides automated directory scaffolding and versioning utilities for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes asynchronous directory generation using Python's `os` and `shutil` modules. Handles nested version track creation.

### Overview
This module serves as a building block for creating character leg rigs in Maya. It combines components from `_ThreeJointIkFkTwist` and `_Foot` to create a comprehensive rigging solution.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.base.decorators`, `bmaya.maya.shapes.shapelib`, `bmaya.maya.util.nameUtils`, `bmaya.maya.util.mathUtils`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: Leg
**Purpose:** A combination of `_ThreeJointIkFkTwist` and `_Foot` components for creating character leg rigs.

#### Methods
- `__init__(self, startJoint=None, ankle=None, ball=None, heel=None, bankOut=None, bankIn=None, toeTip=None, name='Leg1', character=None, parent=None, mirror=False, side='L')`
  - Initializes the Leg class with various parameters.
- `build(self)`
  - Builds the leg rig using components from `_ThreeJointIkFkTwist` and `_Foot`.
  - Configures parent-child relationships between various joints and groups.

#### Attributes
* `modType`: The type of this module, which is "Leg".
* `contract`: A list of joint names that are used to create the leg rig.
* `components`: A list of component objects used in the leg rig.
* `footComponents`, `ikDriveJoints`, `fkDriveJoints`, `node`, `parentConstrain`, `addFkGimbalControl`, and `addIkToeBend`: Various attributes and methods for controlling the leg rig.

---

### 🏷️ `FUNCTION` :: addFkGimbalControl(self)
**Signature:**
```python
def addFkGimbalControl(self):
```
#### Purpose:
Adds a second control on top of the existing leg fk that has zxy (2) rotation order.

#### Description:
Creates a new gimbal control and sets its rotation order to 2. It then parent-constrains the offset group of this control to the components group, and hooks it up to the visibility switch.

---

### 🏷️ `FUNCTION` :: addIkToeBend(self)
**Signature:**
```python
def addIkToeBend(self):
```
#### Purpose:
Creates a group in the ik reverse hierarchy that's the parent of the ball ik handle and has the pivot of the next joint in the hierarchy.

#### Description:
Creates a new group for the toe bend control, matches its transform to the reverse hierarchy, parents it to the ball ik handle, and hooks up its offset group to the components group.