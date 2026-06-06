# Module: `bm_softCluster`

### Pipeline Intent
A tool to create a cluster deformer with the same weights as the soft selection.

### Technical Implementation
Uses Maya's OpenMaya and cmds modules to interact with the scene, retrieving information about the selected objects, their components, and their weights. Handles different types of objects (meshes, nurbs curves, and lattices) by utilizing MItSelectionList and MFnSingleIndexedComponent or MFnTripleIndexedComponent depending on the object type.

### Overview
The `softCluster` function generates a cluster deformer that mimics the same soft selection as the input. This is achieved by iterating through each selected component, retrieving its weight influence, and setting it on the cluster deformer.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** maya.OpenMaya, maya.cmds

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `softCluster`

**Signature:**
```python
def softCluster():
```
#### Arguments
None.

#### Returns
A cluster deformer with the same weights as the soft selection.

---

### 🏷️ `CLASS` :: No classes in this file.

---

### Documentation Drift

None found.