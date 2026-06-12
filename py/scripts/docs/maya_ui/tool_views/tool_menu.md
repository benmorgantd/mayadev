# Reference Component: `bmaya.maya_ui.tool_views.tool_menu`

## Module Level Context
Layout management interface for generating and configuring cascading Maya menus.

---
## Object Taxonomy Reference (Dynamic Introspection)

### 🏷️ `CLASS` :: **ToolMenu**

**Description Summary:**
Generates an editable, cascading Maya native window menu from a layout file.

#### Methods & Interceptors

#### 🛠️ `__init__(self, menu_id=None)`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `build_ui(self, registry)`

```text
Clears out existing artifacts and draws the menu on the global menu bar.
```


#### 🛠️ `load_layout(self, filepath)`

```text
Loads the view structural configuration file.
```



---
### 🏷️ `CLASS` :: **ToolMenuEditorWindow**

**Description Summary:**
UI controller for defining, organizing, and saving custom menu layouts.

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent: PySide6.QtWidgets.QWidget | None = None) -> None`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, flags: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🛠️ `show_menu_editor_ui() -> bmaya.maya_ui.tool_views.tool_menu.ToolMenuEditorWindow`

```text
Helper instantiation execution method entry pipeline standardizer.
```
