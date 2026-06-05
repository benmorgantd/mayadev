Here is the documented code:

# Module: customWidgets

### Pipeline Intent
Provides custom widgets for rigManager to facilitate interaction with character rigs.

### Technical Implementation
Combines Qt classes from `Qt`, `QtGui`, and `QtCore` modules with Maya-specific libraries like `maya.cmds`. Utilizes Qt's tree widget and list views to create a hierarchical structure for managing build data. Implements custom widgets, such as `CustomLineEdit` and `AttributeLayoutValue`, to handle attribute editing.

### Overview
The `customWidgets` module offers a set of reusable UI components designed for use within the rigManager pipeline. These widgets enable users to manage character rigs by creating, renaming, deleting, duplicating, and disabling build items. The module relies on Maya's `maya.cmds` library to interact with Maya's scene management.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya3.lib.Qt`, `bmaya3.core.qtbase`, `shapelib`
* **External Dependencies:** `maya.cmds`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `ModuleList`
**Purpose:** A custom list widget for displaying build data.

*Inherits from:* `qtbase.List`

#### Methods
- `mouseDoubleClickEvent(self, event)`: Handles double-click events on list items.
- `setBuildList(self, listWidget)`: Sets the build list associated with this module list.
- `mousePressEvent(self, event)`: Checks if the event is a right-click and shows the context menu accordingly.

### 🏷️ `CLASS` :: `BuildList`
**Purpose:** A custom tree widget for managing build data.

*Inherits from:* `qtbase.Tree`

#### Methods
- `loadList(self, buildData, attributeLayoutContainer)`: Loads build data into this tree widget.
- `getAllValues(self)`: Retrieves the attribute values of all build items in this tree widget.
- `hideAttrLayouts(self)`: Hides attribute layouts for all build items in this tree widget.
- `renameItem(self)`: Renames the currently selected build item.
- `disableItem(self)`: Disables the currently selected build item.
- `deleteItem(self)`: Deletes the currently selected build item.
- `duplicateItem(self)`: Duplicates the currently selected build item.

### 🏷️ `CLASS` :: `BuildListItem`
**Purpose:** A custom tree item for representing a build item in the `BuildList` widget.

*Inherits from:* `qtbase.TreeItem`

#### Methods
- `loadAttributeTemplates(self)`: Loads attribute templates based on this build item's type.
- `values(self)`: Retrieves the attribute values of this build item.

### 🏷️ `CLASS` :: `AttributeLayout`
**Purpose:** A custom widget for displaying and editing attribute values.

*Inherits from:* `QtWidgets.QWidget`

#### Methods
- `build(self)`: Builds the attribute layout for this widget.
- `toJson(self)`: Converts this attribute value to a JSON string.

### 🏷️ `FUNCTION` :: `AttributeLayoutValue`
**Purpose:** A custom class for representing an attribute value in the `AttributeLayout` widget.

#### Methods
- `build(self)`: Builds the attribute layout item based on its type.
- `translateToType(self, item)`: Translates this attribute value to the specified type.
- `toJson(self)`: Converts this attribute value to a JSON string.

### 🏷️ `FUNCTION` :: `CustomLineEdit`
**Purpose:** A custom line edit widget for editing attribute values.

#### Methods
- `mousePressEvent(self, event)`: Handles mouse press events and shows the context menu.
- `replaceWithSelection(self)`: Replaces this line edit's text with the selected items in Maya.
- `resetToDefault(self)`: Resets this line edit's text to its default value.

### 🏷️ `FUNCTION` :: `LineEditMenu`
**Purpose:** A custom context menu for the `CustomLineEdit` widget.

#### Methods
- `addAction(self, action)`: Adds an action to this menu.
- `hide(self)`: Hides this menu.