# Module: cvshapeinverter

### Pipeline Intent
Provides a mechanism for inverting shapes through deformation chains to correct character rig performance issues. This module automates the process of creating an inverted shape from a deformed base mesh and a corrected corrective mesh.

### Technical Implementation
This module utilizes Maya's OpenMaya API to manipulate geometry, points, and matrices. It exposes various utility functions for retrieving and setting point arrays, matrix manipulation, and dag path handling.

### Overview
The `cvshapeinverter` module provides a tool for animators to correct character rig performance issues by inverting shapes through deformation chains. This process involves duplicating the base mesh, sculpting corrective fixes, selecting the original skinned model, and then running the `invert()` function.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** Maya.cmds, OpenMaya

## API Taxonomy Reference

### 🏷️ `CLASS` :: `None`

---

### 🏷️ `FUNCTION` :: `invert`
**Signature:**
```python
def invert(base=None, corrective=None, name=None) -> str:
```
#### Arguments
- base (str): Deformed base mesh.
- corrective (str): Sculpted corrective mesh.
- name (str): Name of the generated inverted shape.

#### Returns
- str: The name of the inverted shape.

---

### 🏷️ `FUNCTION` :: `get_shape`
**Signature:**
```python
def get_shape(node, intermediate=False) -> str:
```
#### Arguments
- node (str): Name of the node.
- intermediate (bool): True to get the intermediate mesh.

#### Returns
- str: The associated shape node.

---

### 🏷️ `FUNCTION` :: `get_mobject`
**Signature:**
```python
def get_mobject(node) -> OpenMaya.MObject:
```
#### Arguments
- node (str): Name of the node.

#### Returns
- OpenMaya.MObject: The dag path of a node.

---

### 🏷️ `FUNCTION` :: `get_points`
**Signature:**
```python
def get_points(path, space=OpenMaya.MSpace.kObject) -> OpenMaya.MPointArray:
```
#### Arguments
- path (str): Name or dag path of a node.
- space (OpenMaya.MSpace): Space to get the points.

#### Returns
- OpenMaya.MPointArray: The MPointArray of points.

---

### 🏷️ `FUNCTION` :: `set_points`
**Signature:**
```python
def set_points(path, points, space=OpenMaya.MSpace.kObject):
```
#### Arguments
- path (str): Name or dag path of a node.
- points (OpenMaya.MPointArray): MPointArray of points.
- space (OpenMaya.MSpace): Space to get the points.

---

### 🏷️ `FUNCTION` :: `set_matrix_row`
**Signature:**
```python
def set_matrix_row(matrix, new_vector, row):
```
#### Arguments
- matrix (MMatrix): Matrix to set.
- new_vector (MVector or MPoint): Vector to use.
- row (int): Row number.

---

### 🏷️ `FUNCTION` :: `set_matrix_cell`
**Signature:**
```python
def set_matrix_cell(matrix, value, row, column):
```
#### Arguments
- matrix (MMatrix): Matrix to set.
- value (float): Value to set cell.
- row (int): Row number.
- column (int): Column number.

---

### 🏷️ `GLOBAL VARIABLE` :: `None`

Note: Documentation Drift detected for the following elements:

* None