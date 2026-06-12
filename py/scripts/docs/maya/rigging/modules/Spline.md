# Reference Component: `bmaya.maya.rigging.modules.Spline`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference (Dynamic Introspection)

### 🏷️ `CLASS` :: **Spline**

**Description Summary:**
No class descriptions detailed.

#### Methods & Interceptors

#### 🛠️ `__init__(self, start_joint=None, end_joint=None, name='Spline1', character=None, side='M', mirror=False, parent=None, setupTwist=True, controlAmount=3, stretchy=True, startTwistParent=None, shapeType='cube')`

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


#### 🛠️ `buildIkControls(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `buildIkSpline(self)`

```text
Note that there will be some movement on the ikJoints after creating this.
Having the blend maintain offset will help.
```


#### 🛠️ `buildSplineDriverJoints(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `build_fk_controls(self)`

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


#### 🛠️ `setupAdvancedTwist(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `setupIkEndJoint(self)`

```text
Create a joint at the end of the ik chain that serves as more of an fk-style control
```


#### 🛠️ `setupIkHierarchy(self)`

```text
Make a simple switch to make the ik hierarchy behave like an fk one
```


#### 🛠️ `setupStretch(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `setup_align_world(self, component, default_value=0)`

```text
No functional arguments or usage blocks specified.
```



---