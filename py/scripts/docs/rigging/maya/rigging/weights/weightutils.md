Here is the documentation for the `weightutils` module:

# Module: weightutils

### Pipeline Intent
The `weightutils` module provides a set of convenience functions and utilities for working with skin clusters, weights, and mesh deformation in Maya.

### Technical Implementation
This module relies on the Maya Python API (OpenMaya) to interact with the Maya scene graph. It uses various OpenMaya classes such as `MFnSkinCluster`, `MDagPath`, and `MObject` to access and manipulate skin clusters, meshes, and joints.

### Overview
The `weightutils` module provides a range of functions for:

1. Finding and retrieving skin cluster objects from the Maya scene.
2. Getting and setting skin cluster weights.
3. Pruning weight lists to reduce influence count.
4. Converting delta mush deformation to skin cluster weights.
5. Normalizing and pruning skin weights.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:**
	+ Maya.cmds (for scene manipulation)
	+ OpenMaya (for Python API access)

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

No classes are defined in this module.

### 🏷️ `FUNCTION` :: Various

#### Functions
- `get_skin_cluster_name(dag)`: Returns the name of a skin cluster associated with a given mesh.
- `get_skin_cluster_obj(dag)`: Returns the MObject for a skin cluster associated with a given mesh.
- `get_skin_cluster_weights(skinClusterObj, components=None)`: Returns the weights from a skin cluster and any data necessary for setting the weights later down the road.
- `set_skin_cluster_weights(skin_cluster_obj, influence_indices, weights, components=None)`: Sets the weights for a skin cluster.
- `skin(joints, mesh)`: Skins a mesh to a set of joints using Maya's skinning algorithm.
- `quick_skin()`: Quickly skins a selection of meshes to their associated joints.
- `bake_delta_mush_to_skin_cluster(dag)`: Converts delta mush deformation to skin cluster weights.
-