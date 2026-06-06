Here is the documentation for this file:

# Module: bm_findUnderInfluencedVerts

### Pipeline Intent
Provides a tool to prune vertices with less than a specified number of influences in a Maya skin cluster. This helps reduce complexity and improve rig performance.

### Technical Implementation
Utilizes OpenMaya and OpenMayaAnim modules to iterate through selected mesh components, extract skin clusters, and retrieve influence objects and weights. The algorithm identifies vertices with fewer influences than the specified maximum and adds them to an available vertex list for further processing.

### Overview
This module is designed to streamline rigging workflows by automatically removing under-influenced vertices in a Maya skin cluster. This process helps maintain scene integrity while reducing computational overhead.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.cvs`, `bmaya.maya.rigging.weights.skin`
* **External Dependencies:** `maya.OpenMaya`, `maya.OpenMayaAnim`

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `find_under_influenced_verts`
**Signature:**
```python
def find_under_influenced_verts(max_influences=4):
```
#### Arguments
- max_influences (int): The maximum number of influences a vertex can have. Defaults to 4.

#### Returns
None

---

### 🏷️ `FUNCTION` :: `prune_influences`
**Signature:**
```python
def prune_influences(max_influences=3):
```
Note: This function is not defined in the provided code, but it seems to be a wrapper for the `find_under_influenced_verts` function with a default value of 3.

Please let me know if you would like me to make any changes.