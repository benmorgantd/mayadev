# Module: Spline

### Pipeline Intent
Provides a high-level framework for creating spines in Maya, incorporating FK and IK controls. This module enables animators to create flexible and realistic character rigs.

### Technical Implementation
Exposes the `Spline` class, which inherits from `Module`. This class provides automated directory generation and version tracking utilities using Python's standard library modules (`os`, `shutil`).

### Overview
The `Spline` module is designed to facilitate the creation of complex character rigging pipelines in Maya. It integrates FK (forward kinematics) and IK (inverse kinematics) controls, allowing for realistic and flexible character movements.

### Cross-Module Dependencies

* **Internal Framework Links:** `bmaya.maya.rigging.base.module`, `bmaya.maya.util.nameUtils`, `bmaya.maya.util.mathUtils`, `bmaya.maya.rigging.shapes.shapeio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Spline`
**Purpose:** Creates a high-level framework for creating spines in Maya, incorporating FK and IK controls.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, name='Spline1', character=None, side='M', mirror=False, parent=None, setupTwist=True, controlAmount=3, stretchy=True, startTwistParent=None, shapeType='cube')`: Initializes the Spline object with various parameters.

- `build(self)`: Builds the FK and IK controls for the spine.

- `buildFkControls(self)`: Creates the FK controls for the spine.

- `buildIkControls(self)`: Creates the IK controls for the spine.

- `buildIkSpline(self)`: Generates the IK spline curve and handles.

- `setupStretch(self)`: Sets up the stretch factor for the IK controls.

- `buildSplineDriverJoints(self)`: Creates the driver joints for the IK controls.

- `setupAdvancedTwist(self)`: Configures the advanced twist controls for the spine.

- `setupIkEndJoint(self)`: Creates a joint at the end of the ik chain that serves as an fk-style control.

- `setupIkHierarchy(self)`: Sets up the IK hierarchy to behave like an FK one.

---

### 🏷️ `FUNCTION` :: `wrapBuild`
**Signature:**
```python
def wrapBuild(func):
```
#### Arguments
- `func`: The function to be wrapped with error handling and logging.

#### Returns
- None

---

### 🏷️ `GLOBAL VARIABLE` :: `VARIABLE_NAME`
- **Type:** N/A
- **Value/Purpose:** N/A