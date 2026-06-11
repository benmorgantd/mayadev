Here is the Markdown documentation for the `IkChain` module:
# Module: IkChain

### Pipeline Intent
The `IkChain` module is designed to create a simple single-chain ik system. It builds upon existing ik components and provides a way to define the chain's start and end joints, as well as its parent joint.

### Technical Implementation
The `IkChain` class inherits from `module.Module`. It initializes with parameters for start_joint, end_joint, name, character, parent, mirror, upVector, exclude, and side. The `build` method constructs the ik chain by finding hierarchy joints, creating drive joints, and building ik controls. The `setupIkSpaces` method sets up the ik spaces for the chain.

### Overview
The `IkChain` module is a key component in the rigging pipeline, enabling the creation of single-chain ik systems with customizable start and end joints. It provides a foundation for more complex ik structures by allowing users to define the parent joint and mirror settings.

### Cross-Module Dependencies
* Internal framework links: `module`, `shapelib`
* External dependencies: `maya.cmds`, `OpenMaya`

## API Taxonomy Reference

### CLASS :: IkChain
**Purpose:** Create a simple single-chain ik system.
* Inherits from: `module.Module`
#### Methods
- `__init__(self, ...)`: Initialize the ik chain with parameters for start_joint, end_joint, name, character, parent, mirror, upVector, exclude, and side.
- `build(self)`: Construct the ik chain by finding hierarchy joints, creating drive joints, and building ik controls.
- `buildIkControls(self, driveJoints)`: Build ik controls for the drive joints.
- `setupIkSpaces(self, ikCtrl)`: Set up the ik spaces for the chain.

Note: This documentation is based on the provided code and may not be exhaustive.