Here is the documentation for the `joint` module:

# Module: joint
### Pipeline Intent
Utilities for working with joints in Maya.

### Technical Implementation
This module provides a set of functions for working with joints in Maya. These functions include getting the selection center, adding twist joints as children of a given joint, orienting joints to world space, and mirroring face joints.

### Overview
The `joint` module is used to manipulate and transform joints in Maya. It can be used to create complex joint structures and perform various transformations on those joints.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:**
	+ maya.cmds
	+ maya.api.OpenMaya
	+ bmaya.core.util.constants
	+ bmaya.maya.util.nameUtils

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

#### No classes defined in this module.

---

### 🏷️ `FUNCTION` :: `get_selection_center`
**Signature:**
```python
def get_selection_center():
```
#### Description:
Gets the center of the selection.

#### Returns:
om.MVector

### 🏷️ `FUNCTION` :: `add_twist_joints`
**Signature:**
```python
def add_twist_joints(start_joint, end_joint, joint_count=3):
```
#### Description:
Adds twist joints as children of the given joint. The child of the given joint will be used as the end joint to determine length.

#### Args:
* `start_joint` (str): The joint to use as the start point.
* `end_joint` (str): The joint to use as the end point.
* `joint_count` (int): The number of twist joints to add. Defaults to 3.

#### Returns:
(list) An array of Joint classes

### 🏷️ `FUNCTION` :: `orient_to_world`
**Signature:**
```python
def orient_to_world(joints):
```
#### Description:
Orients the given joints to world space.

#### Args:
* `joints` (list): A list of joint names or objects.

#### Returns:
None

### 🏷️ `FUNCTION` :: `orient_to_mesh`
**Signature:**
```python
def orient_to_mesh(joints, mesh):
```
#### Description:
Orients the given joints to match the given mesh.

#### Args:
* `joints` (list): A list of joint names or objects.
* `mesh` (str): The name of the mesh to orient to.

#### Returns:
None

### 🏷️ `FUNCTION` :: `mirror_face_joints`
**Signature:**
```python
def mirror_face_joints(joints):
```
#### Description:
Mirrors the given face joints. This function can be used to create a mirrored version of a joint structure.

#### Args:
* `joints` (list): A list of joint names or objects.

#### Returns:
None