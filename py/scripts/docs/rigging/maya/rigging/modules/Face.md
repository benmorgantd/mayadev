# Module: Face

### Pipeline Intent
Provides facial rig setup for animators. Designed to create the necessary hierarchy and control structures for facial animation.

### Technical Implementation
Exposes a modular system for building facial rig hierarchies using FkChain classes. Utilizes `wrapBuild` decorator for automated versioning utilities. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The Face module is responsible for setting up the facial rig hierarchy and controls for animators. It uses the FkChain class to create the necessary joints and control structures, allowing for more precise facial animation.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.base`, `FkChain`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: Face(module.Module)
**Purpose:** Provides facial rig setup for animators.
*Inherits from:* `module.Module`

#### Methods
- `__init__(self, character=None, name='face', parent=None, upperHead=None, middleHead=None, lowerHead=None, jaw=None, eyeballs=[], eyelidBase=None, eyebrowBase=None, drivers=[]):` Initializer for the Face module.

---

### 🏷️ `FUNCTION` :: build(self)
**Signature:**
```python
@wrapBuild
def build(self):
```
#### Description:
Automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

#### Arguments
- None

#### Returns
- None

---

### 🏷️ `FUNCTION` :: buildFaceFkHierarchy(self, startJoint, exclude=[])
**Signature:**
```python
def buildFaceFkHierarchy(self, startJoint, exclude=[]):
```
#### Description:
Gathers the hierarchy joints for each region, creates their drive joints, and builds the fk controls.

#### Arguments
- `startJoint`: Start joint for the facial rig hierarchy.
- `exclude`: List of joints to exclude from the hierarchy.

#### Returns
- `bindJoints`: List of binding joints.
- `driveJoints`: List of drive joints.
- `controls`: List of fk control joints.

---

### Documentation Drift
* None found