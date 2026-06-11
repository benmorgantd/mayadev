Here is the documentation for the `NeckHead` module:

# Module: NeckHead
## Pipeline Intent
The `NeckHead` module is a custom rigging component designed to create a neck/head hierarchy in Maya. It extends the `FkTwist` class and provides additional functionality for building and constraining twist controls.

## Technical Implementation

This module imports necessary modules from the `bmaya` package, including `maya.cmds`, `maya.api.OpenMaya`, `rigging.modules.FkTwist`, `base.decorators.wrapBuild`, `util.nameUtils`, and `core.constants`. The `NeckHead` class inherits from `FkTwist` and overrides its `__init__` method to set specific attributes for the neck/head rig.

The `build` method is decorated with `wrapBuild` from `bmaya.base.decorators` to ensure proper construction of the rig. It calls the `buildNeckHead` method, which in turn builds the twist controls using the `FkTwist` class.

The `buildNeckHead` method calculates the distance between the start and end components and then constrains each twist control point along that distance using Maya's point constraint tool. It also sets up an aim constraint to orient the twist control space group towards the world up vector (UP_AXIS).

## Overview

The `NeckHead` module provides a custom rigging component for creating neck/head hierarchies in Maya. It extends the `FkTwist` class and includes additional functionality for building and constraining twist controls.

## Cross-Module Dependencies
* Internal Framework Links: `bmaya.maya.rigging.modules.FkTwist`, `bmaya.base.decorators.wrapBuild`
* External Dependencies: None

### 🏷️ `CLASS` :: NeckHead
**Purpose:** Custom rigging component for creating neck/head hierarchies in Maya.
*Inherits from:* `FkTwist`

#### Methods
- `__init__(self, start_joint=None, end_joint=None, exclude=[], name="NeckHead1", character=None, parent=None, shapeType="cube", mirror=False, side="L", alignWorld=False, twistAxis="X", exponent=1):` Initializes the `NeckHead` object with optional parameters for the rig.
- `build(self):` Builds the neck/head hierarchy using the `FkTwist` class and constrains the twist controls.
- `buildNeckHead(self):` Builds the twist controls along the distance between the start and end components.

Note: This documentation follows the strict formatting rules and categorizes code objects strictly using the terms "CLASS", "FUNCTION", or "GLOBAL VARIABLE".