Here is the Markdown documentation for the `asset` module:

# Module: asset

### Pipeline Intent

Base class for production Assets that handles logic for asset Id, file management, and versioning. Assets are made up of components, which are the individual files that make up the asset.

### Technical Implementation

The `Asset` class is designed to handle the identification, creation, and management of assets in a Maya project. It provides methods for opening the asset in the file explorer, opening the asset file in Maya, referencing the asset file in Maya, checking if an asset exists, finding files of a certain type within the asset's directory, and versioning the asset.

### Overview

The `Asset` class has several key features:

*   It uses the `validate_id` method to ensure that the given id is acceptable. The id should be a string in the format: project|type|name.
*   It provides methods for opening the asset in the file explorer, opening the asset file in Maya, referencing the asset file in Maya, checking if an asset exists, finding files of a certain type within the asset's directory, and versioning the asset.

### Cross-Module Dependencies

*   **Internal Framework Links:** `bmaya.core`, `maya.cmds`
*   **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Asset`

**Purpose:** Base class for production Assets that handles logic for asset Id, file management, and versioning.

**Methods**

- `__init__(self, asset_id)`: Initializes the Asset with a given id.
- `root_dir(self)`: Returns the root directory of the asset.
- `project(self)`: Returns the project name associated with the asset.
- `asset_type(self)`: Returns the type of the asset (e.g. character, prop, environment).
- `name(self)`: Returns the name of the asset.
- `validate_id(cls, asset_id)`: Validates whether the given id is acceptable.
- `open_in_explorer(cls, path)`: Opens the file explorer at the given path.
- `open_file(cls, path)`: Opens the file in Maya at the given path.
- `reference_file(cls, path)`: References the file in Maya at the given path.
- `exists(cls, project, name, asset_type)`: Checks if an asset exists with the given project, name, and type.
- `find_files_of_type(cls, path, filetype)`: Finds files of a certain type within the asset's directory.
- `split_path(cls, filepath)`: Splits a file path into its components.
- `get_asset_id_from_file(cls, filepath)`: Derives the asset's name, type, and project from a given file path.
- `component_path_from_type(self, component_type)`: Returns the path of a component with a given type.
- `version_asset(self)`: Versions the entire asset to a folder.

### 🏷️ `FUNCTION` :: `clean_path`

**Signature:**
```python
def clean_path(cls, filepath)
```
**Description:** Cleans and normalizes a file path.