Here is the Markdown documentation for this file:

# Module: `customWidgets`

### Pipeline Intent
Provides a set of custom widgets for rigManager, allowing users to interact with build data and attributes.

### Technical Implementation
The module imports various Qt modules, including `Qt`, `QtWidgets`, `QtGui`, and `QtCore`. It also imports `qtbase` from the `bmaya.core` package, as well as `shapelib` from the `bmaya.maya.rigging.shapes` package. The module defines several classes: `ModuleList`, `BuildList`, `BuildListItem`, `AttributeLayoutValue`, and `AttributeLayout`. These classes provide custom widgets for displaying and interacting with build data and attributes.

### Overview
The `customWidgets` module is designed to work with the rigManager pipeline, providing a set of custom widgets for users to interact with build data and attributes. The modules define several key classes: `ModuleList`, which provides a list view of modules; `BuildList`, which provides a tree view of build items; `BuildListItem`, which represents an individual build item; `AttributeLayoutValue`, which defines the layout for displaying attribute values; and `AttributeLayout`, which manages the display of attributes.

### Cross-Module Dependencies
* Internal Framework Links: `bmaya.core`, `bmaya.maya.rigging.shapes`
* External Dependencies: None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `ModuleList`
**Purpose:** Provides a list view of modules.
*Inherits from:* `qtbase.List`

#### Methods
- `setBuildList(self, listWidget)`: Sets the build list widget.
- `mouseDoubleClickEvent(self, event)`: Handles mouse double-click events.

---

### 🏷️ `CLASS` :: `BuildList`
**Purpose:** Provides a tree view of build items.
*Inherits from:* `qtbase.Tree`

#### Methods
- `loadList(self, buildData, attributeLayoutContainer)`: Loads the build list with data.
- `getAllValues(self)`: Gets all values for the build list.
- `hideAttrLayouts(self)`: Hides attribute layouts.
- `renameItem(self)`: Renames an item in the build list.
- `disableItem(self)`: Disables an item in the build list.
- `deleteItem(self)`: Deletes an item in the build list.

---

### 🏷️ `CLASS` :: `BuildListItem`
**Purpose:** Represents an individual build item.
*Inherits from:* `qtbase.TreeItem`

#### Methods
- `loadAttributeTemplates(self)`: Loads attribute templates for the build item.
- `values(self)`: Gets the values for the build item.

---

### 🏷️ `CLASS` :: `AttributeLayoutValue`
**Purpose:** Defines the layout for displaying attribute values.
*Inherits from:* None

#### Methods
- `build(self)`: Builds the attribute value widget.
- `toJson(self)`: Converts the attribute value to JSON format.

---

### 🏷️ `CLASS` :: `AttributeLayout`
**Purpose:** Manages the display of attributes.
*Inherits from:* `QtWidgets.QWidget`

#### Methods
- `build(self)`: Builds the attribute layout.
- `addAttr(attribute, value, row)`: Adds an attribute to the layout.

---

### 🏷️ `FUNCTION` :: `CustomLineEdit`
**Signature:**
```python
def __init__(self, text, parent=None):
```
#### Arguments
- `text`: The initial text for the line edit.
- `parent`: The parent widget (optional).

#### Returns
None

---

### 🏷️ `CLASS` :: `LineEditMenu`
**Purpose:** Provides a menu for custom line edits.
*Inherits from:* `QtWidgets.QMenu`

#### Methods
- `replaceWithSelection(self)`: Replaces the text with the selection.
- `resetToDefault(self)`: Resets the text to its default value.

---

### Documentation Drift

None found.