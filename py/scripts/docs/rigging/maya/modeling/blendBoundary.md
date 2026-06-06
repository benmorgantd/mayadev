# Module: blendBoundary

### Pipeline Intent
Provides utility for blending vertex normals between two separate meshes where vertices have the same world space position.

### Technical Implementation
Leverages pymel.core and PyMel to access Maya's API. Utilizes list comprehensions, dictionaries, and mathematical operations to optimize performance.

### Overview
The `blendBoundary` module offers a single function, `blendBoundary`, which blends vertex normals between two separate meshes based on their world space position. This process is particularly useful when dealing with complex character rigging pipelines where multiple meshes need to be aligned and averaged for optimal animation results.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** `pymel.core`, `time`

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `blendBoundary`
**Signature:**
```python
def blendBoundary(meshA, meshB, distanceTolerance=0.001):
```
#### Arguments
- `meshA`: The first mesh object to blend.
- `meshB`: The second mesh object to blend.
- `distanceTolerance`: Optional float parameter for the maximum allowed difference in world space position (default: 0.001).

#### Returns
None

---

### 🏷️ `FUNCTION` :: `gatherBorderInfo`
**Signature:**
```python
def gatherBorderInfo(meshObj):
```
#### Arguments
- `meshObj`: The mesh object to gather border information from.

#### Returns
A tuple containing:
	* `border`: A list of boundary vertices.
	* `points`: A list of world space points for the boundary vertices.
	* `normals`: A list of normal vectors for the boundary vertices.