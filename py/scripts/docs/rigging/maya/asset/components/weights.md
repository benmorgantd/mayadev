# Module: weights

### Pipeline Intent
Provides the management and storage of skin weights for a rig. This module is designed to handle the loading and saving of .weights files within the rig's components directory.

### Technical Implementation
This implementation utilizes the `os` module for file system operations and the `weightio` module from `bmaya3.rigging.weights` for handling weight data logic.

### Overview
The Weights component is a folder that contains the skin weight files for a rig. These files are saved and loaded using the `weightio` module, which handles the actual logic for saving and loading weight data.

### Cross-Module Dependencies
* **Internal Framework Links:** 
	+ `bmaya3.rigging.weights.weightio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Weights`
**Purpose:** Manages the skin weights for a rig.
*Inherits from:* `Component`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Weights object with the given asset and component type.

---

### 🏷️ `FUNCTION` :: `relativePath`
**Signature:**
```python
@property
def relativePath(self):
```
#### Returns
- A string representing the path of the weights folder within the rig's components directory, based on the component type.

---

### 🏷️ `FUNCTION` :: `files`
**Signature:**
```python
@property
def files(self):
```
#### Returns
- A list of file names in the weights folder.

---

### 🏷️ `FUNCTION` :: `load`
**Signature:**
```python
def load(self):
```
#### Description
- Loads the skin weight files from the weights folder using the `weightio.load()` method.

---

### 🏷️ `FUNCTION` :: `save`
**Signature:**
```python
def save(self):
```
#### Description
- Saves the skin weight files to the weights folder using the `weightio.save()` method.