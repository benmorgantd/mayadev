Here is the Markdown documentation for the file:

# Module: weightio

### Pipeline Intent
Provides a set of utilities to manage character rig performance files, specifically designed for animators working with Maya. This module handles directory scaffolding and versioning, allowing for better organization and collaboration.

### Technical Implementation
Utilizes Python's `os` and `shutil` modules to automate directory generation and version tracking. The implementation is asynchronous, ensuring efficient creation of nested version tracks.

### Overview
The `weightio` module contains a set of functions that facilitate the management of character rig performance files in Maya. This includes saving selected objects to file with their nameUtils, loading weights from XML files onto matching items in the scene, and handling skin clusters.

### Cross-Module Dependencies
* **Internal Framework Links:** `fileUtils`, `bmaya.core.constants`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A (No classes defined)

#### Methods
None

---

### 🏷️ `FUNCTION` :: getJointsFromXML

**Signature:**
```python
def getJointsFromXML(weightsDir) -> list:
```
#### Arguments
- weightsDir (str): Path to the XML file containing joint information.

#### Returns
- A list of joints extracted from the XML file.

---

### 🏷️ `FUNCTION` :: save

**Signature:**
```python
def save(weightsDir):
```
#### Description
Saves each selected object to a file in the given directory with its nameUtils. Also handles versioning and skin cluster exports.

#### Arguments
- weightsDir (str): Path to the directory where files should be saved.

---

### 🏷️ `FUNCTION` :: load

**Signature:**
```python
def load(weightsPath) -> None:
```
#### Description
Tries to load a single weights file onto a matching item in the scene. This function handles loading skin clusters and deleting old clusters if they exist.

#### Arguments
- weightsPath (str): Path to the XML file containing weight data.

---

### 🏷️ `GLOBAL VARIABLE` :: N/A (No global variables defined)

Let me know if you'd like me to clarify or modify anything!