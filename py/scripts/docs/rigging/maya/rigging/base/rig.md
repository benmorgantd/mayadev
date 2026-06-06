# Module: rig

### Pipeline Intent
Provides the base class for building a rig. This class orchestrates the entire rigging process and is responsible for creating and managing all components of the character rig.

### Technical Implementation
The Rig class inherits from Asset and provides methods for building and managing the various modules that make up the rig. It contains properties for mesh shapes, controls, and influences, as well as methods for adding modules, building layouts, skinning, and coloring controls.

### Overview
The Rig class is the main entry point for building a character rig in Maya. It provides a framework for creating and managing all components of the rig, including meshes, skeletons, weights, CVS, build files, and post-operations scripts.

### Cross-Module Dependencies
* **Internal Framework Links:** 
	+ `bmaya.maya.asset.asset`: The base class for asset management.
	+ `bmaya.maya.asset.components.*`: Various component classes for building the rig (e.g., mesh, skeleton, weights).
	+ `bmaya.core.constants`: A set of constants used throughout the pipeline.
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Rig`
**Purpose:** The main class for building a character rig.

#### Methods
- `__init__(self, assetId)`: Initializes the Rig instance with an asset ID.
- `addModule(self, moduleDict)`: Adds a new module to the rig.
- `buildLayout(self)`: Builds the layout of the rig.
- `buildRig(self)`: Builds the entire character rig.
- `connectToCharacter(self, node)`: Connects the rig to a character node.
- `hideKeyableAttr(self, obj)`: Hides keyable attributes for an object.
- `initComponents(self)`: Initializes the component objects for the asset.
- `initComponentFolders(self)`: Creates the component folders for the asset.
- `initComponentFiles(self)`: Initializes the component files for the asset.
- `lockDownConstraints(self)`: Manages constraints in the rig.
- `makeBindSet(self)`: Creates a bind set for the rig.
- `makeNode(self)`: Creates a new character node.
- `node` :: `str`: The name of the character node.
- `referenceMesh` :: `bool`: A property indicating whether to reference meshes.

#### Properties
- `controls` :: `list[str]`: A list of control objects in the rig.
- `influences` :: `list[str]`: A list of influence objects in the rig.
- `meshShapes` :: `list[str]`: A list of mesh shape objects in the rig.

Note: The "Documentation Drift" section is empty for this file, as there are no inconsistencies between the docstrings and the actual code.