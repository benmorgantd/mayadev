Here is the Markdown documentation for the `Arm` module:

# Module: Arm

### Pipeline Intent
The `Arm` module represents a fundamental component of the character rigging system. It provides the structural foundation for the arm, including FK and IK controls.

### Technical Implementation
This module extends the `_ThreeJointIkFkTwist` class to create an arm-specific implementation. The `build` method initializes the arm's components and sets up the alignment with the world space. The `addFkGimbalControl` method adds a secondary control for gimbal rotation on top of the existing shoulder FK.

### Overview
The `Arm` module is responsible for setting up the basic structure of the character arm, including the FK and IK controls. This module also provides a mechanism to add additional controls for gimbal rotation.

### Cross-Module Dependencies
* **Internal Framework Links:** `_ThreeJointIkFkTwist`, `shapelib`, `nameUtils`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Arm`
**Purpose:** Represents an arm component in the character rigging system.
*Inherits from:* `_ThreeJointIkFkTwist`

#### Methods
- `__init__(self, ...)`: Initializes the arm with given parameters.
- `build(self)`: Builds the arm's components and sets up alignment with world space.
- `addFkGimbalControl(self)`: Adds a secondary control for gimbal rotation on top of the existing shoulder FK.

---

Note: This documentation is generated based on the provided local symbol meta-data and source code contents.