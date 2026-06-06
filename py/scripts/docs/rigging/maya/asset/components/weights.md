# Module: weights

### Pipeline Intent
Provides a framework for handling and persisting skin weights in Maya rigs. This component serves as a central hub for managing .weights files within the rig's components directory.

### Technical Implementation
Built upon the `Component` class from `bmaya.maya.asset.components.component`, this module leverages the `weightio` utility to read and write skin weight data.

### Overview
The Weights component is responsible for storing, loading, and managing skin weights for a given Maya rig. This module ensures that weight files are properly saved and loaded within the designated directory structure.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.weights.weightio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Weights`
**Purpose:** Manages skin weight files for a Maya rig component.
*Inherits from:* `Component`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Weights component with the given asset and component type.

---

### 🏷️ `PROPERTY` :: `relativePath`
**Signature:** 
```python
@property
def relativePath(self):
```
#### Description:
Returns the directory path where this component's weight files are stored.

---

### 🏷️ `PROPERTY` :: `files`
**Signature:** 
```python
@property
def files(self):
```
#### Description:
Retrieves a list of files in this component's weight file directory. If an error occurs while listing files, returns an empty list instead.

---

### 🏷️ `FUNCTION` :: `load`
**Signature:**
```python
def load(self):
```
#### Arguments:

* No arguments

#### Description:
Loads skin weight data from all .weights files in this component's directory using the `weightio.load()` utility.

---

### 🏷️ `FUNCTION` :: `save`
**Signature:**
```python
def save(self):
```
#### Arguments:

* No arguments

#### Description:
Saves the current skin weight data to disk using the `weightio.save()` utility, storing it in this component's designated directory.