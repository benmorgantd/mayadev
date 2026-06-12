# Reference Component: `bmaya.maya.rigging.base.module`

## Module Level Context
Purpose:
The Module class is the base class for all rig modules. It contains the basic attributes and methods that
all modules will need, such as building the module, creating the module node, adding attributes to the node,
finding mirror nodes, etc. Each specific module (such as Arm, Leg, Spine, etc.) will inherit from this class
and implement its own build method to create the specific rig for that module.
The module also contains some class methods that are used by various modules, such as adding a moveable pivot to a control, etc.

---
## Object Taxonomy Reference

### 🏷️ `CLASS` :: **Module**

**Description Summary:**
No class descriptions detailed.

#### Methods & Interceptors

#### 🛠️ `__init__(self, character=None, name='module1', mod_type='Module', parent=None, side='L', mirror=False, shape_type='cube', align_world=None)`

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


#### 🛠️ `build(self)`

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