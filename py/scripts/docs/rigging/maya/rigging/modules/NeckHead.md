# Module: NeckHead

### Pipeline Intent
Provides a character rigging module for animators to efficiently create and manage neck and head components in Maya.

### Technical Implementation
Utilizes the `FkTwist` class from `bmaya3.rigging.modules` and wraps it with `wrapBuild` decorator. Exposes methods for building and setting up constraints for twist controls.

### Overview
The NeckHead module serves as a foundation for creating neck and head components in Maya-based character rigs. It extends the functionality of the FkTwist class, allowing animators to define start and end joints, exclude specific segments, and apply constraints for twist controls.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.rigging.modules.FkTwist`, `bmaya3.core.nameUtils`, `bmaya3.core.constants`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `NeckHead`
**Purpose:** A character rigging module for neck and head components in Maya.

*Inherits from:* `FkTwist.FkTwist`

#### Methods
- `__init__(self, ...)`: Initializes the NeckHead object with start joint, end joint, exclude list, name, character, parent, shape type, mirror, side, align world, twist axis, and exponent.
- `build(self)`: Calls the buildNeckHead method to construct the neck and head components.
- `buildNeckHead(self)`: Builds the FkTwist structure and applies constraints for twist controls.

---

### 🏷️ `FUNCTION` :: `buildNeckHead`
**Signature:**
```python
def buildNeckHead(self):
```

#### Method Body

* Calls `self.buildFkTwist()` to construct the FkTwist structure.
* Calculates the start and end points of the neck and head components.
* Applies constraints for twist controls by creating point constraints, calculating weights, and setting aim constraints.

---

### Documentation Drift
* None detected.