# Module: Arm

### Pipeline Intent
Provides a rigging module for creating character armatures with IK/FK chains and additional control mechanisms.

### Technical Implementation
Utilizes Maya's internal commands and OpenMaya utilities to construct and manipulate the rig's structure, joint layout, and component organization. Exposes build and setup functions for animators to create and customize their own armature templates.

### Overview
This module is designed to simplify the process of creating character arms with IK/FK chains and additional control mechanisms. It provides a foundation for building customizable armatures that can be used in various animation scenarios.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.base.decorators`, `bmaya.maya.shapes`, `bmaya.maya.util.nameUtils`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Arm`
**Purpose:** Creates a character armature with IK/FK chains and additional control mechanisms.
*Inherits from:* `_ThreeJointIkFkTwist.ThreeJointIkFkTwist`

#### Methods
- `__init__(self, startJoint=None, endJoint=None, name='Arm1', ...)`:
  Initializes the arm module with specified joint names, character, and other settings.

- `build(self):`:
  Builds the IK/FK chain structure and sets up additional control mechanisms.

- `addFkGimbalControl(self):`:
  Adds a secondary control mechanism on top of the existing shoulder FK, allowing for XYZ rotation order control.