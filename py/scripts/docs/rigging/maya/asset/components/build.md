# Module: build

### Pipeline Intent
Class for the Build component, which is a json file that contains the rig structure.

### Technical Implementation
This module defines a `Build` class that inherits from `Component`. It uses the `os` module to construct the relative path of the build component based on its type and extension.

### Overview
The `Build` class is used to represent a JSON file containing the rig structure for an animation. It provides a way to access the relative path of the build component, which can be used to determine where the file should be saved or loaded.

### Cross-Module Dependencies
* **Internal Framework Links:** `component.py`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Build`

**Purpose:** Class for the Build component, which is a json file that contains the rig structure.

**Inherits from:** `Component`

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Build component with an asset and component type.
- `@property relative_path(self)`: Returns the relative path of the build component based on its type and extension.

---

Note: This documentation is generated using the provided local symbol metadata.