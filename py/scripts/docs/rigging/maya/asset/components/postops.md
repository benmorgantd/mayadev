# Module: postops

### Pipeline Intent
Allows users to execute custom logic on a rig after it's built, providing flexibility and control over the asset creation process.

### Technical Implementation
Inherits from `Component` class and utilizes the `os` module for file path management. The `relativePath` property generates a file path based on the component type and extension.

### Overview
The PostOps component is designed to provide users with the ability to run custom scripts or logic on their rigs after they are built, giving them more control over the asset creation process.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.component` (inherited from)
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `PostOps`
**Purpose:** Extends the `Component` class to provide custom logic execution on a rig after it's built.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the PostOps component with an asset and component type.
    + **Arguments:**
        - `asset`: The asset being worked on.
        - `componentType`: The type of component (e.g., arm, leg, etc.).

---

### 🏷️ `PROPERTY` :: `relativePath`
- **Type:** `str`
- **Value/Purpose:** Returns the file path for the PostOps component based on its type and extension.

```python
@property
def relativePath(self):
    return os.path.join('rig', 'components', self.type + self.extension)
```

---

**Documentation Drift:**
None found.