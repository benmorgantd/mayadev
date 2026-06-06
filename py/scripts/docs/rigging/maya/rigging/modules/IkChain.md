# Module: IkChain

### Pipeline Intent
Provides production file path verification and localized directory scaffolding for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The `IkChain` module is used to create an inverse kinematic (ik) chain in Maya for character rigging purposes. It provides a simple single-chain ik system that can be customized with various parameters such as start joint, end joint, and up vector.

### Cross-Module Dependencies
* **Internal Framework Links:**
	+ `bmaya.core.constants`
	+ `bmaya.maya.util.nameUtils`
	+ `bmaya.maya.util.mathUtils`
	+ `bmaya.maya.rigging.base.module`
	+ `bmaya.maya.rigging.base.decorators`
	+ `bmaya.maya.rigging.shapes.shapelib`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `IkChain`

**Purpose:** Create an inverse kinematic (ik) chain in Maya for character rigging purposes.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, name='IkChain1', character=None, parent=None, mirror=False, upVector=[0, 2, 0], exclude=[], side='L')`: Initializes the ik chain with parameters.
- `build(self)`: Builds the ik chain.
- `buildIkControls(self, driveJoints, worldAimTarget=None, downAxis='X', upAxis='Y', followWorld=True)`: Creates ik controls for the ik chain.

---

### 🏷️ `FUNCTION` :: `parentConstrain`

**Signature:**
```python
def parentConstrain(parent, child):
```
#### Arguments
- parent (str): The parent object.
- child (str): The child object.

#### Returns
- None

This function connects the child object to the parent object using a parent constraint in Maya.