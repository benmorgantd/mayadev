Here is the documentation for the file:

**Module: bm_copyWeights**

### Pipeline Intent
Provides a tool to copy skin cluster and weights from one target mesh to another. Designed to streamline character rigging performance file management.

### Technical Implementation
Exposes automated versioning utilities using standard library modules `maya.cmds`, `maya.OpenMaya`, and `maya.mel`. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The `bm_copyWeights` module offers a tool for animators to copy skin cluster weights from one target mesh to another. This simplifies character rigging performance file management by preserving the relationships between meshes.

### Cross-Module Dependencies

* **Internal Framework Links:** None
* **External Dependencies:** Maya.cmds, OpenMaya, Mel

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

#### Methods: N/A

---

### 🏷️ `FUNCTION` :: `copy_weights`

**Signature:**
```python
def copy_weights(source_mesh=None, target_meshes=None, method="closestPoint"):
```
#### Arguments:
- `source_mesh`: The source mesh to copy from (str)
- `target_meshes`: The destination meshes to copy to (list)
- `method`: Derived from the copyWeights "surfaceAssociation" tag. Options include "closestPoint", "rayCast", or "closestComponent" (str)

#### Returns:
- None

---

### 🏷️ `FUNCTION` :: `get_selection`

**Signature:**
```python
def get_selection():
```
#### Arguments: N/A

#### Returns:
- `[use_verts (bool), source_mesh (str), target_meshes (list)]` (list)

---

**Documentation Drift**

* None found.