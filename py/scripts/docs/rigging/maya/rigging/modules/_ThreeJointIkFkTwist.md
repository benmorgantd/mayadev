# Module: `_ThreeJointIkFkTwist`

### Pipeline Intent
This module provides a class-based implementation of a three-joint IK-FK twist rig for Maya. The rig is designed to mimic the movement of a human arm, allowing for natural-looking animations.

### Technical Implementation
The `ThreeJointIkFkTwist` class inherits from `IkFkChain`, which provides a foundation for building more complex character rigs. This module uses various Maya API nodes and functions to create a stretchy limb setup, including distanceBetween, condition, multDL, and multiplyDivide nodes.

### Overview
The `_ThreeJointIkFkTwist` module is part of the `bmaya.maya.rigging.modules` package, which provides a range of pre-built character rig modules for Maya. This specific module focuses on building a three-joint IK-FK twist rig with stretchy limb capabilities.

### Cross-Module Dependencies
* **Internal Framework Links:**
	+ `IkFkChain`: A parent class providing a foundation for building complex character rigs.
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `ThreeJointIkFkTwist`
**Purpose:** Builds a three-joint IK-FK twist rig with stretchy limb capabilities.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, ...):` Initializes the rig with optional start and end joint parameters.
- `build(self, startJoint, endJoint, worldAimTarget=None, downAxis='X', upAxis='Y', followWorld=True):` Builds the IK-FK twist rig with stretchy limb capabilities.
- `setupUpperTwist(self):` Sets up the upper twist joints and controls.
- `setupLowerTwist(self):` Sets up the lower twist joints and controls.
- `addStretchySetup(self):` Adds a simple stretchy limb setup.

---

Note: The above documentation is based on the provided code and may not cover all aspects of the module's functionality.