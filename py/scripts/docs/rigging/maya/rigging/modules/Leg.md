# Module: Leg

### Pipeline Intent
Automates the creation of a character leg rig with inverse kinematics and forward kinematics chains. Enforces proper naming conventions for animators.

### Technical Implementation
Imports relevant modules from `bmaya3.rigging.base.decorators` and `bmaya3.shapes` to utilize decorators and shape libraries. Implements the `Leg` class as a hybrid of `_ThreeJointIkFkTwist.ThreeJointIkFkTwist` and `_Foot.Foot`.

### Overview
The `Leg` module provides a standardized way to create character leg rigs, including IK and FK chains. It also handles naming conventions and enforces consistency across different OS environments.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.base.decorators`, `bmaya3.shapes`
* **External Dependencies:** None

## API Taxonomy Reference

### CLASS :: Leg

**Purpose:** Automates the creation of a character leg rig with inverse kinematics and forward kinematics chains.

#### Methods
- `__init__(self, startJoint=None, ankle=None, ball=None, heel=None, bankOut=None, bankIn=None, toeTip=None, name='Leg1', character=None, parent=None, mirror=False, side='L')`: Initializes the leg rig with specified joints and parameters.
- `build(self)`: Builds the leg rig by creating IK and FK chains, constraining joints, and setting up driver groups.
- `addFkGimbalControl(self)`: Adds a second control on top of the existing leg fk that has zxy (2) rotation order.
- `addIkToeBend(self)`: Creates a group in the ik reverse hierarchy that's the parent of the ball ik handle and has the pivot of the next joint in the hierarchy.

---

Note: The documentation drift log is empty for this file, as there are no discrepancies between the docstrings and actual code.