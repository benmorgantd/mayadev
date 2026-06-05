# Module: Spline

### Pipeline Intent
Provides a mechanism for creating and managing spline-based character rigging in Maya. This module focuses on building the foundation of a character's spine, including creation of joints, controls, and constraints.

### Technical Implementation
This module utilizes various Maya commands and functions to create and manipulate objects such as joints, controls, and curves. It also relies on internal utility modules like `mathUtils` for mathematical operations and `nameUtils` for naming conventions.

### Overview
The Spline module is designed to create a character's spine by generating a series of joints and controls along a spline curve. The module allows for customization of the spine's length, control amount, and other parameters. It also includes features such as automatic parenting of controls and constraints, making it easier to set up and manage complex character rigs.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.core.constants`, `bmaya.rigging.base.decorators`, `bmaya.rigging.shapes.shapelib`, `bmaya.maya.cmds`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Spline(module.Module)`
**Purpose:** A class representing a character's spine, responsible for creating and managing the joints, controls, and constraints that define it.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, name='Spline1', character=None, side='M', mirror=False, parent=None, setupTwist=True, controlAmount=3, stretchy=True, startTwistParent=None, shapeType='cube')`: Initializes the Spline object with optional parameters.
- `build(self)`: Builds the spine by creating and parenting joints, controls, and constraints.
- `buildFkControls(self)`: Creates and configures FK (Forward Kinematics) controls for the spine.
- `buildIkControls(self)`: Creates and configures IK (Inverse Kinematics) controls for the spine.
- `setupStretch(self)`: Sets up stretch factors for the spine's controls.
- `setupAdvancedTwist(self)`: Configures advanced twist features for the spine.
- `setupIkEndJoint(self)`: Creates a joint at the end of the ik chain to serve as an FK-style control.
- `setupIkHierarchy(self)`: Makes a simple switch to make the ik hierarchy behave like an fk one.

---

### 🏷️ `FUNCTION` :: `buildIkSpline(self)`: Builds an IK spline for the spine and returns it along with its corresponding curve node.