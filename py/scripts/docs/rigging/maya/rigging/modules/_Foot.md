Here is the Markdown documentation for the file:

# Module: _Foot


### Pipeline Intent
Provides a framework for creating and managing foot rigging in Maya. This module exposes a class-based API for animators to create and control the various components of a character's foot.

### Technical Implementation
The `Foot` class is designed to automate the creation and organization of joints, controls, and hierarchy structures necessary for building a realistic foot rig. It utilizes internal libraries and utility functions from the `bmaya3.rigging.shapes` and `bmaya3.core` modules to achieve this functionality.


### Overview
This module is part of the larger `bmaya3` toolkit, which provides a suite of Python classes and utilities for creating and managing complex character rigs in Maya. The `_Foot` module specifically focuses on the creation and management of foot rigging components.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.shapes`, `bmaya3.core`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Foot`
**Purpose:** A class for creating and managing foot rigging components.

#### Methods
- `__init__(self, name='Foot1', ankle=None, ball=None, heel=None, bankOut=None, bankIn=None, toeTip=None)`: Initializes the Foot object with default values.
- `build(self)`: Builds the foot hierarchy, including FK and IK drive joints, and creates controls for each component.
- `createFkHierarchy(self)`: Creates a FK joint chain for the foot.
- `createIkHierarchy(self)`: Creates an IK joint chain for the foot.
- `createDriveHierarchy(self)`: Creates a drive joint chain for the foot.
- `createReverseHierarchy(self)`: Creates a reverse hierarchy of oriented joints.
- `createIkHandles(self)`: Creates IK handles for the ankle and ball joints.
- `createIkControls(self)`: Creates controls for each component of the foot.
- `createFkControls(self)`: Creates controls for the FK drive joint.

### 🏷️ `FUNCTION` :: `parentConstrain(self, jnt1, jnt2)`
**Signature:**
```python
def parentConstrain(self, jnt1, jnt2):
```
#### Arguments
- `jnt1` (str): The name of the first joint.
- `jnt2` (str): The name of the second joint.

#### Returns
- None

### 🏷️ `GLOBAL VARIABLE` :: `nameUtils`, `constants`, `mathUtils`
- **Type:** Modules
- **Value/Purpose:** These modules provide utility functions for naming, constant values, and mathematical operations used throughout the `_Foot` module.