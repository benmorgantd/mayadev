Here is the documentation for the `qtbase` module:

# Module: qtbase

### Pipeline Intent
Provides foundation classes and utilities for building Qt-based UI components within Maya. This module encapsulates basic widgets, layouts, and utility functions for customizing and extending the Qt framework in a Maya context.

### Technical Implementation
Imports necessary Qt modules (`QtWidgets`, `QtGui`, `QtCore`) and uses them to create custom widgets, layouts, and utilities that can be used to build Maya-specific UI components. Implements several basic widgets (e.g., `SimpleWindow`, `SimpleWidget`, `Table`, `List`, `Tree`), each with its own unique features and behaviors.

### Overview
The `qtbase` module is designed to provide a solid foundation for building custom Qt-based UI components within Maya. It offers a range of pre-built widgets, layouts, and utilities that can be used to create customized UIs tailored to specific needs and workflows.

### Cross-Module Dependencies

* **Internal Framework Links:** None
* **External Dependencies:** `maya.cmds`, `OpenMayaUI`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `SimpleWindow`
**Purpose:** Base class for simple Maya windows with title and layout capabilities.
*Inherits from:* `QtWidgets.QMainWindow`

#### Methods
- `__init__(self, parent=None, designerFile=None, title='Simple Widget')`: Initializes the window object.

---

### 🏷️ `CLASS` :: `Table`
**Purpose:** Custom Qt table widget with basic data handling and formatting capabilities.
*Inherits from:* `QtWidgets.QTableWidget`

#### Methods
- `translateToType(self, item)`: Converts an item's value to a specific type (e.g., string, int).
- `toJson(self, dictionary)`: Serializes a dictionary of key-value pairs into a JSON-formatted string.

---

### 🏷️ `CLASS` :: `DockableWidget`
**Purpose:** Custom Qt widget that can be docked within Maya's workspace.
*Inherits from:* `SimpleWidget`

#### Methods
- `dock(self, width=385, height=735)`: Dock the widget in Maya's workspace with specified dimensions.

---

### 🏷️ `CLASS` :: `Dialog`
**Purpose:** Base class for custom Qt dialog windows with basic layout and formatting capabilities.
*Inherits from:* `QtWidgets.QMainWindow`

#### Methods
- `__init__(self, parent=None, windowTitle='Dialog')`: Initializes the dialog object.

---

### 🏷️ `CLASS` :: `ConfirmDialog`
**Purpose:** Custom Qt confirm dialog window with Yes/No button options.
*Inherits from:* `Dialog`

#### Methods
- None

---

### 🏷️ `CLASS` :: `ProgressWindow`
**Purpose:** Custom Qt progress window with basic status and progress bar capabilities.
*Inherits from:* `SimpleWindow`

#### Methods
- `increment(self, value)`: Updates the progress bar's value by a specified amount.
- `setStatus(self, text)`: Sets the status text label within the progress window.

---

### Documentation Drift

No documentation drift detected.