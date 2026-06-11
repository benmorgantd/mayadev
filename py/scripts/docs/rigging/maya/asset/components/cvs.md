Here is the generated Markdown documentation for the `cvs.py` module:

# Module: Cvs
### Pipeline Intent
The Cvs class is a component that is a json file containing the cv shape data for the controls on a rig. It contains the logic for loading and saving cvs using the shapeio module, which handles the actual logic for saving and loading cv data.

### Technical Implementation

The `Cvs` class inherits from the `Component` class and provides methods for initializing (`__init__`), determining its relative path, loading (`load`), and saving (`save`) CVS (control vertex) shape data.

#### Classes
##### Cvs
- **Inherits from:** `Component`
- **Methods:**
    - `__init__(self, asset, component_type)`: Initializes the CVS class with an asset and a component type.
    - `relative_path(self)`: Returns the relative path of the CVS file based on its type and extension.
    - `load(self)`: Loads the CVS data using the shapeio module.
    - `save(self)`: Saves the CVS data using the shapeio module.

### Cross-Module Dependencies
* **Internal Framework Links:** `Component`, `shapeio`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Cvs`

**Purpose:** A component that handles CVS (control vertex) shape data for the controls on a rig.

#### Methods
- `__init__(self, asset, component_type)`: Initializes the CVS class with an asset and a component type.
- `relative_path(self)`: Returns the relative path of the CVS file based on its type and extension.
- `load(self)`: Loads the CVS data using the shapeio module.
- `save(self)`: Saves the CVS data using the shapeio module.

---

I hope this meets your requirements! Let me know if you have any further requests.