# Module: Arm

### Pipeline Intent
Provides a modular implementation of an arm component for character rigging. This module integrates with the `ThreeJointIkFkTwist` class to create a 3-joint IK/FK chain with a gimbal control.

### Technical Implementation
Utilizes the `_ThreeJointIkFkTwist` class from `bmaya3.rigging.base.threejointikfkTwist` for IK/FK chain management. Wraps the build process using `wrapBuild` decorator to ensure correct execution of the pipeline.

### Overview
The `Arm` module constructs a character arm with three joints and an additional gimbal control, allowing for better manipulation of shoulder movements. This module serves as a building block for creating more complex character rigs.

### Cross-Module Dependencies
* **Internal Framework Links:** `_ThreeJointIkFkTwist`, `shapelib`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Arm`

**Purpose:** A modular implementation of an arm component for character rigging.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, name='Arm1', character=None, parent=None, mirror=False, side='L', fkikDefault=0, alignWorld=True)`: Initializes the arm module with specified parameters.
- `build(self) @wrapBuild`: Builds the 3-joint IK/FK chain and adds a gimbal control.

---

### 🏷️ `FUNCTION` :: `addFkGimbalControl`

**Signature:**
```python
def addFkGimbalControl(self):
```
#### Arguments
- self: Reference to the `Arm` object

#### Returns
- None

#### Description
Adds a gimbal control on top of the existing shoulder FK, allowing for better manipulation of shoulder movements.

---

### 🏷️ `GLOBAL VARIABLE` :: `modType`

- **Type:** String
- **Value/Purpose:** Tracks the type of module (Arm) in the pipeline.