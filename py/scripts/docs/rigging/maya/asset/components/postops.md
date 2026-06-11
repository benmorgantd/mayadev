Here is the documentation for the `postops` module:

# Module: postops

### Pipeline Intent
The PostOps component is a python file that allows the user to run custom logic on a rig after it is built.

### Technical Implementation
This module inherits from the `Component` class and overrides the `__init__` method to set up the necessary asset and component type information. The `relative_path` property returns the path of the PostOps script based on the asset's type and extension.

### Overview
The PostOps component is a part of the rigging pipeline that allows for custom logic to be executed after a rig has been built. This module provides a way to access the relative path of the PostOps script, which can be used to locate the script in the file system.

### Cross-Module Dependencies
* **Internal Framework Links:** `Component` from `component.py`
* **External Dependencies:** None

## API Taxonomy Reference

### CLASS :: PostOps
**Purpose:** A Python class that represents a PostOps component, inheriting from the `Component` class.
*Inherits from:* `Component`

#### Methods
- `__init__(self, asset, component_type)`: Initializes the PostOps component with the given asset and component type.