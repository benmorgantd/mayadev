# Module: joint

### Pipeline Intent
Provides utility functions for working with joints in Maya, including calculating the best-fit plane for a selection of vertices and adding twist joints to a given start joint.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The `joint` module provides a set of utility functions for working with joints in Maya, including calculating the best-fit plane for a selection of vertices and adding twist joints to a given start joint.

### Cross-Module Dependencies

* **Internal Framework Links:** `bmaya.core.util`, `bmaya.maya.util`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `None`

#### Methods
None

---

### 🏷️ `FUNCTION` :: `getSelectionCenter`
**Signature:**
```python
def getSelectionCenter():
```
#### Description:
Calculates the centroid of a selection of vertices.

#### Returns:
A Maya vector representing the center of the selected vertices.

---

### 🏷️ `FUNCTION` :: `bestFitPlane`
**Signature:**
```python
def bestFitPlane():
```
#### Description:
Calculates the best-fit plane for a selection of vertices and aims a locator at it.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `addTwistJoints`
**Signature:**
```python
def addTwistJoints(startJoint, endJoint, jointCount=3):
```
#### Description:
Adds twist joints as children of the given start joint, determined by the length from the start joint to the end joint.

#### Args:
* `startJoint`: The starting joint for the twist.
* `endJoint`: The ending joint for the twist.
* `jointCount`: The number of twist joints to add (default=3).

#### Returns:
An array of Joint classes representing the added twist joints.

---

### 🏷️ `FUNCTION` :: `orientToWorld`
**Signature:**
```python
def orientToWorld(joints):
```
#### Description:
Orients a set of joints to world space, parenting any child joints to their respective parent joints and deleting any intermediate nodes.

#### Args:
* `joints`: The list of joints to orient.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `orientToMesh`
**Signature:**
```python
def orientToMesh(joints, mesh):
```
#### Description:
Orients a set of joints to match the normal of a given mesh.

#### Args:
* `joints`: The list of joints to orient.
* `mesh`: The mesh to orient the joints to.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `mirrorFaceJoints`
**Signature:**
```python
def mirrorFaceJoints(joints):
```
#### Description:
Mirrors a set of face joints, creating mirrored versions and parenting them to their respective parent joints.

#### Args:
* `joints`: The list of joints to mirror.

#### Returns:
None