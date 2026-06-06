# Module: mesh

### Pipeline Intent
Provides a MayaComponent-based class for managing mesh assets in the pipeline. This module defines a Mesh class that contains the model for an Asset.

### Technical Implementation
Uses inheritance from `MayaComponent` to establish a foundation for storing and retrieving asset metadata.

### Overview
The `Mesh` class is designed as a container for holding mesh-related data, providing a way to organize and manage mesh assets within the pipeline.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.component`, `bmaya.maya.asset.components.mayaComponent`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Mesh`
**Purpose:** A MayaComponent-based class for managing mesh assets in the pipeline.

*Inherits from:* `MayaComponent`

#### Methods
- `__init__(self, asset, componentType)`: Initializes a new Mesh instance with an asset and component type.
	Arguments:
	- self (Mesh): The current object instance.
	- asset: The parent asset this mesh belongs to.
	- componentType: The type of component (e.g., "mesh", "rig", etc.).

---

### 🏷️ `PROPERTY` :: `relativePath`
**Signature:**
```python
@property
def relativePath(self):
```
#### Returns
- A file path representing the location of this mesh asset, in the format `/mesh/mesh.ma`.