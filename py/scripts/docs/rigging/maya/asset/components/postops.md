# Module: postops

### Pipeline Intent
Provides the PostOps component, a Python file that enables custom logic execution on a rig after it is built.

### Technical Implementation
Imports and extends the `Component` class from the `bmaya.maya.asset.components.component` module. Utilizes the `os` module to generate the relative path of the PostOps instance.

### Overview
The PostOps component serves as a starting point for custom post-processing operations on character rigs, allowing users to execute custom logic after the rig is built.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.component`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `PostOps`
**Purpose:** Extends the base Component class for post-processing operations on character rigs.
*Inherits from:* `Component`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the PostOps instance with an asset and component type.

---

### 🏷️ `FUNCTION` :: `relativePath`
**Signature:**
```python
@property
def relativePath(self):
```
#### Description
Returns the relative path of the PostOps instance as a string, using the `os.path.join` function to combine the 'rig', 'components', and type-specific directory structure.