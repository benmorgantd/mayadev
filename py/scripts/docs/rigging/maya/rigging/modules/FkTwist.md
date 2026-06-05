# Module: FkTwist

### Pipeline Intent
Provides a module for creating and controlling FK (Forward Kinematics) twist controls in Maya. This module is designed to work with the FkChain class, allowing users to create complex character rigging systems.

### Technical Implementation
This module uses the `FkChain` class as its base and adds additional functionality for twist control. It utilizes various Maya commands and utilities to set up the twist hierarchy and controls.

### Overview
The FkTwist module is used to add twist capabilities to a character rig, allowing for more natural movement and flexibility.

### Cross-Module Dependencies
* **Internal Framework Links:** `FkChain`, `bmaya3.rigging.base.decorators`, `bmaya3.core.nameUtils`, `bmaya3.core.constants`, `bmaya3.util.mathUtils`
* **External Dependencies:** Maya.cmds, OpenMaya

## API Taxonomy Reference

### 🏷️ `CLASS` :: `FkTwist`

**Purpose:** A module for creating and controlling FK twist controls in Maya.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, exclude=[], name='FkTwist1', character=None, parent=None, shapeType='cube', mirror=False, side='L', alignWorld=False, twistAxis='X', exponent=1)`: Initializes the FkTwist module with various parameters.

---

### 🏷️ `FUNCTION` :: `build`

**Signature:**
```
def build(self):
```

#### Description:
This function sets up the FK twist controls and hierarchy using the `FkChain` class. It creates drive joints, bind joints, and control groups for the twist.

---

### 🏷️ `FUNCTION` :: `setupTwist`

**Signature:**
```
def setupTwist(self):
```

#### Description:
This function sets up the twist from the start of the chain by creating offset groups to drive the twist controls. It uses Maya commands and utilities to set up the hierarchy and controls.

---

### 🏷️ `GLOBAL VARIABLE` :: `twistAxis`

* **Type:** str
* **Value/Purpose:** The axis of twist (X, Y, or Z)