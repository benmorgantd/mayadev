# Reference Component: `bmaya.maya.rigging.base.rig`

## Module Level Context
Purpose:
The Rig class is the main class for building a rig. It contains the main logic for building the rig,
as well as the main attributes that are used by the modules to build the rig, such as the list of modules,
the build data, etc. It also contains methods for building the layout rig, skinning the rig,
coloring controls, etc.
The Rig class is responsible for orchestrating the entire rigging process,
and is the main class that is instantiated when building a rig.

---
## Object Taxonomy Reference (Dynamic Introspection)

### 🏷️ `CLASS` :: **Rig**

**Description Summary:**
Rig is the base class for all rigs

How to build a rig:

from bmaya.maya.asset.asset import Asset
from bmaya.maya.rigging.base.rig import Rig

myAsset = Asset('dev|prop|cube')
myRig = Rig(myAsset.asset_id)
myRig.buildRig()
myAsset.openFile(myAsset.componentPathFromType('animRig'))

#### Methods & Interceptors

#### 🛠️ `__init__(self, asset_id, has_face=True)`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `add_module(self, module_dict)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `add_node_attrs(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `build_layout(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `build_rig(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `color_controls(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `component_path_from_type(self, component_type)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `connect_to_character(self, node)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `hideKeyableAttr(self, obj)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `init_component_files(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `init_component_folders(self)`

```text
Creates the component folders for the asset
```


#### 🛠️ `init_components(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `load_plugins(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `lockMeshes(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `lock_down_constraints(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `make_bind_set(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `make_node(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `run_post_ops(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `setup_mesh_referencing(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `skin(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `version_asset(self)`

```text
Versions the entire asset to a folder
```



---