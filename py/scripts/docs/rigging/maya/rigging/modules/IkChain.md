# Module: IkChain

### Pipeline Intent
Provides production file path verification and localized directory scaffolding for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The IkChain module is responsible for building a simple single-chain IK system. It creates drive joints, binds joints, and sets up ik spaces. This module is part of the character rigging pipeline and is used to create performance rigs for animators.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.core`, `bmaya3.rigging.base`, `bmaya3.rigging.shapes`
* **External Dependencies:** `maya.cmds`, `OpenMaya`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `IkChain`

**Purpose:** Provides a single-chain IK system for character rig performance files.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, name='IkChain1', ...)`: Initializes the IkChain module with start and end joints, name, and other parameters.
- `build(self)`: Builds a simple single-chain IK system.
- `setupIkSpaces(self, ikCtrl, defaultValue=1)`: Sets up IK spaces for an ik control.

---

### 🏷️ `FUNCTION` :: `findHierarchyJoints`

**Signature:**
```python
def findHierarchyJoints(self, shortestDistance=True, exclude=[]) -> list:
```
#### Arguments
- `shortestDistance`: A boolean indicating whether to use the shortest distance or not.
- `exclude`: A list of joints to exclude from the hierarchy.

#### Returns
- `list`: A list of hierarchy joints.

---

### 🏷️ `FUNCTION` :: `createDriveJoints`

**Signature:**
```python
def createDriveJoints(self) -> list:
```
#### Returns
- `list`: A list of drive joints.

---

### 🏷️ `GLOBAL VARIABLE` :: `IkChain`

* **Type:** Module
* **Value/Purpose:** Represents the IkChain module.