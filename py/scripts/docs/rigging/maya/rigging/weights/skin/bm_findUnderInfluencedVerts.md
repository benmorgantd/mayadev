Here is the documentation for the file:

# Module: `bm_findUnderInfluencedVerts`

### Pipeline Intent
Provides a tool to identify and prune under-influenced vertices from a skin cluster, helping to optimize rig performance.

### Technical Implementation
Utilizes Maya's OpenMaya and OpenMayaAnim libraries to interact with the scene, selecting vertices and retrieving skin cluster information. Exposes automated pruning functionality based on user-defined maximum influence count.

### Overview
This module allows artists to streamline their workflow by identifying and eliminating under-influenced vertices from a character rig's skin cluster, reducing computational overhead and improving overall performance.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.skin`, `bmaya.maya.rigging.weights.weightio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `find_under_influenced_verts`
**Signature:**
```python
def find_under_influenced_verts(max_influences=4):
```
#### Arguments
- max_influences (int): The maximum number of influences allowed for a vertex. Defaults to 4.

#### Returns
None

---

### 🏷️ `FUNCTION` :: `prune_influences`
**Signature:**
```python
def prune_influences(max_influences=3):
```
#### Arguments
- max_influences (int): The maximum number of influences allowed for a vertex. Defaults to 3.

#### Returns
None

---

Note that there is no `CLASS` or `GLOBAL VARIABLE` documentation in this file, as it only contains two functions: `find_under_influenced_verts` and `prune_influences`.