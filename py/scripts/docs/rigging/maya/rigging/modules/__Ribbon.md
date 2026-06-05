# Module: __Ribbon
### Pipeline Intent
Provides production file path verification and localized directory scaffolding for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
The __Ribbon module is a part of the bMAYA rigging toolkit, responsible for creating and managing ribbons (a type of deformation curve) in Maya. This module provides a set of tools for building and controlling ribbons, allowing animators to create complex character movements.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.base`, `bmaya3.rigging.shapes`, `bmaya3.core.constants`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ CLASS :: Ribbon
**Purpose:** Represents a ribbon (a type of deformation curve) in Maya.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, controlAmount=3, name='Ribbon1', character=None, parent=None, side='L', mirror=False, addDeformers=True)`: Initializes the ribbon with the given parameters.
- `build(self)`: Builds and configures the ribbon's components.
- `buildRibbon(self, startJoint, endJoint, name, twist=True, sine=False, identifier='')`: Builds a new ribbon with the specified properties.
- `makeFollowJoints(self, skinnedPlane, startJoint, identifier='')`: Creates follow joints for the ribbon.
- `makeDriveJoints(self, skinnedPlane, startJoint, identifier='')`: Creates drive joints for the ribbon.
- `makeFollowJointControls(self, bindJoints, followJoints)`: Creates controls for the follow joints.
- `skinDriverJointsToPlane(self, driveJoints, skinnedPlane)`: Skins the drive joints to the plane.
- `makeDriverControls(self, startJoint, driveJoints)`: Creates driver controls for the ribbon.
- `addVisibilitySwitches(self)`: Adds visibility switches for the ribbon's components.

### 🏷️ FUNCTION :: buildSkinnedPlane
**Purpose:** Builds a skinned plane for the ribbon.

#### Arguments
* `startJoint`: The starting joint of the ribbon.
* `endJoint`: The ending joint of the ribbon.

#### Returns
* `skinnedPlane`: The built skinned plane.

### 🏷️ FUNCTION :: buildDeformerPlane
**Purpose:** Builds a deformer plane for the ribbon.

#### Arguments
* `startJoint`: The starting joint of the ribbon.
* `endJoint`: The ending joint of the ribbon.
* `skinnedPlane`: The skinned plane to use as a basis for the deformer plane.
* `twist=True`, `sine=False`: Optional arguments to control the type of deformation applied.

#### Returns
* `deformerPlane`: The built deformer plane.