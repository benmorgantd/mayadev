Here is the Markdown documentation for the `skeleton.py` file:

# Module: skeleton

### Pipeline Intent
Provides serialization and deserialization utilities for joint hierarchies in Maya rigs. This component serves as a bridge between the rig's skeletal structure and external data storage.

### Technical Implementation
The Skeleton class inherits from the MayaComponent base class, utilizing its asset management and component type handling capabilities. It leverages the `maya.cmds` module to interact with the Maya API and manipulate joint hierarchies.

### Overview
The Skeleton class is designed to facilitate the saving and loading of rig skeletons in a standardized format. This enables animators to easily transfer their work between different machines, environments, or projects.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.mayaComponent`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: Skeleton
**Purpose:** Represents the joint hierarchy for a Maya rig and provides serialization and deserialization utilities.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Skeleton instance with an asset and component type.
- `relativePath(self)`: Returns the relative file path for the skeleton component's serialized data.
- `serializeJointHierarchy(cls, rootJoint)`: Serializes the joint hierarchy rooted at the specified joint, returning a list of joint data dictionaries.
- `deserializeJointHierarchy(cls, data)`: Deserializes the provided joint data and creates new joints in Maya, recreating the original hierarchy.

---

### 🏷️ `GLOBAL VARIABLE` :: None

Note: There are no global variables defined in this file.