# Module: _Foot

### Pipeline Intent
Provides a foot rigging module for animators to create character performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
This module provides a foot rigging system, allowing animators to create character performance files with localized directory scaffolding for easy organization. The module includes various methods for building and manipulating joints, ik handles, and controls.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.shapes` (shapelib), `bmaya.core.constants`, `bmaya.util.nameUtils`, `bmaya.util.mathUtils`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Foot`
**Purpose:** A foot rigging module for animators to create character performance files.

*Inherits from:* `object`

#### Methods
- `__init__(self, name='Foot1', ankle=None, ball=None, heel=None, bankOut=None, bankIn=None, toeTip=None)`: Initializes the foot rigging module.
- `build(self)`: Builds and manipulates joints, ik handles, and controls for the foot rig.
- `createFkHierarchy(self)`: Creates a forward kinematics (FK) hierarchy for the foot rig.
- `createIkHierarchy(self)`: Creates an inverse kinematics (IK) hierarchy for the foot rig.
- `createDriveHierarchy(self)`: Creates drive joints for the foot rig.
- `createReverseHierarchy(self)`: Creates a reverse hierarchy of oriented joints for the foot rig.
- `createIkHandles(self)`: Creates IK handles for the foot rig.
- `createIkControls(self)`: Creates IK controls for the foot rig.
- `createFkComponents(self)`: Creates FK components (joints and controllers) for the foot rig.

---

### 🏷️ `FUNCTION` :: `parentConstrain`
**Signature:**
```python
def parentConstrain(self, ctrl, jnt, maintainOffset=True):
```
#### Arguments
- `ctrl`: Control to constrain.
- `jnt`: Joint to be constrained to.
- `maintainOffset`: Whether to maintain the offset of the control.

#### Returns
- None

---

### 🏷️ `GLOBAL VARIABLE` :: `_Foot`

* **Type:** Class
* **Value/Purpose:** The _Foot class is used to create and manipulate foot rigging components, including joints, IK handles, and controls.