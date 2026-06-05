# Module: weightutils

### Pipeline Intent
Provides utility functions for working with Maya's skin clustering and vertex weights.

### Technical Implementation
Exposes a set of Python functions that interact with Maya's OpenMaya API to perform tasks related to skin cluster manipulation, weight calculation, and pruning. These functions are designed to be used in conjunction with the `bmaya.maya.rigging.weights` module to automate various rigging-related tasks.

### Overview
The `weightutils` module provides a set of Python functions that can be used to manipulate Maya's skin clusters and vertex weights. This includes functions for calculating weights, pruning weights, and converting delta mush deformations to skin cluster weights.

### Cross-Module Dependencies
* **Internal Framework Links:** None (standalone module)
* **External Dependencies:** `maya.OpenMaya`, `maya.OpenMayaAnim`, `maya.cmds`, `maya.mel`

## API Taxonomy Reference

### 🏷️ `CLASS` :: None (no classes defined in this file)

#### Methods
None

---

### 🏷️ `FUNCTION` :: getSkinClusterName(dag)
**Signature:**
```python
def getSkinClusterName(dag):
```
#### Arguments
- dag (MDagPath): A MDagPath for the mesh we want to investigate.

#### Returns
- skinCluster (str), skinClusterObj (MObject)

---

### 🏷️ `FUNCTION` :: getSkinClusterObj(dag)
**Signature:**
```python
def getSkinClusterObj(dag):
```
#### Arguments
- dag (MDagPath): A MDagPath for the mesh we want to investigate.

#### Returns
- skinCluster (str), skinClusterObj (MObject)

---

### 🏷️ `FUNCTION` :: getSkinClusterWeights(skinClusterObj, components=None)
**Signature:**
```python
def getSkinClusterWeights(skinClusterObj, components=None):
```
#### Arguments
- skinClusterObj (MObject) : The MObject for the skinCluster you want to get weights from
- components (MObject) : If given, the skinCluster will only gives weights for these verts

#### Returns
- [weights, infIndices, infObjects]

---

### 🏷️ `FUNCTION` :: setSkinClusterWeights(skinClusterObj, influenceIndices, weights, components=None)
**Signature:**
```python
def setSkinClusterWeights(skinClusterObj, influenceIndices, weights, components=None):
```
#### Arguments
- skinClusterObj (MObject) : The MObject for the skinCluster you want to set weights for
- influenceIndices : A list of indices representing the order of the influences
- weights : A list of weights corresponding to each influence index
- components (MObject) : If given, only sets weights for these verts

#### Returns
None

---

### 🏷️ `FUNCTION` :: skin(joints, mesh)
**Signature:**
```python
def skin(joints, mesh):
```
#### Arguments
- joints (list of str): A list of joint names to use as the influences
- mesh (str): The name of the mesh to apply the skinning to

#### Returns
- cstr (str): The name of the newly created skin cluster

---

### 🏷️ `FUNCTION` :: quickSkin()
**Signature:**
```python
def quickSkin():
```
#### Arguments
None

#### Returns
None

---

### 🏷️ `FUNCTION` :: bakeDeltaMushToSkinCluster(dag)
**Signature:**
```python
def bakeDeltaMushToSkinCluster(dag):
```
#### Arguments
- dag (MDagPath): The MDagPath for the mesh we want to convert delta mush deformations to skin cluster weights

#### Returns
None

---

### 🏷️ `FUNCTION` :: pruneWeightList(weights, maxInfluence=4)
**Signature:**
```python
def pruneWeightList(weights, maxInfluence=4):
```
#### Arguments
- weights (list of float): A list of vertex weights to prune
- maxInfluence (int, optional): The maximum number of influences allowed for a vertex. Defaults to 4.

#### Returns
- prunedWeights (list of float)

---

### 🏷️ `FUNCTION` :: pruneSkinWeights(maxInfluence=4)
**Signature:**
```python
def pruneSkinWeights(maxInfluence=4):
```
#### Arguments
- maxInfluence (int, optional): The maximum number of influences allowed for a vertex. Defaults to 4.

#### Returns
- [mFnSkinCluster, dag, selectedComponents, influenceIndices, oldWeights]

---

### 🏷️ `FUNCTION` :: getSkinClusterWeightDict(skinClusterObj)
**Signature:**
```python
def getSkinClusterWeightDict(skinClusterObj):
```
#### Arguments
- skinClusterObj (MObject) : The MObject for the skin cluster to generate a weight dictionary for

#### Returns
- weightDict (dict)

---

Documentation Drift:

* None detected.