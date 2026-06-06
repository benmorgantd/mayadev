# Module: layout

### Pipeline Intent
Provides the foundation for creating a character rig by importing the skeleton and mesh, setting up main rig groups and sets, and establishing a stack of offset controls.

### Technical Implementation
Leverages Maya's `cmds` module to interact with the scene. Utilizes class-based inheritance from the `Module` class and incorporates shape library (`shapelib`) and constants (`constants`) imports for precise control over rig component creation.

### Overview
The Layout module sets up the necessary structure for a character rig by importing the skeleton, mesh, and creating main rig groups and sets. It also establishes a stack of offset controls that can be used to position the rig in the scene before building the rest of the rig.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.modules`, `bmaya.core.constants`, `bmaya.maya.rigging.shapes`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Layout`

**Purpose:** Create the foundation for a character rig by setting up main rig groups and sets, importing the skeleton and mesh, and establishing a stack of offset controls.

#### Methods
- `__init__(self, character=None)`: Initialize the Layout module with optional character parameter.
- `build(self)`: Build the rig structure by importing the skeleton and mesh, creating main rig groups and sets, and setting up offset controls.
- `makeRigSets(self)`: Create a set for the mesh component.
- `makeRigGroups(self)`: Create the main rig groups, including mesh, skeleton, and modules.
- `makeCtrls(self)`: Set up a stack of offset controls.

---

Note: The code does not include any documentation drift.