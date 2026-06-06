# Module: cvshapeinverter_plugin

### Pipeline Intent
Provides an MPxDeformerNode implementation for inverting corrective shapes within Maya's rigging pipeline.

### Technical Implementation
Uses OpenMayaMPx to create a deform node that reads matrices and deformed points, then applies these inputs to perform shape inversion calculations. This allows animators to utilize the corrective mesh data and invert its effects on the character rig.

### Overview
The cvShapeInverter module is designed to enable Maya artists to correct for unwanted shape deformation in their rigged characters. By providing an MPxDeformerNode, this module can be easily integrated into existing pipelines, offering a robust and efficient way to reverse the effects of corrective shapes.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.animRig`, `bmaya.maya.asset.components.build`, `bmaya.maya.rigging.weights.weightio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: cvShapeInverter
**Purpose:** An MPxDeformerNode implementation for inverting corrective shapes.

#### Methods
- `__init__(self)`: Initializes the node's internal state.
- `deform(self, data, itGeo, localToWorldMatrix, geomIndex)`: Performs shape inversion calculations based on input matrices and deformed points.
- `creator()`: Returns a pointer to an instance of this class.
- `initialize()`: Sets up attribute connections for the node.
- `initializePlugin(mobject)`: Registers the node with the Maya plugin system.
- `uninitializePlugin(mobject)`: Deregisters the node from the Maya plugin system.

---

### 🏷️ `FUNCTION` :: creator
**Signature:**
```python
def creator():
    return OpenMayaMPx.asMPxPtr(cvShapeInverter())
```
#### Arguments
None

#### Returns
A pointer to an instance of cvShapeInverter

---

### 🏷️ `FUNCTION` :: initialize
**Signature:**
```python
def initialize():
    # Code...
```
#### Arguments
None

#### Returns
None