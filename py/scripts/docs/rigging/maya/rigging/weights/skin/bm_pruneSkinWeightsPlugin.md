# Module: `bm_pruneSkinWeightsPlugin`

### Pipeline Intent
Provides a Python plugin for Maya's `skinPercent` command, pruning skin weights for character rig performance files. This module optimizes the workflow by automatically setting weights to zero for non-affecting joints, allowing animators to focus on refining poses.

### Technical Implementation
The plugin utilizes OpenMaya and OpenMayaAnim APIs to access and manipulate Maya's internal data structures. It exposes a `PruneWeights` command that can be executed in the Maya UI or programmatically using the Python API.

### Overview
This module implements a custom `skinPercent` command that prunes skin weights based on influence counts. The plugin utilizes the OpenMayaAnim library to interact with Maya's animation system and perform weight manipulation.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.weights.weightio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `PruneWeights`
**Purpose:** A custom Maya command for pruning skin weights based on influence counts.

#### Methods
- `__init__(self)`: Initializes the command with default settings.
- `isUndoable(self)`: Returns `True`, indicating that this command is undoable.
- `doIt(self, args)`: Invokes the `redoIt` method to prune skin weights and save the original state for undoing.
- `redoIt(self)`: Reduces influence counts by pruning non-affecting joints and normalizing the remaining weights.
- `undoIt(self)`: Restores the original skin weights by setting the old values.

### 🏷️ `FUNCTION` :: `pruneSkinWeights`
**Signature:**
```python
def pruneSkinWeights(self, maxInfluence=4):
```
#### Arguments
- `maxInfluence` (int): The maximum influence count to consider for pruning. Defaults to 4.

#### Returns
- None

### 🏷️ `FUNCTION` :: `pruneWeightList`
**Signature:**
```python
def pruneWeightList(self, weights, maxInfluence=4):
```
#### Arguments
- `weights` (list): The list of skin weights to prune.
- `maxInfluence` (int): The maximum influence count to consider for pruning. Defaults to 4.

#### Returns
- pruned_weights: A normalized list of skin weights with non-affecting joints set to zero.

### 🏷️ `FUNCTION` :: `getSkinCluster`
**Signature:**
```python
def getSkinCluster(self, dag):
```
#### Arguments
- `dag` (MDagPath): The MDagPath object representing the mesh to investigate.

#### Returns
- skin_cluster (str): The name of the skin cluster affecting the mesh.
- skin_cluster_obj (MObject): The MObject representation of the skin cluster.

### 🏷️ `FUNCTION` :: `cmdCreator`
**Signature:**
```python
def cmdCreator():
  return omMPx.asMPxPtr(PruneWeights())
```
#### Returns
- A pointer to the `PruneWeights` command.

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
#### Arguments
- `mObject` (MObject): The MObject representation of the Maya plugin.

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
#### Arguments
- `mObject` (MObject): The MObject representation of the Maya plugin.

### Documentation Drift

* None detected.