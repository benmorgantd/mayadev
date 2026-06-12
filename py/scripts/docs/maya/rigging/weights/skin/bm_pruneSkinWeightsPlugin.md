# Reference Component: `bmaya.maya.rigging.weights.skin.bm_pruneSkinWeightsPlugin`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference (Dynamic Introspection)

### ⚙️ Global Constants & Configurations

| Constant Name | Live Runtime Value | Type / Category |
| :--- | :--- | :--- |
| `kPluginCmdName` | `'pruneWeights'` | Runtime Extracted Value |

---
### 🏷️ `CLASS` :: **PruneWeights**

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


#### 🛠️ `getSkinCluster(self, dag)`

```text
A convenience function for finding the skinCluster deforming a mesh.

params:
  dag (MDagPath): A MDagPath for the mesh we want to investigate.
```


#### 🛠️ `isUndoable(self)`

```text
To make this command undoable, we need to override this function to return True
```


#### 🛠️ `pruneSkinWeights(self, maxInfluence=4)`

```text
Sets the weights for each vertex to the average of its neighbors.
```


#### 🛠️ `pruneWeightList(self, weights, maxInfluence=4)`

```text
Prunes the given list to have only four non-zero values
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
