Here is the Markdown documentation for the `blendBoundary` module:

# Module: blendBoundary

### Pipeline Intent
The purpose of this utility is to blend the vertex normals between two separate meshes where vertices have the same world space position.

### Technical Implementation
This module utilizes pymel.core and log from bmaya.core to interact with Maya objects. It defines two functions, `gather_border_info` and `blend_boundary`, which are used to identify and blend the vertex normals of two meshes at their shared boundaries.

### Overview
The `blendBoundary` module provides a utility for blending vertex normals between two separate meshes in Maya. This is achieved by identifying the vertices that share the same world space position and then averaging their normals.

### Cross-Module Dependencies
* **Internal Framework Links:** pymel.core, bmaya.core
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `gather_border_info`
**Signature:**
```python
def gather_border_info(meshObj):
```
#### Description:
This function takes a mesh object as input and returns the border vertices, points, and normals of that mesh.

#### Returns:
* `border`: A list of border vertices.
* `points`: A list of 3D points representing the world space positions of the border vertices.
* `normals`: A list of vertex normals for the border vertices.

---

### 🏷️ `FUNCTION` :: `blend_boundary`
**Signature:**
```python
def blend_boundary(mesh_a, mesh_b, distance_tolerance=0.001):
```
#### Description:
This function takes two mesh objects and a distance tolerance value as input. It blends the vertex normals of the two meshes at their shared boundaries.

#### Parameters:
* `mesh_a`: The first mesh object.
* `mesh_b`: The second mesh object.
* `distance_tolerance`: A float value specifying the maximum distance between vertices for them to be considered adjacent (default: 0.001).

#### Returns:
None

---

### GLOBAL VARIABLES
* **`__all__`**: This is a global variable that specifies the module's namespace. It contains only one element, `blend_boundary`, which is the only function exported by this module.

I hope this documentation meets your requirements! Let me know if you need any further assistance.