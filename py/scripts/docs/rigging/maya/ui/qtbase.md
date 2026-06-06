# Module: qtbase

### Pipeline Intent
Provides a foundation for building Qt-based UI components within Maya. This module serves as a starting point for creating customizable and reusable GUI elements.

### Technical Implementation
Imports relevant modules from the `bmaya` library, such as `Qt`, to facilitate interaction with Qt-based widgets. The module also utilizes Maya's `maya.cmds` and `OpenMayaUI` libraries to integrate Maya-specific functionality into the UI components.

### Overview
This module provides a collection of basic UI components, including windows, widgets, tables, lists, trees, dockable widgets, dialogs, and progress windows. These components can be used as building blocks for creating custom UIs within Maya.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.lib.Qt`, `maya.cmds`, `OpenMayaUI`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `SimpleWindow`
**Purpose:** A basic window class for creating custom UI components.

#### Methods
- `__init__(self, parent=None, designerFile=None, title='Simple Widget')`: Initializes the window with optional parent widget, designer file, and title.
- `setWindowTitle(self, title)`: Sets the window's title.
- `setAttribute(self, attribute, value)`: Sets a Qt attribute for the window.

---

### 🏷️ `CLASS` :: `SimpleWidget`
**Purpose:** A basic widget class for creating custom UI components.

#### Methods
- `__init__(self, parent=None, designerFile=None, title='Simple Widget')`: Initializes the widget with optional parent widget, designer file, and title.
- `setWindowTitle(self, title)`: Sets the widget's title.
- `setAttribute(self, attribute, value)`: Sets a Qt attribute for the widget.

---

### 🏷️ `CLASS` :: `Table`
**Purpose:** A basic table class for displaying tabular data.

#### Methods
- `__init__(self)`: Initializes the table with default settings.
- `setShowGrid(self, flag)`: Toggles the display of grid lines in the table.
- `toJson(self, dictionary)`: Converts a dictionary into a JSON-formatted string.

---

### 🏷️ `CLASS` :: `List`
**Purpose:** A basic list class for displaying list-based data.

#### Methods
- `__init__(self, parent=None)`: Initializes the list with optional parent widget.
- `setAlternatingRowColors(self, flag)`: Toggles alternating row colors in the list.

---

### 🏷️ `CLASS` :: `Tree`
**Purpose:** A basic tree class for displaying hierarchical data.

#### Methods
- `__init__(self, parent=None)`: Initializes the tree with optional parent widget.
- `setAlternatingRowColors(self, flag)`: Toggles alternating row colors in the tree.
- `items(self)`: Returns a list of top-level items in the tree.
- `topLevelItems(self)`: Returns a list of top-level items in the tree.

---

### 🏷️ `CLASS` :: `TreeItem`
**Purpose:** A basic tree item class for representing individual nodes in the tree.

#### Methods
- `__init__(self, parent=None)`: Initializes the tree item with optional parent widget.
- `parents(self)`: Returns a list of parents for the tree item.
- `children(self)`: Returns a list of children for the tree item.
- `name(self)`: Returns the name of the tree item.

---

### 🏷️ `CLASS` :: `DockableWidget`
**Purpose:** A basic dockable widget class for creating custom UI components that can be docked within Maya's workspace.

#### Methods
- `__init__(self, parent=None, designerFile=None, title='rigManager')`: Initializes the dockable widget with optional parent widget, designer file, and title.
- `dock(self, width=385, height=735)`: Docks the widget within Maya's workspace.

---

### 🏷️ `CLASS` :: `Dialog`
**Purpose:** A basic dialog class for creating custom UI components that can be used as modal windows.

#### Methods
- `__init__(self, parent=None, windowTitle='Dialog')`: Initializes the dialog with optional parent widget and title.
- `setWindowFlags(self, flags)`: Sets various flags for the dialog window.

---

### 🏷️ `CLASS` :: `ConfirmDialog`
**Purpose:** A basic confirm dialog class for creating custom UI components that can be used to prompt users for confirmation.

#### Methods
- `__init__(self, parent=None, windowTitle='Confirm Dialog')`: Initializes the confirm dialog with optional parent widget and title.
- `setMinimumWidth(self, width)`: Sets the minimum width of the confirm dialog.
- `setMinimumHeight(self, height)`: Sets the minimum height of the confirm dialog.

---

### 🏷️ `CLASS` :: `ProgressWindow`
**Purpose:** A basic progress window class for creating custom UI components that can be used to display progress indicators.

#### Methods
- `__init__(self, parent=None, designerFile=None, title='Simple Widget')`: Initializes the progress window with optional parent widget, designer file, and title.
- `increment(self, value)`: Increments the progress bar by a given value.
- `setStatus(self, text)`: Sets the status text for the progress window.

---

### Documentation Drift
None detected.