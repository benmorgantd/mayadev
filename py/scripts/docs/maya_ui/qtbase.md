# Reference Component: `bmaya.maya_ui.qtbase`

## Module Level Context
Base classes for qt widgets compatible with Python 3 and PySide6

---
## Object Taxonomy Reference (Dynamic Introspection)

### 🏷️ `CLASS` :: **ConfirmDialog**

**Description Summary:**
Modal confirm dialog that pauses execution and returns a boolean result.

#### Methods & Interceptors

#### 🛠️ `__init__(self, message, parent=None, windowTitle='Confirm Dialog')`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🏷️ `CLASS` :: **Dialog**

**Description Summary:**
QDialog(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None, windowTitle='Dialog')`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🏷️ `CLASS` :: **DockableWidget**

**Description Summary:**
QWidget(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None, designerFile=None, title='rigManager')`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `dock(self, width=385, height=735)`

```text
No functional arguments or usage blocks specified.
```



---
### 🏷️ `CLASS` :: **List**

**Description Summary:**
QListWidget(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None)`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🏷️ `CLASS` :: **ProgressWindow**

**Description Summary:**
QMainWindow(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, flags: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None, designerFile=None, title='Progress Tracker')`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, flags: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `refresh_ui(self) -> None`

```text
Syncs the Qt widgets to the current state of the pure python singleton.
```



---
### 🏷️ `CLASS` :: **PythonSyntaxHighlighter**

**Description Summary:**
Provides fundamental Python syntax highlighting for the embedded script editor.

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent: PySide6.QtGui.QTextDocument | None = None) -> None`

```text
__init__(self, parent: PySide6.QtCore.QObject) -> None
__init__(self, parent: PySide6.QtGui.QTextDocument) -> None

Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `highlightBlock(self, text: str) -> None`

```text
Applies formatting rules across the text block contextually.
```



---
### 🏷️ `CLASS` :: **SimpleWidget**

**Description Summary:**
QWidget(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None, designerFile=None, title='Simple Widget')`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🏷️ `CLASS` :: **SimpleWindow**

**Description Summary:**
QMainWindow(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, flags: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None, designerFile=None, title='Simple Widget')`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, flags: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🏷️ `CLASS` :: **Table**

**Description Summary:**
QTableWidget(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None
QTableWidget(self, rows: int, columns: int, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self)`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None
__init__(self, rows: int, columns: int, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `toJson(self, dictionary)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `translateToType(self, item)`

```text
No functional arguments or usage blocks specified.
```



---
### 🏷️ `CLASS` :: **Tree**

**Description Summary:**
QTreeWidget(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None)`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🏷️ `CLASS` :: **TreeItem**

**Description Summary:**
QTreeWidgetItem(self, other: PySide6.QtWidgets.QTreeWidgetItem) -> None
QTreeWidgetItem(self, parent: PySide6.QtWidgets.QTreeWidgetItem, after: PySide6.QtWidgets.QTreeWidgetItem, type: int = <ItemType.Type: 0>) -> None
QTreeWidgetItem(self, parent: PySide6.QtWidgets.QTreeWidgetItem, strings: Sequence[str], type: int = <ItemType.Type: 0>) -> None
QTreeWidgetItem(self, parent: PySide6.QtWidgets.QTreeWidgetItem, type: int = <ItemType.Type: 0>) -> None
QTreeWidgetItem(self, strings: Sequence[str], type: int = <ItemType.Type: 0>) -> None
QTreeWidgetItem(self, treeview: PySide6.QtWidgets.QTreeWidget, after: PySide6.QtWidgets.QTreeWidgetItem, type: int = <ItemType.Type: 0>) -> None
QTreeWidgetItem(self, treeview: PySide6.QtWidgets.QTreeWidget, strings: Sequence[str], type: int = <ItemType.Type: 0>) -> None
QTreeWidgetItem(self, treeview: PySide6.QtWidgets.QTreeWidget, type: int = <ItemType.Type: 0>) -> None
QTreeWidgetItem(self, type: int = <ItemType.Type: 0>) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None)`

```text
__init__(self, other: PySide6.QtWidgets.QTreeWidgetItem) -> None
__init__(self, parent: PySide6.QtWidgets.QTreeWidgetItem, after: PySide6.QtWidgets.QTreeWidgetItem, type: int = <ItemType.Type: 0>) -> None
__init__(self, parent: PySide6.QtWidgets.QTreeWidgetItem, strings: Sequence[str], type: int = <ItemType.Type: 0>) -> None
__init__(self, parent: PySide6.QtWidgets.QTreeWidgetItem, type: int = <ItemType.Type: 0>) -> None
__init__(self, strings: Sequence[str], type: int = <ItemType.Type: 0>) -> None
__init__(self, treeview: PySide6.QtWidgets.QTreeWidget, after: PySide6.QtWidgets.QTreeWidgetItem, type: int = <ItemType.Type: 0>) -> None
__init__(self, treeview: PySide6.QtWidgets.QTreeWidget, strings: Sequence[str], type: int = <ItemType.Type: 0>) -> None
__init__(self, treeview: PySide6.QtWidgets.QTreeWidget, type: int = <ItemType.Type: 0>) -> None
__init__(self, type: int = <ItemType.Type: 0>) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🛠️ `get_maya_main_window()`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `loadUiFile(designerFile, parent=None)`

```text
Helper replacement for the old QtCompat.load_ui layout stream
```
