# Reference Component: `bmaya.maya.rigging.modules.Face`

## Module Level Context
Facial rig setup

---
## Object Taxonomy Reference (Dynamic Introspection)

### 🏷️ `CLASS` :: **Face**

**Description Summary:**
No class descriptions detailed.

#### Methods & Interceptors

#### 🛠️ `__init__(self, character=None, name='face', parent=None, upperHead=None, middleHead=None, lowerHead=None, jaw=None, eyeballs=[], eyelidBase=None, eyebrowBase=None, drivers=[])`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `add_node_attrs(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `blend_chains(self, fk_chain, ik_chain, child_chain, drive_attribute)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `build(self, *args, **kwargs)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `buildFaceFkHierarchy(self, start_joint, exclude=[])`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `build_fk_controls(self, drive_joints, setup_align_world=False)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `capture_component_defaults(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `check_contract(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `connect_bind_joints(self)`

```text
Connects the module's bind joints to their control
```


#### 🛠️ `connect_components(self)`

```text
Connects the module's compenents to the module
```


#### 🛠️ `create_drive_joint(self, jnt, label='Driver', constrain=True)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `create_drive_joints(self, label='DRIVER', constrain=True)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `determine_parent(self, parent)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `do_mirror(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `find_hierarchy_joints(self, shortest_distance=False, start_joint=None, end_joint=None, exclude=[])`

```text
Expands from a start joint and until it hits excluded joints.
```


#### 🛠️ `find_joint_name(self, node, identifier=None, count=0, suffix='DRIVER')`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `find_mirror(self, node)`

```text
Returns the mirrored node of the same type if it's in the scene.
Else returns None
```


#### 🛠️ `find_twist_joints(self, jnt)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `get_driver(self, joint)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `make_ik_handle(self, start_joint, end_joint, solver_type, name)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `make_node(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `message_connect(self, node_a, node_b, longName_a, longName_b)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `parent_constrain(self, parent=None, child=None, maintain_offset=True)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `parent_module(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `parse_for_maya_attr(self, attr)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `setup_align_world(self, component, default_value=0)`

```text
No functional arguments or usage blocks specified.
```



---