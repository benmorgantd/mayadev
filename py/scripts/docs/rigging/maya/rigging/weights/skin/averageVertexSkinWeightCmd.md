# Module: averageVertexSkinWeightCmd

### Pipeline Intent
Provides a script tool for animators to manage and adjust skin weights in Maya. This command allows users to set vertex weights based on the distance from the operating vertex.

### Technical Implementation
The `averageVertexSkinWeightCmd` script tool uses OpenMaya and OpenMayaAnim libraries to interact with Maya's API. It exposes a command-line interface for animators to specify the index of the vertex, the value of the brush pressure, and the number of maximum influences to maintain.

### Overview
This module is designed to help animators manage skin weights in Maya by averaging the surrounding vertex weights based on their distance from the operating vertex. The script tool uses a brush-like approach to influence the vertex weight, allowing for more precise control over the skinning process.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** OpenMaya (om), OpenMayaAnim (oma)

## API Taxonomy Reference

### 🏷️ `CLASS` :: AverageVertexSkinWeightCmd
**Purpose:** Provides a script tool for animators to manage and adjust skin weights in Maya.

#### Methods
- `__init__(self)`: Initializes the command.
- `isUndoable(self)`: Returns True if the command is undoable.
- `doIt(self, args)`: Performs the actual weight calculation based on the brush pressure and distance from the operating vertex.
- `undoIt(self)`: Undoes the previous weight calculation by setting the original weights back to the skin cluster.
- `redoIt(self)`: Redoes the previous weight calculation.

---

### 🏷️ `FUNCTION` :: cmdCreator
**Signature:**
```python
def cmdCreator():
```
#### Returns
- `ompx.asMPxPtr(AverageVertexSkinWeightCmd())`: Creates and returns an instance of the `AverageVertexSkinWeightCmd` class as a Maya command.

---

### 🏷️ `FUNCTION` :: syntaxCreator
**Signature:**
```python
def syntaxCreator():
```
#### Returns
- `om.MSyntax()`: Creates and returns a syntax object for the `averageVertexSkinWeightCmd` command.

---

### 🏷️ `GLOBAL VARIABLE` :: kPluginCmdName
- **Type:** String
- **Value/Purpose:** The name of the plugin command, used to register and deregister the command.