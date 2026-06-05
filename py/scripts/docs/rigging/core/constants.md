# Module: constants

### Pipeline Intent
Provides a collection of named constants and utility values for the Maya rigging pipeline, serving as a centralized hub for asset type definitions, joint naming conventions, and layout control structure initialization.

### Technical Implementation
Exposed through Python dictionaries and f-strings, these constants leverage built-in modules like `os` to generate path-related information. The script also defines control naming patterns using suffixes and side designations.

### Overview
This module offers a set of pre-defined values for character rigging, including asset types, joint numbering, layout controls, and mesh file extensions. These constants facilitate the creation and organization of Maya assets by providing consistent naming conventions and structural guidelines.

### Cross-Module Dependencies
* **Internal Framework Links:** None noted.
* **External Dependencies:** `os`, `maya.cmds`

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A (constants module)

#### Constants

- **TEMPLATES_PATH**: [No actual implementation]
- **ASSET_TYPES**: ['prop', 'environment', 'character', 'head']
- **COUNT_START**: 0
- **SIDE_NAMES**: {'left': 'L', 'right': 'R', 'middle': 'M'}
- **JOINT_SUFFIX**: 'JNT'
- **DOWN_AXIS**, **SPINE_UP_AXIS**, **UP_AXIS**: ['X', 'Y', or 'Z']
- **ROOT_JOINT**: f'root_{COUNT_START}_{SIDE_NAMES["middle"]}_{JOINT_SUFFIX}'
- **CTRL_SUFFIX**: 'ctrl'
- **TOP_LAYOUT_CONTROL** and **BOTTOM_LAYOUT_CONTROL**: layout control names based on `COUNT_START`
- **MESH_SUFFIX**: 'mesh'
- **REQUIRED_PLUGINS**: ['matrixNodes', 'quatNodes']
- **UNIT_VECTORS**: {'X': [1, 0, 0], 'Y': [0, 1, 0], 'Z': [0, 0, 1]}
- **POSTOPS_TEMPLATE**: a template string for post-processing operations
- **LAYOUT_CONTROL_COUNT**: 3
- **MODULE_SUFFIX**: 'LIMB'

Note: Documentation drift detected in `TEMPLATES_PATH` (commented out implementation).