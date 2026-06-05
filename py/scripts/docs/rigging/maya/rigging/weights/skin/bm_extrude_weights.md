# Module: bm_extrude_weights

### Pipeline Intent
Automates the process of extruding skin weights for a polygon mesh in Maya, allowing for quick fixes of intersections on thick meshes. This module is designed to be used within the Maya UI.

### Technical Implementation
The `ExtrudeWeights` class extends the OpenMayaMPx.MPxCommand interface and provides methods for undoing and redoing the command. The `doIt`, `redoIt`, and `undoIt` methods work together to execute the command, which involves finding the skin cluster on a selected mesh, copying the weights for each vertex to its closest neighbor in the inverse normal direction, and then setting those new weights.

### Overview
This module is used to automate the process of extruding skin weights for a polygon mesh in Maya. It can be used to quickly fix intersections on thick meshes by copying the weights for each vertex to its closest neighbor in the inverse normal direction.

### Cross-Module Dependencies
* **Internal Framework Links:** `maya.OpenMaya`, `maya.OpenMayaAnim`, `maya.OpenMayaMPx`, `maya.cmds`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `ExtrudeWeights`
**Purpose:** Provides methods for extruding skin weights on a polygon mesh in Maya.

#### Methods
- `__init__(self)`: Initializes the command.
- `isUndoable(self)`: Indicates whether this command is undoable.
- `doIt(self, args)`: Executes the command.
- `redoIt(self)`: Re-executes the command for redos.
- `undoIt(self)`: Undoes the command.

---

### 🏷️ `FUNCTION` :: `cmdCreator`
**Signature:**
```python
def cmdCreator() -> omMPx.MPxCommand:
```
#### Purpose:** Creates an instance of the `ExtrudeWeights` class.

---

### 🏷️ `FUNCTION` :: `initializePlugin`
**Signature:**
```python
def initializePlugin(mObject) -> None:
```
#### Purpose:** Initializes the plugin by registering the command.

---

### 🏷️ `FUNCTION` :: `uninitializePlugin`
**Signature:**
```python
def uninitializePlugin(mObject) -> None:
```
#### Purpose:** Uninitializes the plugin by deregistering the command.