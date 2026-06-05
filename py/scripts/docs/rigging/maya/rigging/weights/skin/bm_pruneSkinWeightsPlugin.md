# Module: bm_pruneSkinWeightsPlugin

### Pipeline Intent
Provides a Maya plugin for pruning skin weights on a selected mesh. This tool helps maintain character rig performance by removing redundant weight influences.

### Technical Implementation
The `PruneWeights` class is an OpenMayaMPx command that utilizes the `omMPx.MPxCommand` and `omAnim.MFnSkinCluster` classes to prune the skin weights of a selected mesh. It uses a combination of Python and MEL scripts to achieve this functionality.

### Overview
This plugin provides a Maya command for pruning skin weights on a selected mesh. The command takes into account the original influences and averages them based on their proximity to the vertex being processed, thus preserving the overall shape of the character while removing redundant weight influences.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.mesh`, `bmaya.maya.asset.components.skeleton`, `bmaya.maya.rigging.weights.weightio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `PruneWeights`
**Purpose:** Prunes skin weights on a selected mesh.

#### Methods
- `__init__(self)`: Initializes the command.
- `isUndoable(self)`: Returns whether the command is undoable.
- `doIt(self, args)`: Calls the redoIt function to prune the skin weights.
- `redoIt(self)`: Prunes the skin weights and returns the data for undoing.
- `undoIt(self)`: Sets the original weights using the data from redoIt.

### 🏷️ `FUNCTION` :: `cmdCreator`
**Signature:**
```python
def cmdCreator():
  return omMPx.asMPxPtr(PruneWeights())
```
#### Returns
- A pointer to the PruneWeights command.

### 🏷️ `FUNCTION` :: `initializePlugin`
**Signature:**
```python
def initializePlugin(mObject):
  fnPlugin = omMPx.MFnPlugin(mObject, "Ben Morgan", "1.0.0", "Any")
  try:
    fnPlugin.registerCommand(kPluginCmdName, cmdCreator)
  except:
    om.MGlobal.displayError("Failed to register command {0}".format(kPluginCmdName))
```
#### Returns
- None

### 🏷️ `FUNCTION` :: `uninitializePlugin`
**Signature:**
```python
def uninitializePlugin(mObject):
  fnPlugin = omMPx.MFnPlugin(mObject)
  try:
    fnPlugin.deregisterCommand(kPluginCmdName)
  except:
    om.MGlobal.displayError("Failed to deregister command {0}".format(kPluginCmdName))
```
#### Returns
- None