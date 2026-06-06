# Module: averageVertexSkinWeightCmd

### Pipeline Intent
Provides a scripting tool for Maya to automate the process of assigning skin weights to vertices based on proximity to the operating vertex. This command is designed to maintain the maximum number of influences and apply a brush value to the resulting weight calculation.

### Technical Implementation
This module utilizes the OpenMaya and OpenMayaAnim libraries to interact with Maya's internal data structures and execute custom commands. The `AverageVertexSkinWeightCmd` class defines the logic for processing user input flags, parsing dependencies, and performing the actual weight assignment.

### Overview
The `averageVertexSkinWeightCmd` command takes two optional flags: `-i` or `--index`, which specifies the vertex index to operate on, and `-v` or `--value`, which sets the brush value used in the weight calculation. The command iterates through surrounding vertices, calculates their distances from the operating vertex, and applies a weighted average based on these distances.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.animRig`, `bmaya.maya.rigging.buildio`
* **External Dependencies:** Maya.cmds, OpenMaya, PyMel

## API Taxonomy Reference

### 🏷️ `CLASS` :: AverageVertexSkinWeightCmd
**Purpose:** Script command for assigning skin weights to vertices based on proximity.

#### Methods
- `__init__(self)`: Initializes the command with default values.
- `isUndoable(self): Returns True, indicating that the command is undoable.
- `doIt(self, args)`: Processes user input flags and performs the actual weight assignment.
- `undoIt(self): Sets the old weights to restore the previous state.
- `redoIt(self): Performs the same actions as `doIt`, but for redoing an undone action.

---

### 🏷️ `FUNCTION` :: cmdCreator
**Signature:**
```python
def cmdCreator():
```
#### Returns:
- `ompx.asMPxPtr(AverageVertexSkinWeightCmd())`: Creates and returns a pointer to the `AverageVertexSkinWeightCmd` class instance.

---

### 🏷️ `FUNCTION` :: syntaxCreator
**Signature:**
```python
def syntaxCreator():
```
#### Returns:
- `om.MSyntax()`: Returns an instance of the Maya syntax parser.

---

### 🏷️ `GLOBAL VARIABLE` :: kPluginCmdName
* **Type:** String
* **Value/Purpose:** The command name used to register this script with Maya.