Here is the generated Markdown documentation:

# Module: weights
### Pipeline Intent
The Weights component is a folder that contains the skin weight files for a rig. These live in .weights files in the rig/components/weights folder and are saved and loaded using the weightio module, which handles the actual logic for saving and loading weight data.

### Technical Implementation
This module defines the `Weights` class, which inherits from the `Component` class. It uses the `os` library to interact with the file system and the `weightio` module to load and save skin weight files.

### Overview
The Weights component provides a folder structure for storing skin weight files related to a rig. It allows users to load and save these files using the `weightio` module, which handles the actual logic for saving and loading weight data.

### Cross-Module Dependencies
* **Internal Framework Links:** `Component`, `weightio`
* **External Dependencies:** None

## API Taxonomy Reference

### CLASS :: Weights
**Purpose:** The Weights component is a folder that contains the skin weight files for a rig.
**Inherits from:** `Component`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Weights component with an asset and component type.
- `@property relative_path(self)`: Returns the relative path of the Weights component.
- `@property files(self)`: Returns a list of files in the Weights component's directory.
- `load(self)`: Loads skin weight files from the Weights component's directory using the `weightio` module.
- `save(self)`: Saves skin weight files to the Weights component's directory using the `weightio` module.

---

I hope this meets your requirements! Let me know if you need any further modifications.