# Module: shapeio

### Pipeline Intent
Provides utility functions to manipulate and manage character rig performance files. Designed to handle creation, export, import, and modification of shape data.

### Technical Implementation
Leverages the Maya API (OpenMaya) to interact with the scene graph and perform operations on nurbs curves. Utilizes Python's built-in `json` module for file I/O and scripting utilities provided by the `fileUtils` module from `bmaya3.core.util`.

### Overview
The shapeio module offers a set of functions to manage and manipulate shape data stored in CV files. These functions enable users to export, import, mirror, and remove shape data.

### Cross-Module Dependencies
* **Internal Framework Links:** `fileUtils`
* **External Dependencies:** Maya.cmds, OpenMaya

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

#### Methods
None

---

### 🏷️ `FUNCTION` :: save
**Signature:**
```python
def save(cvsPath):
```
#### Arguments
- cvspath (str): The path to the CV file.

#### Returns
- shapeData (dict): A dictionary containing the shape data.

---

### 🏷️ `FUNCTION` :: load
**Signature:**
```python
def load(cvsPath):
```
#### Arguments
- cvspath (str): The path to the CV file.

#### Returns
- shapeData (dict): A dictionary containing the shape data.

---

### 🏷️ `FUNCTION` :: mirror
**Signature:**
```python
def mirror(cvsPath):
```
#### Arguments
- cvspath (str): The path to the CV file.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: removeShapeData
**Signature:**
```python
def removeShapeData(cvsPath, controls=[]):
```
#### Arguments
- cvspath (str): The path to the CV file.
- controls (list): A list of control names.

#### Returns
- None