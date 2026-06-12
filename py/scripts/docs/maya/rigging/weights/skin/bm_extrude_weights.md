# Reference Component: `bmaya.maya.rigging.weights.skin.bm_extrude_weights`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference (Dynamic Introspection)

### ⚙️ Global Constants & Configurations

| Constant Name | Live Runtime Value | Type / Category |
| :--- | :--- | :--- |
| `kPluginCmdName` | `'extrudeWeights'` | Runtime Extracted Value |

---
### 🏷️ `CLASS` :: **ExtrudeWeights**

**Description Summary:**
No class descriptions detailed.

#### Methods & Interceptors

#### 🛠️ `__init__(self)`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `doIt(self, args)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `extrude_weights(self)`

```text
Copies the weights for each selected vertex to the vertex closest in
its inverse normal direction.

Great for quickly fixing intersections on an thick mesh.
```


#### 🛠️ `find_skin_cluster(self, dag)`

```text
A convenience function for finding the skinCluster deforming a mesh.

params:
  dag (MDagPath): A MDagPath for the mesh we want to investigate.
```


#### 🛠️ `isUndoable(self)`

```text
To make this command undoable, we need to override this function to return True
```


#### 🛠️ `redoIt(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `undoIt(self)`

```text
No functional arguments or usage blocks specified.
```



---
### 🛠️ `cmdCreator()`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `initializePlugin(mObject)`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `uninitializePlugin(mObject)`

```text
No functional arguments or usage blocks specified.
```
