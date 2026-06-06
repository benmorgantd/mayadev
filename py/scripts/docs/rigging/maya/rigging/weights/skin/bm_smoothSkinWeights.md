# Module: bm_smoothSkinWeights

### Pipeline Intent
Provides automated skin weight smoothing for character rig performance files. This module is designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes utilities using standard library `os` and `shutil` modules, handling directory generation asynchronously when creating nested version tracks.

### Overview
This module provides a set of functions for smoothing skin weights in Maya character rigs. It can be used to automate the process of setting skin weights for each vertex to the average of its neighbors.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.skin`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `getSkinCluster`

**Signature:**
```python
def getSkinCluster(dag):
```

#### Arguments
- dag (MDagPath): A MDagPath for the mesh we want to investigate.

#### Returns
- skin_cluster (str): The name of the skin cluster node.
- skin_cluster_obj (om.MObject): The MObject for that skin cluster node.

---

### 🏷️ `FUNCTION` :: `smoothSkinWeights`

**Signature:**
```python
def smoothSkinWeights():
```

#### Description
Sets the weights for each vertex to the average of its neighbors.

---

Documentation Drift:
None detected.