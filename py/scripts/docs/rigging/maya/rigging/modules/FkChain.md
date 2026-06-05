# Module: FkChain

### Pipeline Intent
Provides a foundational framework for building FK (Forward Kinematics) chains in character rigging, facilitating the creation of articulated joints and drives.

### Technical Implementation
Uses Maya's cmds module to interact with the Maya API. Leverages decorators from `bmaya3.rigging.base.decorators` to implement build workflows. Incorporates shape libraries from `bmaya3.rigging.shapes` for joint creation. Utilizes name utilities from `bmaya3.core.nameUtils` for naming conventions.

### Overview
The FkChain module serves as a building block for constructing FK chains in character rigging, enabling the creation of articulated joints and drives. This module provides a foundation for creating complex character rigs by establishing a hierarchical structure of joints and drives.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.base`, `bmaya3.rigging.shapes`, `bmaya3.core`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `FkChain`

**Purpose:** A foundational module for building FK (Forward Kinematics) chains in character rigging.

#### Methods
- `__init__(self, startJoint=None, endJoint=None, exclude=[], name='FkChain1', character=None, parent=None, shapeType='cube', mirror=False, side='L', alignWorld=False)`:
	+ Initializes the FkChain module with optional parameters for starting and ending joints, exclusion list, name, character, parent, shape type, mirroring, and world alignment.
- `build(self)`: @wrapBuild decorator wraps this method, which builds the FK chain by finding suitable joints, creating drive joints, and constructing fk controls.

---

### 🏷️ `FUNCTION` :: `findHierarchyJoints`
**Signature:**
```python
def findHierarchyJoints(self, exclude=[]) -> list:
```
#### Arguments
- `exclude`: List of joints to be excluded from the hierarchy chain.