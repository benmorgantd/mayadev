Here is the Markdown documentation for the provided Python file:

# Module

### Pipeline Intent
Provides production file path verification and localized directory scaffolding for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The Module class is the base class for all rig modules. It contains basic attributes and methods that all modules will need, such as building the module, creating the module node, adding attributes to the node, finding mirror nodes, etc. Each specific module (such as Arm, Leg, Spine, etc.) will inherit from this class and implement its own build method to create the specific rig for that module.

### Cross-Module Dependencies
* **Internal Framework Links:**
	+ `bmaya.maya.asset.components.animRig`
	+ `bmaya.maya.asset.components.build`
	+ `bmaya.maya.rigging.joint`
	+ `bmaya.maya.util.dagUtils`
	+ `bmaya.maya.util.nameUtils`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Module`
**Purpose:** Base class for all rig modules.

#### Methods
- `__init__(self, character=None, name='module1', modType='Module', parent=None, side='L', mirror=False, shapeType='cube', alignWorld=None)`: Initializes the module with optional parameters.
- `build(self)`: Should get defined by child class.
- `makeNode(self)`: Creates the module node before anything gets built.
- `parseForMayaAttr(self, attr)`: Converts attribute values to Maya-compatible types.
- `addNodeAttrs(self)`: Adds attributes to the module node.
- `findMirror(self, node)`: Returns the mirrored node of the same type if it's in the scene.
- `doMirror(self)`: Creates a mirrored copy of the module (if mirror is True).
- `determineParent(self, parent)`: Determines the parent for the module or its components.
- `parentModule(self)`: Parent the whole module's group into the module group for the character.

### 🏷️ `FUNCTION` :: `addMoveablePivot(cls, ctrl)`
**Signature:**
```python
def addMoveablePivot(cls, ctrl):
```
#### Arguments
- `ctrl`: The control to add a moveable pivot to.

#### Returns
- None

#### Description:
Adds a new control that represents the pivot for this control.