# Module: namingTool

### Pipeline Intent
Provides a graphical user interface (GUI) for animators to rename character rig performance files based on localized directory scaffolding. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules, leveraging Qt libraries for GUI development.

### Overview
The Naming Tool module offers a user-friendly interface for renaming character rig performance files according to the studio's directory structure. This tool streamlines the process of assigning unique names to performance files while maintaining consistency across different operating systems.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.lib.Qt`, `bmaya3.maya.ui`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `NamingTool`
**Purpose:** A GUI tool for renaming character rig performance files based on localized directory scaffolding.

*Inherits from:* `qtbase.SimpleWindow`

#### Methods
- `__init__(self, parent=None, title='Naming Tool')`: Initializes the Naming Tool window.
- `_addWidgets(self)`: Adds UI widgets to the main layout.
- `doRename(self)`: Handles the renaming process upon clicking the "Rename" button.

---

### 🏷️ `FUNCTION` :: `run`
**Signature:**
```python
def run():
```
#### Returns
- None

---

### 🏷️ `GLOBAL VARIABLE` :: None
No global variables are defined in this module.