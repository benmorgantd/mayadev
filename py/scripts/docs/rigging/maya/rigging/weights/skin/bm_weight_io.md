# Module: bm_weight_io

### Pipeline Intent
Provides automated weight management tools for character riggers, enabling seamless export and import of skin weights between Maya scenes.

### Technical Implementation
This module utilizes the standard library `os` to manage file system operations and `xml.etree.ElementTree` to parse XML files. It also leverages the Maya API (`maya.cmds`, `maya.OpenMaya`) for interacting with the Maya environment.

### Overview
The `bm_weight_io` module offers a pair of functions: `parse_xml` and `export_weights`. The `parse_xml` function parses an XML file, extracting joints information from it. The `export_weights` function exports skin weights for selected objects to a specified path. Additionally, the module includes an `import_weights` function that imports skin weights from an XML file and applies them to the corresponding object in the Maya scene.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:**
	+ `maya.cmds`
	+ `maya.OpenMaya`
	+ `xml.etree.ElementTree`

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

#### No classes are defined in this module.

---

### 🏷️ `FUNCTION` :: parse_xml
**Signature:**
```python
def parse_xml(filepath):
```
#### Arguments
- filepath (str): Path to the XML file to be parsed.

#### Returns
- joints (list of str): A list of joints extracted from the XML file.

---

### 🏷️ `FUNCTION` :: export_weights
**Signature:**
```python
def export_weights(path=r"D:/Documents/Google Drive/01 BFA/Thesis Project Local Files/Rig/skin_library/Alpha/"):
```
#### Arguments
- path (str, optional): Path where the skin weights will be exported. Default is `r"D:/.../Alpha/"`.

#### Description
Exports skin weights for selected objects to a specified path.

---

### 🏷️ `FUNCTION` :: import_weights
**Signature:**
```python
def import_weights(path=r"D:/Documents/Google Drive/01 BFA/Thesis Project Local Files/Rig/skin_library/Alpha/"):
```
#### Arguments
- path (str, optional): Path where the skin weights will be imported from. Default is `r"D:/.../Alpha/"`.

#### Description
Imports skin weights from an XML file and applies them to the corresponding object in the Maya scene.

---

### 🏷️ `GLOBAL VARIABLE` :: None

*No global variables are defined in this module.*