Here is the documentation for the `SingleJoint` module:

# Module: SingleJoint

### Pipeline Intent
The `SingleJoint` module is responsible for building a single joint control on a given joint in Maya.

### Technical Implementation
This module inherits from `module.Module` and uses decorators to wrap its build method. It initializes with several parameters, including the start joint, name, character, parent, shape type, mirror flag, side, align world, and add offset control flags. The `build` method creates a single joint control on the given joint and adds it to the component list.

### Overview
The `SingleJoint` module is used to create a single joint control in Maya. It takes several parameters to customize the creation of the joint control. The module uses decorators to wrap its build method, which allows for custom initialization and setup of the joint control.

### Cross-Module Dependencies

* **Internal Framework Links:** `bmaya.maya.rigging.base`, `bmaya.maya.rigging.shapes`, `bmaya.maya.util`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `SingleJoint`

**Purpose:** Builds a single joint control on a given joint.

**Inherits from:** `module.Module`

#### Methods
- `__init__(self, start_joint=None, name="singleJoint1", character=None, parent=None, shapeType="cube", mirror=False, side="L", align_world=None, addOffsetControl=False, offsetShapeType="cube")`: Initializes the SingleJoint module with the given parameters.
- `build(self)`: Builds a single joint control on the given joint.

---

I hope this documentation meets your requirements. Let me know if you have any further requests!