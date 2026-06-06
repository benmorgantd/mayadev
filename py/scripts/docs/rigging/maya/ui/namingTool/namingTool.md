# Module: namingTool

### Pipeline Intent
Provides a graphical user interface for renaming and organizing assets in Maya. This tool is designed to simplify the process of assigning unique names to character rig performance files, making it easier for animators to work with complex scenes.

### Technical Implementation
Uses Qt libraries for creating GUI elements and OpenMaya (OpenMaya) for interacting with Maya's command line interface. The tool exposes a simple window with input fields, dropdown menus, and a rename button, allowing users to assign names based on specific categories and naming conventions.

### Overview
The Naming Tool is a Maya-based UI module that simplifies the process of renaming character rig performance files. It provides a user-friendly interface for selecting names from predefined lists, and automatically generates unique names based on the selected criteria.

### Cross-Module Dependencies

* **Internal Framework Links:** `bmaya.lib.Qt`, `bmaya.maya.ui.qtbase`
* **External Dependencies:** OpenMaya (OpenMaya)

## API Taxonomy Reference

### 🏷️ `CLASS` :: `NamingTool`
**Purpose:** Simple window-based UI for renaming character rig performance files in Maya.

#### Methods
- `__init__(self, parent=None, title='Naming Tool')`: Initializes the NamingTool instance.
  - **Arguments:**
    - parent (None): The parent window of this tool.
    - title ('Naming Tool'): The title of the tool's window.
  - **Returns:** None

- `_addWidgets(self)`: Adds GUI elements to the tool's window, including a text input field, two dropdown menus, and a rename button.

  - **Arguments:** None
  - **Returns:** None

- `doRename(self)`: Handles the rename button click event, prompting the system to rename selected assets based on user-defined criteria.
  - **Arguments:** None
  - **Returns:** None

### 🏷️ `FUNCTION` :: `run`
**Signature:**
```python
def run() -> None:
```
#### Arguments: None

#### Returns: None