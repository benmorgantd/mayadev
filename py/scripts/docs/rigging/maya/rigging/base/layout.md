# Module: layout

### Pipeline Intent
Provides the foundation for character rigging by importing skeleton and mesh components, creating main rig groups, and setting up a stack of offset controls. This module serves as the entry point for rig creation.

### Technical Implementation
Utilizes Maya's `cmds` module to interact with the scene graph, leveraging the studio's standard directory structure. Asynchronous handling is employed through Python's built-in threading capabilities.

### Overview
The Layout module initializes the character rig by importing essential components, setting up main groups and sets, and creating a stack of offset controls for positioning the rig in the scene.

### Cross-Module Dependencies
* **Internal Framework Links:** `module`, `decorators`, `shapes` (from `bmaya3.rigging`), `constants` (from `bmaya3.core`)
* **External Dependencies:** Maya.cmds

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Layout`
**Purpose:** Initializes character rig by importing skeleton and mesh components, setting up main rig groups and sets, and creating a stack of offset controls.

#### Methods
- `__init__(self, character=None)`: Constructor initializes module type, shape type, name, and character.
- `build(self)`: Builds the rig hierarchy, imports skeleton and mesh, creates main groups and sets, and sets up offset controls.
- `makeRigSets(self)`: Creates a set for the mesh component.
- `makeRigGroups(self)`: Sets up main rig groups, including skeleton, mesh, and modules groups.
- `makeCtrls(self)`: Creates a stack of offset controls for positioning the rig in the scene.

---

### 🏷️ `FUNCTION` :: `addMoveablePivot`
**Signature:**
```python
def add_moveable_pivot(shp):
```
#### Description:
Adds a moveable pivot to the specified shape.