# Module: _ThreeJointIkFkTwist

### Pipeline Intent
Provides a three-joint IK/FK twist setup for character rigging. This module is designed to create a flexible and stretchy limb that can be used in various animation scenarios.

### Technical Implementation
The `_ThreeJointIkFkTwist` module utilizes Maya's scripting API to create a complex rigging setup that involves several joints, constraints, and controllers. The code defines two main classes: `ThreeJointIkFkTwist` and its child classes `UpperTwist` and `LowerTwist`. These classes are responsible for setting up the IK/FK twist rig, including creating joints, constraints, and controllers.

### Overview
The `_ThreeJointIkFkTwist` module is designed to create a flexible and stretchy limb that can be used in various animation scenarios. The code defines two main classes: `UpperTwist` and `LowerTwist`, which are responsible for setting up the IK/FK twist rig, including creating joints, constraints, and controllers.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.base.decorators`, `bmaya3.rigging.shapes.shapeio`
* **External Dependencies:** Maya.cmds, OpenMaya

## API Taxonomy Reference

### CLASS :: ThreeJointIkFkTwist
**Purpose:** Provides a three-joint IK/FK twist setup for character rigging.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, name='ThreeJointIkFkTwist1', character=None, parent=None, mirror=False, side='L', fkikDefault=0, alignWorld=True)`: Initializes the three-joint IK/FK twist setup.
- `build(self, startJoint, endJoint, worldAimTarget=None, downAxis='X', upAxis='Y', followWorld=True)`: Builds the IK/FK twist rig.
- `setupUpperTwist(self)`: Sets up the upper twist joint and its corresponding controller.
- `setupLowerTwist(self)`: Sets up the lower twist joint and its corresponding controller.
- `addStretchySetup(self)`: Adds a stretchy setup to the IK/FK twist rig.

#### Attributes
- `modType`: The type of the module (Three-Joint IK/FK Twist).
- `contract`: A list of joints that are part of the contract.
- `driveJoints`: A list of drive joints used in the IK/FK twist rig.
- `ikComponents`: A list of IK components used in the IK/FK twist rig.
- `fkComponents`: A list of FK components used in the IK/FK twist rig.

---

### CLASS :: UpperTwist
**Purpose:** Sets up the upper twist joint and its corresponding controller.

#### Methods
- `__init__(self)`: Initializes the upper twist joint and its controller.
- `setup(self)`: Sets up the upper twist joint and its controller.

#### Attributes
- `joints`: A list of joints that are part of the upper twist setup.
- `controls`: A list of controllers used in the upper twist setup.

---

### CLASS :: LowerTwist
**Purpose:** Sets up the lower twist joint and its corresponding controller.

#### Methods
- `__init__(self)`: Initializes the lower twist joint and its controller.
- `setup(self)`: Sets up the lower twist joint and its controller.

#### Attributes
- `joints`: A list of joints that are part of the lower twist setup.
- `controls`: A list of controllers used in the lower twist setup.

---

### GLOBAL VARIABLE :: IkFkChain
**Type:** Class
**Value/Purpose:** Provides a base class for IK/FK chain components.