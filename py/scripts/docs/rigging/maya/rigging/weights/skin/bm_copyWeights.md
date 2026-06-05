# Module: bm_copyWeights

### Pipeline Intent
Provides a tool for copying skin cluster and weights from one target mesh to another. This module is designed to facilitate efficient rigging performance by allowing animators to easily replicate character weights across different meshes.

### Technical Implementation
This module utilizes the Maya API (maya.cmds, maya.OpenMaya) and MEL scripting language to automate the process of copying skin cluster and weights from a source mesh to one or more target meshes. The `copy_weights` function is the core component of this tool, responsible for handling various scenarios such as copying only to selected vertices or binding multiple target meshes.

### Overview
The `bm_copyWeights` module offers a convenient way to transfer skin cluster and weights between meshes in Maya. This functionality is particularly useful when working with complex character rigs where consistency across different body parts is crucial.

### Cross-Module Dependencies

* **Internal Framework Links:** None
* **External Dependencies:** maya.cmds, maya.OpenMaya, PyMel

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

#### Methods: N/A

---

### 🏷️ `FUNCTION` :: `copy_weights`
**Signature:**
```python
def copy_weights(source_mesh=None, target_meshes=None, method="closestPoint"):
```
#### Arguments
- `source_mesh`: The source mesh to copy from (str)
- `target_meshes`: A list of destination meshes to copy to (list)
- `method`: Derived from the "surfaceAssociation" tag. Options include "closestPoint", "rayCast", or "closestComponent" (str)

#### Returns
- None

---

### 🏷️ `FUNCTION` :: `get_selection`
**Signature:**
```python
def get_selection():
```
#### Arguments: N/A

#### Returns
- A list containing `use_verts` (bool), `source_mesh` (str), and `target_meshes` (list)

---

### 🏷️ `GLOBAL VARIABLE` :: N/A