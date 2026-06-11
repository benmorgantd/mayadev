# Module: `_Foot`

### Pipeline Intent
The `_Foot` module is responsible for creating a rigging system for the foot of a character. It defines a class `Foot` that represents the foot and its components, including joints, controllers, and IK handles.

### Technical Implementation
The module imports necessary classes from other modules, such as `maya.cmds`, `shapelib`, `nameUtils`, and `mathUtils`. The `Foot` class has several methods for creating joints, IK handles, and controllers. These methods include `build`, `createFkHierarchy`, `createIkHierarchy`, `createDriveHierarchy`, `createReverseHierarchy`, `createIkHandles`, and `createIkControls`.

### Overview
The `_Foot` module is used to create a rigging system for the foot of a character. It defines a class `Foot` that represents the foot and its components, including joints, controllers, and IK handles.

### Cross-Module Dependencies

* **Internal Framework Links:** The module relies on other modules in the codebase, such as `maya.cmds`, `shapelib`, `nameUtils`, and `mathUtils`.
* **External Dependencies:** None