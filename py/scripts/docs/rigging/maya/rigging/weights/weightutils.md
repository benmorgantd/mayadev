# Reference Component: `bmaya.maya.rigging.weights.weightutils`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference

### 🛠️ `bake_delta_mush_to_skin_cluster(dag)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `get_skin_cluster_name(dag)`

```text
A convenience function for finding the skinCluster deforming a mesh.
params:
    dag (MDagPath): A MDagPath for the mesh we want to investigate.
returns:
    skinCluster (str), skinClusterObj (MObject)
```

### 🛠️ `get_skin_cluster_obj(dag)`

```text
A convenience function for finding the skinCluster deforming a mesh.
params:
    dag (MDagPath): A MDagPath for the mesh we want to investigate.
returns:
    skinCluster (str), skinClusterObj (MObject)
```

### 🛠️ `get_skin_cluster_obj_from_shape(shape)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `get_skin_cluster_weight_dict(skinClusterObj)`

```text
Return the weight dictionary for the given skin cluster
```

### 🛠️ `get_skin_cluster_weights(skinClusterObj, components=None)`

```text
Returns the weights from a skinCluster and any data necessary for setting
the weights later down the road
params:
    skinClusterObj (MObject) : The MObject for the skinCluster you want to get weights from
    components (MObject) : If given, the skinCluster will only gives weights for these verts
```

### 🛠️ `prune_skin_weights(maxInfluence=4)`

```text
Sets the weights for each vertex to the average of its neighbors.
```

### 🛠️ `prune_weight_list(weights, maxInfluence=4)`

```text
Prunes the given list to have only four non-zero values
```

### 🛠️ `quick_skin()`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `set_skin_cluster_weights(skin_cluster_obj, influence_indices, weights, components=None)`

```text
needs API type arrays
```

### 🛠️ `skin(joints, mesh)`

```text
No functional arguments or usage blocks specified.
```
