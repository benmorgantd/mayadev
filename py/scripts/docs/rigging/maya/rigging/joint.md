# Module: joint

### Pipeline Intent
Provides utility functions for working with joints in Maya. This module offers functionality for calculating the best-fit plane of a selection, adding twist joints as children of a given joint, orienting joints to world or mesh space, and mirroring face joints.

### Technical Implementation
This module relies on the `maya.cmds` and `OpenMaya` libraries to interact with the Maya application. It utilizes various functions from these libraries to perform calculations and transformations.

### Overview
The `joint` module is designed to provide a set of utility functions for working with joints in Maya. These functions can be used to manipulate joint hierarchies, calculate spatial relationships between joints, and orient joints to different reference frames.

### Cross-Module Dependencies

* **Internal Framework Links:** [List any modules from the codebase manifest that this file imports or interacts with]
	+ `bmaya.core.util.fileUtils`
	+ `bmaya.maya.util.nameUtils`
* **External Dependencies:** [e.g., Maya.cmds, OpenMaya]

## API Taxonomy Reference

### 🏷️ `CLASS` :: `None`
**Purpose:** 
#### Methods
- `getSelectionCenter(self)`: Calculates the centroid of a selection.
- `bestFitPlane(self)`: Calculates the best-fit plane of a selection and orients a locator to that plane.
- `addTwistJoints(startJoint, endJoint, jointCount=3)`: Adds twist joints as children of a given joint.
- `orientToWorld(joints)`: Orients joints to world space.
- `orientToMesh(joints, mesh)`: Orients joints to a specified mesh.
- `mirrorFaceJoints(joints)`: Mirrors face joints.

---

### 🏷️ `FUNCTION` :: `getSelectionCenter`
**Signature:**
```python
def getSelectionCenter():
```
#### Arguments

* None

#### Returns
- The centroid of the selection.

---

### 🏷️ `FUNCTION` :: `bestFitPlane`
**Signature:**
```python
def bestFitPlane():
```
#### Arguments

* None

#### Returns
- A locator oriented to the best-fit plane of the selection.

---

### 🏷️ `FUNCTION` :: `addTwistJoints`
**Signature:**
```python
def addTwistJoints(startJoint, endJoint, jointCount=3):
```
#### Arguments

* `startJoint`: The starting joint.
* `endJoint`: The ending joint.
* `jointCount=3`: The number of twist joints to add.

#### Returns
- An array of Joint classes representing the added twist joints.

---

### 🏷️ `FUNCTION` :: `orientToWorld`
**Signature:**
```python
def orientToWorld(joints):
```
#### Arguments

* `joints`: A list of joint names or MObject handles.

#### Returns

* None

---

### 🏷️ `FUNCTION` :: `orientToMesh`
**Signature:**
```python
def orientToMesh(joints, mesh):
```
#### Arguments

* `joints`: A list of joint names or MObject handles.
* `mesh`: The name or MObject handle of the mesh to orient to.

#### Returns

* None

---

### 🏷️ `FUNCTION` :: `mirrorFaceJoints`
**Signature:**
```python
def mirrorFaceJoints(joints):
```
#### Arguments

* `joints`: A list of joint names or MObject handles.

#### Returns

* None