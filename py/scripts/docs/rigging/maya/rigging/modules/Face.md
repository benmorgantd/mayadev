# Module: Face

### Pipeline Intent
Provides facial rig setup for animators, automating the creation of FKHierarchy modules to build controls for different regions of the face.

### Technical Implementation
Uses Maya.cmds and OpenMaya (FkChain) to generate hierarchical joint structures and bind them to drive joints. Utilizes Python's list comprehensions and conditional statements for data manipulation and processing.

### Overview
This module serves as a foundation for facial rigging in Maya, handling the creation of different FKHierarchy modules for upper head, middle head, lower head, jaw, eyebrows, and eyelids. It also establishes relationships between these regions using parent constraints to maintain offset.

### Cross-Module Dependencies
* **Internal Framework Links:** 
  - `bmaya.maya.rigging.base` (module)
  - `bmaya.maya.rigging.base.decorators` (wrapBuild decorator)
  - `bmaya.maya.rigging.shapes` (shapelib module)
  - `bmaya.maya.util` (nameUtils utility)

## API Taxonomy Reference

### 🏷️ `CLASS` :: Face(module.Module)
**Purpose:** The "Face" module sets up facial rigging in Maya, handling the creation of FKHierarchy modules for different regions of the face.

*Inherits from:* `bmaya.maya.rigging.base.module.Module`

#### Methods
- `__init__(self, character=None, name='face', parent=None, ...):` Initializes the Face module with specified parameters.
- `build(self):` Builds the facial rig hierarchy by creating FKHierarchy modules for different regions of the face and establishing relationships between them using parent constraints.

---

### 🏷️ `FUNCTION` :: buildFaceFkHierarchy
**Signature:**
```python
def buildFaceFkHierarchy(self, startJoint, exclude=[]):
```
#### Arguments
- `startJoint`: The starting joint for the FKHierarchy.
- `exclude`: A list of joints to exclude from the FKHierarchy.

#### Returns
- `bindJoints`: A list of bind joints created in the FKHierarchy.
- `driveJoints`: A list of drive joints created in the FKHierarchy.
- `controls`: A list of control shapes created in the FKHierarchy.

---

### 🏷️ `FUNCTION` :: createDriveJoint
**Signature:**
```python
def createDriveJoint(self, jnt):
```
#### Arguments
- `jnt`: The joint for which to create a drive joint.

#### Returns
- A drive joint created from the input joint.

---

### 🏷️ `FUNCTION` :: buildFkControls
**Signature:**
```python
def buildFkControls(self, driveJoints):
```
#### Arguments
- `driveJoints`: A list of drive joints for which to create control shapes.

#### Returns
- A list of control shapes created from the input drive joints.