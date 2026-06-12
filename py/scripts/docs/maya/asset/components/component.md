# Reference Component: `bmaya.maya.asset.components.component`

## Module Level Context
Purpose:
Base class for production Components that handles logic for asset Id, file management, and versioning.
Components are the individual files that make up an asset.
Contains the type extensions for each component type, as well as the base class for all components.
Also handles the unimplemented logic for loading and saving and referencing, which must be defined by each specific component type.

---
## Object Taxonomy Reference (Dynamic Introspection)

### ⚙️ Global Constants & Configurations

| Constant Name | Live Runtime Value | Type / Category |
| :--- | :--- | :--- |
| `TYPE_EXTENSIONS` | `{'mesh': '.ma', 'skeleton': '.ma', 'cvs': '.json', 'animRig': '.ma', 'weights': '.json', 'build': '.json', 'component...` | Runtime Extracted Value |

---
### 🏷️ `CLASS` :: **Component**

**Description Summary:**
No class descriptions detailed.

#### Methods & Interceptors

#### 🛠️ `__init__(self, asset, component_type)`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `load(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `reference(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `save(self)`

```text
No functional arguments or usage blocks specified.
```



---