Here is the Markdown documentation for the `Leg` module:

# Module: Leg

### Pipeline Intent
The `Leg` module is responsible for building and managing a character's leg rigging structure. It inherits from `_ThreeJointIkFkTwist` and `_Foot`, allowing it to leverage the features of both parent modules.

### Technical Implementation
The `Leg` class initializes its components by calling the constructors of its parent classes, setting up the IK/FK chain and foot structures. The `build` method constructs the leg rigging hierarchy, including the FK and IK chains, foot drive joints, and various control components. It also sets up parent-child relationships between these components.

### Overview
The `Leg` module is designed to provide a comprehensive solution for building character legs in Maya. It offers a robust set of features for controlling the movement and animation of the leg, including FK and IK chains, foot drive joints, and various control components.

### Cross-Module Dependencies

* **Internal Framework Links:**
	+ `_ThreeJointIkFkTwist`
	+ `_Foot`
* **External Dependencies:** None

## API Taxonomy Reference

### CLASS :: Leg
**Purpose:** Builds and manages a character's leg rigging structure.
*Inherits from:* `_ThreeJointIkFkTwist`, `_Foot`

#### Methods
- `__init__(self, ...)`: Initializes the leg components.
- `build(self)`: Constructs the leg rigging hierarchy.
- `addFkGimbalControl(self)`: Adds a second control on top of the existing leg FK.
- `addIkToeBend(self)`: Creates a group in the IK reverse hierarchy that's the parent of the ball IK handle.

---

I hope this documentation meets your requirements! Let me know if you need any further assistance.