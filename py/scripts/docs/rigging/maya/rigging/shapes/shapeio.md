# Module: shapeio

### Pipeline Intent
The `shapeio` module is responsible for exporting and importing NURBS curve CV data to/from a JSON file, allowing for efficient storage and manipulation of this data.

### Technical Implementation
This module utilizes the Maya API (OpenMaya) and Python's built-in `json` library to read and write the shape data. The `save` function iterates through all selected NURBS curves, extracts their CV points in world space, and stores them in a dictionary for each curve. The resulting data is then written to a JSON file using the `json.dumps()` method.

The `load` function reads the shape data from a JSON file, selects the corresponding NURBS curves in Maya, and sets their CV points to match the stored values. This process ensures that the loaded shape data matches the original exported data.

The `mirror` function mirrors the CV data of selected NURBS curves by flipping their X-coordinate values. It also updates the corresponding shape data dictionary and saves the changes to the JSON file using the `save` function.

The `remove_shape_data` function removes the CV data for specific controls from the shape data dictionary, then writes the modified data back to the JSON file.

### Overview
The `shapeio` module provides a set of functions for managing NURBS curve CV data in Maya. It can export and import this data to/from a JSON file, allowing for efficient storage and manipulation of shape data.

### Cross-Module Dependencies

* **Internal Framework Links:** None
* **External Dependencies:**
	+ `maya.api.OpenMaya` (for working with Maya's API)
	+ `maya.cmds` (for interacting with Maya's command-line interface)
	+ `json` (for JSON data serialization and deserialization)

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: save
**Signature:**
```python
def save(cvsPath):
```
#### Arguments
- `cvsPath`: The path to the CSV file.

#### Returns
- A dictionary containing the shape data for each NURBS curve.

---

### 🏷️ `FUNCTION` :: load
**Signature:**
```python
def load(cvsPath):
```
#### Arguments
- `cvsPath`: The path to the CSV file.

#### Returns
- None (modifies Maya's selection and sets NURBS curve CV points)

---

### 🏷️ `FUNCTION` :: mirror
**Signature:**
```python
def mirror(cvsPath):
```
#### Arguments
- `cvsPath`: The path to the CSV file.

#### Returns
- None (modifies shape data dictionary and saves changes to JSON file)

---

### 🏷️ `FUNCTION` :: remove_shape_data
**Signature:**
```python
def remove_shape_data(cvsPath, controls=[]):
```
#### Arguments
- `cvsPath`: The path to the CSV file.
- `controls`: A list of control names (default is an empty list).

#### Returns
- None (removes shape data for specified controls and saves changes to JSON file)