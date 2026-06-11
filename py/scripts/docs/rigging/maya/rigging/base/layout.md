# Module: layout
### Pipeline Intent
The Layout module is the first module in the rig hierarchy. It imports the skeleton and mesh, creates main rig groups and sets, and creates a stack of offset controls to position the rig in the scene.

### Technical Implementation
This module inherits from `module.Module`. The `__init__` method initializes the module with a mod_type, shape_type, name, and character. The `build` method imports the skeleton and mesh components, makes rig sets and groups, and creates offset controls for positioning the rig. The `make_rig_sets`, `make_rig_groups`, and `make_ctrls` methods perform specific tasks within the `build` method.

### Overview
This module is responsible for setting up the base structure of a character rig in Maya. It imports the skeleton and mesh, creates main rig groups and sets, and provides a foundation for further rigging operations.

### Cross-Module Dependencies
* **Internal Framework Links:** module.Module, decorators.wrapBuild, core.constants, log
* **External Dependencies:** maya.cmds

## API Taxonomy Reference

### 🏷️ `CLASS` :: Layout
**Purpose:** Every rig must have a Layout module

#### Methods
- `__init__(self, character=None)`: Initializes the module with a mod_type, shape_type, name, and character
- `build(self)`: Builds the rig by importing skeleton and mesh components and creating main rig groups and sets
- `make_rig_sets(self)`: Creates a set for the mesh component
- `make_rig_groups(self)`: Creates groups for the rig, mesh, and skeleton components
- `make_ctrls(self)`: Creates offset controls to position the rig in the scene