# Reference Component: `bmaya.maya.asset.asset`

## Module Level Context
Purpose:
Base class for production Assets that handles logic for asset Id, file management, and versioning.
Assets are made up of components, which are the individual files that make up the asset.
For example, a character asset may have components for model, rig, textures, weights, etc.

Assets are identified by an Id, which is a string in the format: project|type|nameUtils.

The project is the name of the project the asset belongs to, the type is the type of asset (e.g. character, prop, environment),
and the name is the name of the asset itself. The asset class also has methods for opening the asset in the file explorer,
opening the asset file in Maya, referencing the asset file in Maya, checking if an asset exists,
finding files of a certain type within the asset's directory, and versioning the asset.

---
## Object Taxonomy Reference (Dynamic Introspection)

### 🏷️ `CLASS` :: **Asset**

**Description Summary:**
No class descriptions detailed.

#### Methods & Interceptors

#### 🛠️ `__init__(self, asset_id)`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `component_path_from_type(self, component_type)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `version_asset(self)`

```text
Versions the entire asset to a folder
```



---