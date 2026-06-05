Here is the Markdown documentation for the file:

# Module

### Pipeline Intent
Provides production file path verification and localized directory scaffolding for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The Module class is the base class for all rig modules, containing basic attributes and methods that all modules will need, such as building the module, creating the module node, adding attributes to the node, finding mirror nodes, etc.

### Cross-Module Dependencies
* **Internal Framework Links:** [List of modules from the codebase manifest that this file imports or interacts with]
	+ None listed.
* **External Dependencies:** [e.g., Maya.cmds, OpenMaya, PyMel]
	+ None listed.

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Module`
**Purpose:** Base class for all rig modules
*Inherits from:* None

#### Methods
- `__init__(self, character=None, name='module1', modType='Module', parent=None, side='L', mirror=False, shapeType='cube', alignWorld=None)`: Initializes the module with attributes.
- `makeNode(self)`: Creates the module node before anything gets built.
- `addNodeAttrs(self)`: Adds attributes to the module node.
- `findMirror(self, node)`: Returns the mirrored node of the same type if it's in the scene. Else returns None.
- `doMirror(self)`: Mirrors the module and its children.
- `parentModule(self)`: Parents the whole module's group into the character modules group.
- `connectComponents(self)`: Connects the module's components to the module.
- `connectBindJoints(self)`: Connects the module's bind joints to their control.

### 🏷️ `FUNCTION` :: `createDriveJoint`
**Signature:**
```python
def createDriveJoint(self, jnt, label='Driver', constrain=True):
```
#### Arguments
- `jnt`: The joint to drive.
- `label`: The label for the driver joint.
- `constrain`: Whether to constrain the driver joint.

### 🏷️ `FUNCTION` :: `captureComponentDefaults`
**Signature:**
```python
def captureComponentDefaults(self):
```
#### No arguments

This function captures the default values of keyable attributes for each component in the module.