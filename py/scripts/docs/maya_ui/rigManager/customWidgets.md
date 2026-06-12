# Reference Component: `bmaya.maya_ui.rigManager.customWidgets`

## Module Level Context
Custom widgets for rigManager

---
## Object Taxonomy Reference (Dynamic Introspection)

### 🏷️ `CLASS` :: **AttributeLayout**

**Description Summary:**
QWidget(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, parent=None, attributes=None)`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None, f: PySide6.QtCore.Qt.WindowType = Default(Qt.WindowFlags)) -> None

Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `build(self)`

```text
No functional arguments or usage blocks specified.
```



---
### 🏷️ `CLASS` :: **AttributeLayoutValue**

**Description Summary:**
No class descriptions detailed.

#### Methods & Interceptors

#### 🛠️ `__init__(self, attribute, defaultValue)`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `build(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `toJson(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `translateToType(self, item)`

```text
No functional arguments or usage blocks specified.
```



---
### 🏷️ `CLASS` :: **BuildList**

**Description Summary:**
QTreeWidget(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self)`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `deleteItem(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `disableItem(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `duplicateItem(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `getAllValues(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `hideAttrLayouts(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `loadList(self, buildData, attributeLayoutContainer)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `mouseDoubleClickEvent(self, event)`

```text
mouseDoubleClickEvent(self, event: PySide6.QtGui.QMouseEvent) -> None
```


#### 🛠️ `mousePressEvent(self, event)`

```text
mousePressEvent(self, event: PySide6.QtGui.QMouseEvent) -> None
```


#### 🛠️ `renameItem(self)`

```text
No functional arguments or usage blocks specified.
```



---
### 🏷️ `CLASS` :: **BuildListContextMenu**

**Description Summary:**
QMenu(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None
QMenu(self, title: str, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, buildList)`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None
__init__(self, title: str, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🏷️ `CLASS` :: **BuildListItem**

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

#### 🛠️ `__init__(self, modType, customAttrs=None, attributeContainer=None, name=None)`

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


#### 🛠️ `loadAttributeTemplates(self)`

```text
No functional arguments or usage blocks specified.
```



---
### 🏷️ `CLASS` :: **CustomLineEdit**

**Description Summary:**
QLineEdit(self, arg__1: str, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None
QLineEdit(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, text, parent=None)`

```text
__init__(self, arg__1: str, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `mousePressEvent(self, event)`

```text
mousePressEvent(self, arg__1: PySide6.QtGui.QMouseEvent) -> None
```


#### 🛠️ `replaceWithSelection(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `resetToDefault(self)`

```text
No functional arguments or usage blocks specified.
```



---
### 🏷️ `CLASS` :: **LineEditMenu**

**Description Summary:**
QMenu(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None
QMenu(self, title: str, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, lineEdit)`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None
__init__(self, title: str, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

Initialize self.  See help(type(self)) for accurate signature.
```



---
### 🏷️ `CLASS` :: **ModuleList**

**Description Summary:**
QListWidget(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

#### Methods & Interceptors

#### 🛠️ `__init__(self, attributeContainer=None)`

```text
__init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None

Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `mouseDoubleClickEvent(self, event)`

```text
mouseDoubleClickEvent(self, event: PySide6.QtGui.QMouseEvent) -> None
```


#### 🛠️ `setBuildList(self, listWidget)`

```text
No functional arguments or usage blocks specified.
```



---