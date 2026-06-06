# Module: __Ribbon

### Pipeline Intent
Provides a ribbon module for animators to quickly create and rig characters. This module creates a skeleton with follow joints, drive joints, and controls for animation.

### Technical Implementation
The `__Ribbon` class inherits from the `Module` base class and overrides its `build` method to generate the necessary assets and rigging components. The class takes several parameters in its constructor, including start and end joints, control amount, name, character, parent, side, and mirror flag.

### Overview
The `__Ribbon` module is designed to create a ribbon-shaped skeleton with follow joints and drive joints. It uses Maya's nurbs plane and non-linear deformers to generate the shape of the ribbon. The module also includes controls for animation, such as FK (forward kinematics) and IK (inverse kinematics) chains.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.base`, `bmaya.maya.rigging.shapes`, `bmaya.core.util`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Ribbon`

**Purpose:** Create a ribbon-shaped skeleton with follow joints and drive joints.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, controlAmount=3, name='Ribbon1', character=None, parent=None, side='L', mirror=False):`
    Initializes the ribbon module.
- `build(self):`
    Builds the ribbon module by generating necessary assets and rigging components.
- `buildRibbon(self, startJoint, endJoint, name, twist=True, sine=False, identifier=''):` 
    Builds a ribbon with optional twisting or sinusoidal deformations.

#### Attributes
- `startJoint`: The starting joint of the ribbon.
- `endJoint`: The ending joint of the ribbon.
- `controlAmount`: The number of controls in the ribbon.
- `name`: The name of the ribbon module.
- `character`: The character to which the ribbon belongs.
- `parent`: The parent node of the ribbon module.
- `side`: The side of the ribbon (L or R).
- `mirror`: A flag indicating whether the ribbon should be mirrored.

#### Global Variables
- `Ribbon`: The class itself.

---

Documentation Drift:

* None found.