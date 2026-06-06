# Module: facePoses

### Pipeline Intent
Provides a FacePoses component for animators to hand-animate poses on the rig and save them off.

### Technical Implementation
Instantiates a MayaComponent class from `bmaya.maya.asset.components.component` and initializes it with asset path and component type. Utilizes the standard library's `os` module to generate the relative file path.

### Overview
The FacePoses component serves as a container for storing animated poses of a character's face, allowing animators to create custom animations and save them off for further editing or rendering.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.component`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: FacePoses
**Purpose:** Facilitates the creation and management of a FacePoses component for animators to hand-animate poses on the rig.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the FacePoses component with an asset path and component type.
- `@property relativePath(self)`: Returns the relative file path for the FacePoses component.

---

Note: There is no documentation drift detected.