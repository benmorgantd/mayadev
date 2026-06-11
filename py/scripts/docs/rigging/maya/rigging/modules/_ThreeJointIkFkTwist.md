Here is the Markdown documentation for the `_ThreeJointIkFkTwist` module:

# _ThreeJointIkFkTwist

### Pipeline Intent
The `_ThreeJointIkFkTwist` module is designed to create a three-joint IK/FK twist setup for a character's leg. This module aims to provide a foundation for creating more complex character rigging setups by integrating inverse kinematics (IK) and forward kinematics (FK) techniques.

### Technical Implementation
The `_ThreeJointIkFkTwist` module inherits from `IkFkChain`, which is a parent class that provides the basic structure for building IK/FK chains. The module's constructor initializes the IK/FK chain by setting up the start and end joints, as well as the character and parent nodes.

### Overview
The `_ThreeJointIkFkTwist` module consists of several methods that work together to create a three-joint IK/FK twist setup:

* `__init__`: Initializes the IK/FK chain with the start and end joints, character, and parent nodes.
* `build`: Builds the IK/FK chain by setting up the bind joints, drive joints, and control curves for the upper and lower twists.
* `setupUpperTwist`: Sets up the upper twist joints and controls.
* `setupLowerTwist`: Sets up the lower twist joints and controls.
* `addStretchySetup`: Creates a stretchy limb setup that allows for dynamic stretching of the character's leg.

### Cross-Module Dependencies
The `_ThreeJointIkFkTwist` module depends on several other modules in the `bmaya.maya.rigging.modules` package, including:

* `IkFkChain`
* `MayaComponent`

These dependencies are used to create and manage the IK/FK chain, as well as to integrate the twist setup with the character's overall rigging.

## API Taxonomy Reference

### 🏷️ `CLASS` :: `_ThreeJointIkFkTwist`
**Purpose:** Creates a three-joint IK/FK twist setup for a character's leg.

*Inherits from:* `IkFkChain`

#### Methods
