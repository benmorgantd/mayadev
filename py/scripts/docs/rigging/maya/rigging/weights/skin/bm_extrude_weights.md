# Module: bm_extrude_weights

### Pipeline Intent
Automated weight extrusion for skin clusters in Maya, allowing animators to quickly fix intersection issues on complex meshes.

### Technical Implementation
This module uses OpenMaya and OpenMayaAnim APIs to interact with Maya's internal data structures. It leverages `omMPx.MPxCommand` to create a custom command that applies the weight extrusion algorithm.

### Overview
The `bm_extrude_weights` module provides an interactive tool for animators to quickly fix intersection issues on complex meshes by extruding skin cluster weights to nearby vertices in inverse normal directions. This is particularly useful when working with thick meshes or those prone to self-intersections.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.weights.skin`
* **External Dependencies:** Maya.cmds, OpenMaya, OpenMayaAnim

## API Taxonomy Reference

### 🏷️ `CLASS` :: ExtrudeWeights
**Purpose:** Custom command for weight extrusion in skin clusters.

#### Methods
- `isUndoable(self)`: Verifies whether the command is undoable.
- `doIt(self, args)`: Performs the actual weight extrusion process.
- `redoIt(self)`: Redoes the previous weight extrusion operation.
- `undoIt(self)`: Undoes the previous weight extrusion operation.

---

### 🏷️ `FUNCTION` :: cmdCreator
**Signature:**
```python
def cmdCreator():
  return omMPx.asMPxPtr(ExtrudeWeights())
```
#### Returns
- An instance of `omMPx.MPxCommand` (ExtrudeWeights) wrapped in an `omMPx.asMPxPtr`.

---

### 🏷️ `FUNCTION` :: initializePlugin
**Signature:**
```python
def initializePlugin(mObject):
  fnPlugin = omMPx.MFnPlugin(mObject, "Ben Morgan", "1.0.0", "Any")
  try:
    fnPlugin.registerCommand(kPluginCmdName, cmdCreator)
  except:
    om.MGlobal.displayError("Failed to register command {0}".format(kPluginCmdName))
```
#### Arguments
- `mObject`: The Maya object representing the plugin.

#### Returns
- None

---

### 🏷️ `FUNCTION` :: uninitializePlugin
**Signature:**
```python
def uninitializePlugin(mObject):
  fnPlugin = omMPx.MFnPlugin(mObject)
  try:
    fnPlugin.deregisterCommand(kPluginCmdName)
  except:
    om.MGlobal.displayError("Failed to deregister command {0}".format(kPluginCmdName))
```
#### Arguments
- `mObject`: The Maya object representing the plugin.

#### Returns
- None

---

### 🏷️ `GLOBAL VARIABLE` :: kPluginCmdName
- **Type:** str
- **Value/Purpose:** The name of the extrude weights command, used for registration and deregistration.