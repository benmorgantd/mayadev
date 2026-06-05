# Module: bm_smoothSkinWeights

### Pipeline Intent
Smothes skin weights for a selected polygon mesh in Maya. This module is designed to average the weights of each vertex with its neighboring vertices.

### Technical Implementation
Exposes Pythonic interfaces using OpenMaya (OM) and OpenMayaAnim (OMA). Handles mesh selection, influence object retrieval, and weight manipulation.

### Overview
This module provides a convenience function for finding the skin cluster deforming a mesh. It also contains another function that sets the weights for each vertex to the average of its neighbors, aiming to smooth out the skinning effect.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.component`, `bmaya.maya.rigging.joint`, `bmaya.maya.rigging.weights.weightio`
* **External Dependencies:** Maya.cmds, OpenMaya, OpenMayaAnim

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: getSkinCluster
**Signature:**
```python
def getSkinCluster(dag):
```
#### Arguments
- dag (MDagPath): A MDagPath for the mesh we want to investigate.

#### Returns
- skin_cluster (str): The name of the skin cluster, if found.
- skin_cluster_obj (MObject): The MObject representing the skin cluster.

---

### 🏷️ `FUNCTION` :: smoothSkinWeights
**Signature:**
```python
def smoothSkinWeights():
```
#### Description
Sets the weights for each vertex to the average of its neighbors.