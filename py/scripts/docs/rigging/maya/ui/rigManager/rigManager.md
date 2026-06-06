# Module: rigManager
### Pipeline Intent
Provides an interface for animators to manage and control character rigs, including building, loading, saving, and referencing components.

### Technical Implementation
Exposes a graphical user interface (GUI) using Qt libraries, allowing users to interact with the rig management system. Utilizes Maya's OpenMaya and cmds modules for low-level interaction.

### Overview
The Rig Manager is a centralized hub for managing character rigs in Maya. It enables animators to create, load, save, and reference different components of a character rig, such as arms, legs, and faces. The module also provides tools for building and versioning builds, allowing for efficient collaboration and tracking.

### Cross-Module Dependencies
* **Internal Framework Links:**
	+ `bmaya.maya.asset`: Used to interact with asset management.
	+ `bmaya.maya.rigging.buildio`: Utilized for build management and versioning.
	+ `bmaya.maya.rigging.modules`: Imported modules provide individual component rigging functionality.
* **External Dependencies:**
	+ Maya.cmds: Low-level interface for interacting with Maya's scene graph.
	+ OpenMaya: Provides a higher-level interface for working with Maya's scene graph.

## API Taxonomy Reference

### 🏷️ `CLASS` :: `RigManager`
**Purpose:** Centralized hub for managing character rigs in Maya.

*Inherits from:* `qtbase.DockableWidget`

#### Methods
- `__init__(self, parent=None, designerFile=None, title='Rig Manager')`: Initializes the Rig Manager with a parent widget and optional designer file.
- `setupUI(self)`: Sets up the user interface by creating and populating various widgets.
- `loadModules(self)`: Loads available rig modules for selection.
- `saveComponent(self)`: Saves a selected component to disk.
- `loadComponent(self)`: Loads a saved component into memory.
- `referenceComponent(self)`: References a loaded component in the scene.
- `buildCharacter(self)`: Builds and saves the character rig.

---

### 🏷️ `FUNCTION` :: `run`
**Signature:**
```python
def run() -> RigManager:
```
#### Description:** Creates an instance of the Rig Manager class, sets up the UI, and docks it to the Maya window.
#### Returns:** A reference to the created Rig Manager instance.

---

### 🏷️ `GLOBAL VARIABLE` :: `assetCreator`
- **Type:** Module
- **Value/Purpose:** Provides a GUI-based interface for creating new assets.