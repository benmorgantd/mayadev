Here is the Markdown documentation for the Spline module:

# Module: Spline

### Pipeline Intent
This module is designed to create a spline-based rigging system that allows for advanced control over joint movements. The pipeline intent is to provide a flexible and customizable way to create complex character rigs.

### Technical Implementation
The Spline module uses Maya's built-in IK handle and curve tools to create a spline-based rig. It also utilizes various utility nodes and Python code to create a sophisticated system that can be controlled by multiple joints and controllers.

### Overview
The Spline module is designed to work in conjunction with other modules, such as the FK and IK modules, to provide a comprehensive character rigging solution. The module provides advanced control over joint movements through the use of various utility nodes and Python code.

### Cross-Module Dependencies
* **Internal Framework Links:** bmaya.core.constants, bmaya.maya.util.nameUtils, bmaya.maya.util.mathUtils, bmaya.maya.rigging.base.decorators, bmaya.maya.rigging.shapes.shapelib, bmaya.maya.rigging.base.module
* **External Dependencies:** Maya.cmds

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Spline`
**Purpose:** This class is used to create a spline-based rig that can be controlled by multiple joints and controllers.
*Inherits from:* `module.Module`

#### Methods
- `__init__(self, start_joint=None, end_joint=None, name="Spline1", character=None, side="M", mirror=False, parent=None, setupTwist=True, controlAmount=3, stretchy=True, startTwistParent=None, shapeType="cube")`: Initializes the spline module.
- `build(self)`: Creates a spline-based rig and sets up the necessary nodes and connections.
- `build_fk_controls(self)`: Creates FK controls for the spline rig.
- `buildIkControls(self)`: Creates IK controls for the spline rig.
- `setupStretch(self)`: Sets up stretch factor calculations for the spline rig.
- `buildSplineDriverJoints(self)`: Creates driver joints for the spline rig.
- `setupAdvancedTwist(self)`: Sets up advanced twist control for the spline rig.
- `setupIkEndJoint(self)`: Sets up an IK end joint for the spline rig.
- `setupIkHierarchy(self)`: Sets up the IK hierarchy for the spline rig.

---

I hope this meets your requirements! Let me know if you need any further assistance.