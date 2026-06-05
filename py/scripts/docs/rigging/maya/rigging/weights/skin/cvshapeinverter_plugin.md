# Module: cvshapeinverter_plugin

### Pipeline Intent
Provides a Maya Deformer Node that inverts the shape of a corrective mesh by applying a series of matrices to deformed points. This node is used to correct character rig performance issues.

### Technical Implementation
Exposes an OpenMayaMPx-based implementation for creating and initializing a cvShapeInverter plugin, which can be registered with Maya's Deformer Node system. Handles attribute creation and connection setup for the corrective mesh, deformed points, and inversion matrix inputs.

### Overview
The `cvShapeInverter` class is a Maya Deformer Node that applies a series of matrices to deformed points to correct character rig performance issues. This node takes three input attributes: `correctiveMesh`, `deformedPoints`, and `inversionMatrix`. The node inverts the shape of the corrective mesh by applying the matrices to the deformed points.

### Cross-Module Dependencies
* **Internal Framework Links:** [None]
* **External Dependencies:** maya.OpenMayaMPx, maya.OpenMaya

## API Taxonomy Reference

### 🏷️ `CLASS` :: cvShapeInverter
**Purpose:** Maya Deformer Node for inverting the shape of a corrective mesh.

#### Methods
- `__init__(self)`: Initializes the node's attributes and internal state.
- `deform(self, data, itGeo, localToWorldMatrix, geomIndex)`: Applies the matrices to deformed points to correct character rig performance issues.
- `creator()`: Returns an instance of the cvShapeInverter class.

#### Attributes
- `aCorrectiveGeo`: Input attribute for the corrective mesh.
- `aDeformedPoints`: Input attribute for the deformed points.
- `aMatrix`: Input attribute for the inversion matrix.

---

### 🏷️ `FUNCTION` :: creator
**Signature:**
```python
def creator() -> OpenMayaMPx.MPxPtr:
```
#### Returns
- An instance of the cvShapeInverter class.

---

### 🏷️ `FUNCTION` :: initialize
**Signature:**
```python
def initialize():
```
#### Purpose
Initializes the node's attributes and connects them to the Maya Deformer Node system.

---

### 🏷️ `FUNCTION` :: uninitializePlugin
**Signature:**
```python
def uninitializePlugin(mobject):
```
#### Purpose
Unregisters the cvShapeInverter plugin from Maya's Deformer Node system.