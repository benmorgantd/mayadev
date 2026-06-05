Here is your requested documentation:

**Module: bm_smooth_skinned_curve**

### Pipeline Intent
Provides a moving average-based method for smoothing skinned nurbs curve weights in Maya.

### Technical Implementation
 Utilizes Maya's OpenMaya and OpenMayaAnim libraries to retrieve information about the skin cluster, influence objects, and CVs on the target curve. The `smooth_weights` function applies a weighted average of neighboring CVs' weights to each point on the curve, with adjustable strength.

### Overview
This module enables animators to fine-tune the behavior of skinned nurbs curves in Maya by applying a moving average-based smoothing algorithm. This can help reduce the effect of isolated points or sharp changes in the curve's shape.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.animRig`, `bmaya.maya.rigging.buildio`
* **External Dependencies:** `maya.cmds`, `OpenMaya`, `OpenMayaAnim`

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `find_skin_cluster`
**Signature:**
```python
def find_skin_cluster(dag):
```
#### Arguments
- dag (type): The DAG path of the target mesh.

#### Returns
- skin_cluster (str): The name of the skin cluster associated with the input mesh.
- skin_cluster_obj (om.MObject): The MObject representation of the skin cluster.

### 🏷️ `FUNCTION` :: `smooth_weights`
**Signature:**
```python
def smooth_weights(curve=None, smooth_strength=.25):
```
#### Arguments
- curve (str): The name of the nurbs curve to process. Optional.
- smooth_strength (float): The strength of the smoothing algorithm. Defaults to 0.25.

#### Returns
None

### 🏷️ `GLOBAL VARIABLE` :: None