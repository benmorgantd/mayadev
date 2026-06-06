# Module: cvshapeinverter

### Pipeline Intent
Provides a mechanism for inverting a shape through the deformation chain, allowing animators to correct pose-related issues and apply the corrected mesh as a blendShape target.

### Technical Implementation
The `cvshapeinverter` module utilizes Maya's OpenMaya API and various Python modules (e.g., math) to perform point-wise calculations and manipulation of mesh data. It exposes an `invert` function that takes three input parameters: `base`, `corrective`, and `name`. The function generates an inverted shape by calculating the difference between the deformed base mesh and the sculpted corrective mesh.

### Overview
The `cvshapeinverter` module is designed to automate the process of inverting a shape through the deformation chain, making it easier for animators to correct pose-related issues and apply the corrected mesh as a blendShape target. This module provides a Pythonic interface for performing this inversion operation.

### Cross-Module Dependencies
* **Internal Framework Links:** `maya.cmds`, `maya.OpenMaya`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

### 🏷️ `FUNCTION` :: `invert`
**Signature:**
```python
def invert(base=None, corrective=None, name=None):
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
def get_shape(node, intermediate=False):
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
def get_mobject(node):
```
#### Arguments
- node (str): Name of the node.

#### Returns
- MObject: The dag path of a node.

---

### 🏷️ `FUNCTION` :: `get_dag_path`
**Signature:**
```python
def get_dag_path(node):
```
#### Arguments
- node (str): Name of the node.

#### Returns
- MDagPath: The dag path of a node.

---

### 🏷️ `FUNCTION` :: `get_points`
**Signature:**
```python
def get_points(path, space=OpenMaya.MSpace.kObject):
```
#### Arguments
- path (str or MObject): Name or dag path of a node.
- space (OpenMaya.MSpace): Space to get the points.

#### Returns
- MPointArray: The control point positions of a geometry node.

---

### 🏷️ `FUNCTION` :: `set_points`
**Signature:**
```python
def set_points(path, points, space=OpenMaya.MSpace.kObject):
```
#### Arguments
- path (str or MObject): Name or dag path of a node.
- points (MPointArray): The control point positions to set.
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

### 🏷️ `GLOBAL VARIABLE` :: N/A