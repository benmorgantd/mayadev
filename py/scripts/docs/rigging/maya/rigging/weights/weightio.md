Here is the Markdown documentation for the `weightio` module:

# Module: weightio
### Pipeline Intent
Provides functionality for loading and saving skin weights to/from XML files.

### Technical Implementation
This module uses the `xml.etree.ElementTree` library to parse XML files, and Maya's API (OpenMaya) for interacting with the Maya scene. It also utilizes the `bmaya.core.util.fileUtils` module for versioning file names, and the `log` module from `bmaya.core` for logging messages.

### Overview
The `weightio` module provides two main functions: `get_joints_from_xml` and `save/load`. The first function reads an XML file and extracts a list of joints from it. The second function saves or loads skin weights to/from an XML file, using Maya's deformerWeights command.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.core.util`, `log`
* **External Dependencies:** `xml.etree.ElementTree`, Maya API (OpenMaya), Maya.cmds

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `get_joints_from_xml`
**Signature:**
```python
def get_joints_from_xml(weights_dir):
```
#### Description:
Reads an XML file and extracts a list of joints from it.

#### Returns:
A list of joint names.

---

### 🏷️ `FUNCTION` :: `save`
**Signature:**
```python
def save(weights_dir):
```
#### Description:
Saves each selected object to a file in the given directory with its nameUtils.

#### Returns:
None

---

### 🏷️ `FUNCTION` :: `load`
**Signature:**
```python
def load(weights_path):
```
#### Description:
Tries to load a single weights file onto a matching item in the scene.

#### Returns:
None

Note that this documentation is strictly based on the provided source code, without any additional information.