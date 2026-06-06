# Module: shapeio

### Pipeline Intent
Provides utility functions for manipulating and processing control vertex (CV) data in Maya.

### Technical Implementation
Uses the Maya OpenMaya API to interact with scene objects, and Python's built-in `json` module for file input/output operations.

### Overview
The `shapeio` module provides a set of functions for managing CV data, including saving, loading, mirroring, and removing shape data. These utilities are designed to simplify the process of working with control vertex data in Maya.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** Maya.OpenMaya, Maya.cmds

## API Taxonomy Reference

### 🏷️ `CLASS` :: None (no classes defined)

#### Functions

### 🏷️ `FUNCTION` :: `save`
**Signature:**
```python
def save(cvsPath):
```
#### Arguments
- `cvsPath`: The path to the CVS file.

#### Returns
- shapeData: The processed CV data as a dictionary.

#### Description:
Saves the control vertex (CV) data from the current Maya scene into a CSV file.

### 🏷️ `FUNCTION` :: `load`
**Signature:**
```python
def load(cvsPath):
```
#### Arguments
- `cvsPath`: The path to the CVS file.

#### Returns
- shapeData: The loaded CV data as a dictionary.

#### Description:
Loads the control vertex (CV) data from a CSV file into the current Maya scene.

### 🏷️ `FUNCTION` :: `mirror`
**Signature:**
```python
def mirror(cvsPath):
```
#### Arguments
- `cvsPath`: The path to the CVS file.

#### Returns
- None

#### Description:
Mirrors the control vertex (CV) data from a CSV file, flipping the x-axis values and updating the corresponding Maya scene objects.

### 🏷️ `FUNCTION` :: `removeShapeData`
**Signature:**
```python
def removeShapeData(cvsPath, controls=[]):
```
#### Arguments
- `cvsPath`: The path to the CVS file.
- `controls`: A list of control names to remove from the CSV file (default is an empty list).

#### Returns
- None

#### Description:
Removes the specified control vertex (CV) data from a CSV file, updating the corresponding Maya scene objects.

---

### Documentation Drift
None found.