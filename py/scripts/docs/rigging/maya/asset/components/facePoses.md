# Module: facePoses

### Pipeline Intent
Class for the FacePoses component, which is a maya file that contains an animation of poses. An animator can hand-animate each pose on the rig and save these off.

### Technical Implementation
The `FacePoses` class inherits from `MayaComponent`. In the constructor (`__init__`), it calls the parent's constructor with the `asset` and `component_type`.

#### Methods
- `__init__(self, asset, component_type)`: Initializes the FacePoses component.
- `@property relative_path(self)`: Returns the relative path of the FacePoses file.

### Overview
The `FacePoses` class represents a maya file that contains an animation of poses. It inherits from `MayaComponent`.

### Cross-Module Dependencies

* **Internal Framework Links:** `mayaComponent`
* **External Dependencies:** None