# Module: buildio

### Pipeline Intent
Provides production file path verification and localized directory scaffolding for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `json` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The `buildio` module gives logic for saving and loading build components, which are JSON files containing rig structures.

### Cross-Module Dependencies
* **Internal Framework Links:** None reported
* **External Dependencies:** Maya.cmds, OpenMaya, PyMel (not explicitly used in this file)

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A
No classes defined in this module.

#### No methods or attributes are exposed at the class level.

---

### 🏷️ `FUNCTION` :: load
**Signature:**
```python
def load(filepath):
```
#### Arguments
- filepath (str): The path to the JSON file to be loaded.

#### Returns
- buildData (dict): The contents of the JSON file, parsed as a dictionary. Raises a `RuntimeError` if the file does not exist.

---

### 🏷️ `FUNCTION` :: save
**Signature:**
```python
def save(filepath, data):
```
#### Arguments
- filepath (str): The path where the JSON file will be saved.
- data (dict): The dictionary to be serialized as a JSON file. Raises a `RuntimeError` if the parent directory does not exist.

#### Returns
- None

---

### 🏷️ `GLOBAL VARIABLE` :: N/A
No global variables defined in this module.

Documentation Drift: None reported