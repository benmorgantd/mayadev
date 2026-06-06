# Module: selectionUtils

### Pipeline Intent
Provides utility functions for working with selections in Maya. These functions are used by various components to perform common tasks that involve selections, such as getting the selected joints, etc.

### Technical Implementation
Imports `maya.cmds` module and defines a single function `getSelection` that returns the selected items based on the specified type. If no type is provided, it returns all selected items.

### Overview
This module provides a set of utility functions for working with selections in Maya, allowing components to perform common tasks such as getting selected joints or transforms.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** maya.cmds

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `getSelection`
**Signature:**
```python
def getSelection(ofType=None) -> list:
```
#### Arguments
- ofType (str): Optional type filter. If provided, returns only selected items of the specified type.

#### Returns
- list: A list of selected items. If ofType is not None, returns a list of items of the specified type.

---

### 🏷️ `VARIABLE` :: `sl1`
- **Type:** str
- **Value/Purpose:** The first item in the selection.

---

### 🏷️ `VARIABLE` :: `selected`
- **Type:** list
- **Value/Purpose:** A list of all selected items.

---

### 🏷️ `VARIABLE` :: `selectedJoints`
- **Type:** list
- **Value/Purpose:** A list of selected joints.

---

### 🏷️ `VARIABLE` :: `selectedTransforms`
- **Type:** list
- **Value/Purpose:** A list of selected transforms.