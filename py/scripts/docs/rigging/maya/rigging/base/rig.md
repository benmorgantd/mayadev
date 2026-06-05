# Module: rig

### Pipeline Intent
Provides the foundation for building a character rig in Maya. This module orchestrates the entire rigging process, including loading plugins, creating nodes, skinning meshes, and managing constraints.

### Technical Implementation
Exposes various methods for building and customizing a character rig, such as adding modules, building layout rigs, skinning meshes, and managing weights. Utilizes Python's built-in `json` module to read and write JSON files.

### Overview
The Rig class is responsible for building a character rig in Maya. It contains methods for loading plugins, creating nodes, skinning meshes, and managing constraints.

### Cross-Module Dependencies

* **Internal Framework Links:**
	+ `bmaya.maya.asset.asset`: Inherits from the Asset class.
	+ `bmaya.maya.asset.components`: Imports various component classes (e.g., Mesh, Skeleton, Weights).
	+ `bmaya.maya.rigging.shapes`: Imports shape-related modules (e.g., shapelib, shapeio).
	+ `bmaya.maya.rigging.weights`: Imports weight-related modules (e.g., weightio, skinCluster).
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Rig`
**Purpose:** The main class for building a character rig in Maya.

#### Methods
- `__init__(self, assetId, hasFace=True)`: Initializes the Rig class with an asset ID and optional face flag.
- `addModule(self, moduleDict)`: Adds a module to the rig's list of modules.
- `buildLayout(self)`: Builds the layout rig for the character.
- `buildRig(self)`: Builds the entire character rig, including skinning meshes, managing constraints, and creating nodes.

---

### 🏷️ `FUNCTION` :: `makeNode`
**Signature:**
```python
def makeNode(self):
```
#### Description:** Creates a new node for the character rig.

### 🏷️ `FUNCTION` :: `addNodeAttrs`
**Signature:**
```python
def addNodeAttrs(self):
```
#### Description:** Adds attributes to the character node, such as the rig's name and components.

### 🏷️ `FUNCTION` :: `skin`
**Signature:**
```python
def skin(self):
```
#### Description:** Skins meshes to a skeleton set or uses existing weights files.

---

### 🏷️ `GLOBAL VARIABLE` :: `Rig`
- **Type:** Class
- **Value/Purpose:** The main class for building a character rig in Maya.