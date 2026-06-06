# Module: nameUtils

### Pipeline Intent
Provides utility functions for working with names in Maya, used by various components to perform common naming tasks.

### Technical Implementation
Utilizes the `maya.cmds` and `maya.OpenMaya` modules to interact with the Maya environment. Leverages the `bmaya.core.constants` module for accessing consistent naming conventions.

### Overview
This module contains three main functions: `nameSelection`, `findControlName`, and `findJointName`. These functions help automate tasks related to renaming objects in Maya, such as naming joints and controls based on a consistent naming convention.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.core.constants`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `nameSelection`
**Signature:**
```python
def nameSelection(selection, name='joint', side='L', suffix='JNT'):
```
#### Arguments
- selection (list): The list of objects to rename.
- name (str): The base name for the new names. Defaults to 'joint'.
- side (str): The side identifier ('L' or 'R') for the new names. Defaults to 'L'.
- suffix (str): The suffix for the new names. Defaults to 'JNT'.

#### Returns
None

---

### 🏷️ `FUNCTION` :: `findControlName`
**Signature:**
```python
def findControlName(node, identifier=None):
```
#### Arguments
- node (str): The node name.
- identifier (str): An optional identifier to append to the node name.

#### Returns
The control name as a string.

---

### 🏷️ `FUNCTION` :: `findJointName`
**Signature:**
```python
def findJointName(node, identifier=None, count=0, suffix='DRIVER'):
```
#### Arguments
- node (str): The node name.
- identifier (str): An optional identifier to append to the node name.
- count (int): The joint number. Defaults to 0.
- suffix (str): The suffix for the new joint name. Defaults to 'DRIVER'.

#### Returns
The joint name as a string.

**Documentation Drift**
None found.