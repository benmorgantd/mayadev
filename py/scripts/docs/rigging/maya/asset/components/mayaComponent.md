# Module: MayaComponent

### Pipeline Intent
Provides production file path verification and localized directory scaffolding for animators saving character rig performance files. Designed to enforce the studio's directory structure across OS environments.

### Technical Implementation
Exposes automated versioning utilities using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Overview
A MayaComponent is a type of Component that is specific to Maya. It contains the file handling logic for components that are Maya files.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.core.util.fileUtils`, `bmaya.maya.asset.component`
* **External Dependencies:** `maya.cmds`, `OpenMaya`

## API Taxonomy Reference

### 🏷️ `CLASS` :: `MayaComponent`
**Purpose:** A Maya-specific component that handles file operations.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the MayaComponent with an asset and a component type.
- `save(self)`: Saves the Maya component to disk using the specified file path.
	* **Arguments:**
	+ None
	* **Returns:** None

    - `load(self)`: Loads the Maya component from disk using the specified file path.
	* **Arguments:**
	+ None
	* **Returns:** None

    - `reference(self)`: References the Maya component in Maya, setting up a reference to the file.
	* **Arguments:**
	+ None
	* **Returns:** None