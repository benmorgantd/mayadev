# Reference Component: `bmaya.maya.rigging.weights.skin.bm_copyWeights`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference

### 🛠️ `copy_weights(source_mesh=None, target_meshes=None, method='closestPoint')`

```text
Copies the skin cluster and weights from a target mesh to other meshes.

    :param source_mesh: The source mesh to copy from
    :param target_meshes: The destination meshes to copy to
    :param method: Derived from the copyWeights "surfaceAssociation" tag.
Options include "closestPoint", "rayCast", or "closestComponent"
    :type source_mesh: str
    :type target_meshes: list
    :type method: str
    :return: None
    
```

### 🛠️ `get_selection()`

```text
Returns our selection and determines if we'll copy only to vertices or not.

:return: [use_verts (bool), source_mesh (str), target_meshes (list)]
:rtype: list
```
