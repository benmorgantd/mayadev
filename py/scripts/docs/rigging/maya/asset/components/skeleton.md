Here is the Markdown documentation for the `skeleton` module:

# Module: skeleton
### Pipeline Intent
The Skeleton class is a MayaComponent that contains the joint hierarchy for a rig. It contains the logic for serializing and deserializing a joint hierarchy, which is used to save and load the skeleton component of a rig.

### Technical Implementation

This module extends the `MayaComponent` class and provides methods for serializing and deserializing the joint hierarchy of a rig. The serialization process involves gathering data about each joint, including its name, parent joint, world matrix, and radius. The deserialization process creates new joints in Maya and sets their properties based on the serialized data.

### Overview
The Skeleton class is responsible for managing the joint hierarchy of a rig. It provides methods for serializing and deserializing the joint hierarchy, which allows for easy saving and loading of the skeleton component of a rig.

### Cross-Module Dependencies

* **Internal Framework Links:** MayaComponent, maya.cmds
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Skeleton`
**Purpose:** A MayaComponent that contains the joint hierarchy for a rig.
**Inherits from:** MayaComponent

#### Methods
- `__init__(self, asset, component_type)`: Initializes the Skeleton class with an asset and a component type.
- `relative_path(self)`: Returns the relative path of the skeleton file (e.g., "rig/components/skeleton.ma").
- `serialize_joint_hierarchy(cls, root_joint)`: Serializes the joint hierarchy of a rig.
- `deserialize_joint_hierarchy(cls, data)`: Deserializes the joint hierarchy of a rig.

---

Note: This documentation follows the strict formatting rules and critical analysis guidelines provided earlier.