# Reference Component: `bmaya.maya.util.mathUtils`

## Module Level Context
Purpose:
Utility functions for working with math in maya. These are used by various components to perform common
tasks that involve math, such as finding the pole vector position for an ik handle, etc.

---
## Object Taxonomy Reference

### 🛠️ `find_pole_vector(joints, scaleFactor=1)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `fit_curve_to_points(points, name='fitCurve')`

```text
[cmds.xform(jnt, q=1, t=1, ws=1) for jnt in joints]
```

### 🛠️ `get_local_matrix(transform)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `get_matrix(transform, worldSpace=True)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `get_matrix_along_curve(curve, parameter, downAxis='X')`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `get_mmatrix_from_list(matrixList)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `get_world_matrix(transform)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `list_from_matrix(matrix)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `match_transforms(source, targets, translate=True, rotate=True, scale=True)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `reorder_matrix(matrix, downAxis=0, upAxis=0)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `setup_ik_twist(twist_joint=None, ik_start_joint=None, ik_handle_parent=None, twist_joint_parent=None, name=None)`

```text
start_joint (str): Required for the scik method. This joint will be the base of or single chain IK system.
ikParent (str): Required for the scik method. The resulting IK handle will eventually be the child of this joint.
* It's recommended that you don't use a "bind" joint for this. Try to keep your bind hierarchy clean :)

twistJointParent (str): Required for the scik method. The parent joint of the base of the IK chain.

mathUtils.setupIkTwist(twistJoint='leg_00_L_JNT', start_joint='leg_01_L_JNT', ikParent='pelvis_00_M_JNT', twistJointParent='leg_00_L_JNT', name='legTwist_L'
```

### 🛠️ `setup_quat_twist(obj=None, twistAxis='X')`

```text
No functional arguments or usage blocks specified.
```
