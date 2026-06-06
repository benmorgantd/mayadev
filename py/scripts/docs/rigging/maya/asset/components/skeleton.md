# Module: skeleton

### Pipeline Intent
Provides the logic for serializing and deserializing a joint hierarchy used to save and load the skeleton component of a rig.

### Technical Implementation
Utilizes Maya's OpenMaya API and commands to manipulate and query joints, as well as serialize and deserialize data structures.

### Overview
The Skeleton class is a MayaComponent that encapsulates the joint hierarchy for a rig. It contains methods for serializing and deserializing this hierarchy, which is used to save and load the skeleton component of a rig.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.mayaComponent`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Skeleton`
**Purpose:** A MayaComponent that contains the joint hierarchy for a rig.
**Inherits from:** `MayaComponent`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Skeleton with an asset and component type.

---

### 🏷️ `FUNCTION` :: `serializeJointHierarchy`
**Signature:**
```python
@classmethod
def serializeJointHierarchy(cls, rootJoint):
```
**Purpose:** Serializes a joint hierarchy starting from the given root joint.
#### Arguments
- `rootJoint`: The root joint to start serialization from.

#### Returns
- A list of dictionaries containing serialized joint data.

---

### 🏷️ `FUNCTION` :: `deserializeJointHierarchy`
**Signature:**
```python
@classmethod
def deserializeJointHierarchy(cls, data):
```
**Purpose:** Deserializes a joint hierarchy from the given data.
#### Arguments
- `data`: A list of dictionaries containing serialized joint data.

#### Returns
- None

---

### 🏷️ `GLOBAL VARIABLE` :: `relativePath`
- **Type:** str
- **Value/Purpose:** The path to the skeleton component file in the rig directory, relative to the asset.