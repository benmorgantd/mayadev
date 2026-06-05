# Module: weightio

### Pipeline Intent
Provides utilities for managing character rig performance files. This module focuses on saving and loading skin cluster weights for animators.

### Technical Implementation
utilizes Maya's OpenMaya library, along with os and ElementTree modules to read XML-based joint configuration data. This data is then used to export or load skin cluster weights in the scene.

### Overview
This module offers two main functions: `getJointsFromXML` for reading joint information from an XML file, and `save` and `load` for handling weight exports and imports between scenes.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** maya.cmds, OpenMaya, os, ElementTree

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

#### Methods: N/A

---

### 🏷️ `FUNCTION` :: getJointsFromXML
**Signature:**
```python
def getJointsFromXML(weightsDir):
```
#### Arguments
- weightsDir (str): The directory path to the XML file.

#### Returns
- A list of joint names as strings, read from the XML file.

---

### 🏷️ `FUNCTION` :: save
**Signature:**
```python
def save(weightsDir):
```
#### Arguments
- weightsDir (str): The directory path where the skin cluster weights should be saved.

#### Returns
- None

#### Description:
Saves each selected object to a file in the given directory with its name. If the directory does not exist, it will be created.

---

### 🏷️ `FUNCTION` :: load
**Signature:**
```python
def load(weightsPath):
```
#### Arguments
- weightsPath (str): The path to the .weights file to be loaded.

#### Returns
- None

#### Description:
Tries to load a single weights file onto a matching item in the scene. It checks if the object exists and creates it if not, then applies the skin cluster weights from the loaded file.

---

### 🏷️ `GLOBAL VARIABLE` :: N/A