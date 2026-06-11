# Module: IkFkChain

### Pipeline Intent
IkFkChain module is designed to facilitate the creation of inverse kinematics (IK) and forward kinematics (FK) chains for Maya rigs, allowing for more complex character movements and interactions.

### Technical Implementation
This module inherits from both `IkChain` and `FkChain`, combining the functionality of IK and FK into a single entity. The `build` method initializes the chain by finding hierarchy joints, creating drive joints, and setting up the IK-FK system. The `buildFkIkSetup` method is responsible for building the individual IK and FK components.

### Overview
The IkFkChain module provides a comprehensive framework for managing complex character movements and interactions in Maya. It combines inverse kinematics (IK) and forward kinematics (FK) to create highly realistic and dynamic movements.

### Cross-Module Dependencies

* **Internal Framework Links:**
	+ `IkChain`
	+ `FkChain`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `IkFkChain`

**Purpose:** Combine inverse kinematics (IK) and forward kinematics (FK) for Maya rigging.

*Inherits from:* `FkChain.FkChain`, `IkChain.IkChain`

#### Methods
- `__init__(self, ...):` Initializes the IkFkChain with start and end joints.
- `build(self):` Builds the IK-FK system by finding hierarchy joints, creating drive joints, and setting up the IK-FK system.
- `buildFkIkSetup(self, ...):` Builds individual IK and FK components.

---

I hope this meets your requirements! Let me know if you need any further assistance.