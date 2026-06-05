# Module: blendBoundary

### Pipeline Intent
Provides a utility to blend vertex normals between two separate meshes where vertices have the same world space position. This allows for smooth transitions when combining different character rig parts.

### Technical Implementation
Uses the `pymel.core` library to interact with Maya and manipulate mesh data. The primary method is `gatherBorderInfo`, which identifies boundary vertices and extracts their positions and normals. The secondary method, `blendBoundary`, blends vertex normals between the two meshes based on a specified distance tolerance.

### Overview
This module enables animators to seamlessly blend character rig parts by averaging vertex normals along shared boundaries. This process reduces visual artifacts and enhances overall performance.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** `pymel.core`

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

---

### 🏷️ `FUNCTION` :: gatherBorderInfo

**Signature:**
```python
def gatherBorderInfo(meshObj):
```
#### Arguments
- meshObj (PyNode): The input mesh object to analyze.

#### Returns
- border, points, normals (tuple): A tuple containing the boundary vertices, their positions, and their normals.

---

### 🏷️ `FUNCTION` :: blendBoundary

**Signature:**
```python
def blendBoundary(meshA, meshB, distanceTolerance=0.001):
```
#### Arguments
- meshA (PyNode): The first input mesh object.
- meshB (PyNode): The second input mesh object.
- distanceTolerance (float): The tolerance for considering vertices as "close enough" to blend.

#### Returns
N/A

---

### 🏷️ `GLOBAL VARIABLE` :: N/A