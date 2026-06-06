# Module: FkChain

### Pipeline Intent
Provides flexible FK chain rigging functionality for animators, handling joint hierarchies and mirroring. Enables creation of articulated skeletons with adjustable constraints.

### Technical Implementation
Utilizes decorators from `bmaya.maya.rigging.base.decorators` to encapsulate the build process, ensuring thread-safe and asynchronous execution. Integrates shape manipulation capabilities from `bmaya.maya.shapes`.

### Overview
The FkChain module offers a comprehensive rigging framework for creating articulated skeletons in Maya. It enables animators to define FK chains with custom start and end joints, mirroring, and alignment.

### Cross-Module Dependencies
* **Internal Framework Links:** 
	+ `bmaya.maya.rigging.base`: For `module` and decorator-based pipeline management.
	+ `bmaya.maya.shapes`: For shape manipulation and creation.
	+ `bmaya.util`: For naming utilities.
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `FkChain`
**Purpose:** A modular implementation of a FK chain rigging system.

#### Methods
- `__init__(self, ...)`: Initializes the FkChain module with optional start and end joints, exclusions, name, character, parent, shape type, mirroring, side, and alignment settings.
- `build(self)`: Builds the FK chain by finding hierarchical joints to include in the chain, creating drive joints, and constructing FK controls.

---

Note: Documentation Drift

* No discrepancies found between docstrings and actual code.