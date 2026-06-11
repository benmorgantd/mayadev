Here is the generated Markdown documentation for the `FkChain` module:

# Module: FkChain
### Pipeline Intent
The `FkChain` module is designed to create a forward kinematic (FK) chain of joints in Maya. It allows users to specify start and end joints, as well as exclude certain joints from the chain.

### Technical Implementation
The `FkChain` class inherits from `module.Module`, which provides basic functionality for rigging modules. The class has several attributes: `start_joint`, `end_joint`, `exclude`, `name`, `character`, `parent`, `shape_type`, `mirror`, and `align_world`. These attributes are used to customize the FK chain's behavior.

The `__init__` method initializes the module, setting its name, type, character, shape type, mirror side, and alignment world. It also sets the parent joint, start joint, end joint (if specified), and exclusion list.

The `build` method is decorated with `@wrapBuild`, which indicates that it should be executed in a build context. This method finds the joints that belong in the chain using the `find_hierarchy_joints` method, creates drive joints using the `create_drive_joints` method, and builds FK controls using the `build_fk_controls` method.

### Overview
The `FkChain` module provides a way to create complex FK chains in Maya. It can be used to create realistic character animations by specifying start and end joints, as well as excluding certain joints from the chain.

### Cross-Module Dependencies
* **Internal Framework Links:** `module`, `base.decorators`, `shapes.shapelib`, `util.nameUtils`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `FkChain`
**Purpose:** Create a forward kinematic (FK) chain of joints in Maya.

**Attributes:**

- `start_joint`: The starting joint of the FK chain.
- `end_joint`: The ending joint of the FK chain. If not specified, the chain will expand through the DAG and trim itself at excluded joints.
- `exclude`: A list of joints to exclude from the FK chain.
- `name`: The name of the FK chain module.
- `character`: The character associated with the FK chain.
- `parent`: The parent joint of the FK chain.
- `shape_type`: The shape type of the FK chain (e.g., "cube").
- `mirror`: A boolean indicating whether to mirror the FK chain.
- `side`: The side of the body (L or R) for mirroring.
- `align_world`: A boolean indicating whether to align the FK chain with the world.

#### Methods:

- `__init__(self, ...)`: Initializes the FK chain module.
- `build(self)`: Builds the FK chain using the specified joints and attributes.