# Module: asset

### Pipeline Intent
Provides a foundation for production Assets that handle file management, versioning, and asset Id validation. This class serves as a base for character, prop, environment, and other types of assets.

### Technical Implementation
Utilizes Python's built-in `os` and `shutil` modules to manage directory scaffolding, file copying, and path manipulation. Interacts with Maya's `cmds` module for opening asset files in the application.

### Overview
The Asset class encapsulates the core logic for managing production assets, including component management, file organization, and versioning. It also provides methods for checking if an asset exists, finding files of a specific type within the asset's directory, and referencing or opening asset files.

### Cross-Module Dependencies

* **Internal Framework Links:** `bmaya.maya.asset.components.animRig`, `bmaya.maya.asset.components.build`, `bmaya.maya.asset.components.component`, etc.
* **External Dependencies:** Maya.cmds, os, shutil

## API Taxonomy Reference

### 🏷️ `CLASS` :: `Asset`
**Purpose:** Base class for production Assets that handles logic for asset Id, file management, and versioning.

#### Methods
- `__init__(self, assetId)`: Initializes the Asset instance with a given asset ID.
- `rootDir(self)`: Returns the root directory path of the asset.
- `project(self)`: Retrieves the project name from the asset ID.
- `assetType(self)`: Gets the type (character, prop, environment, etc.) from the asset ID.
- `name(self)`: Obtains the asset name from the asset ID.
- `validateId(cls, assetId)`: Verifies whether the given asset ID is in the correct format: project|type|name.
- `openInExplorer(cls, path)`: Opens the given file path in the system's default file explorer.
- `openFile(cls, path)`: Opens the given file path in Maya if it's a `.ma` file or opens it with the system's default application otherwise.
- `referenceFile(cls, path)`: References the given file path in Maya by creating a namespace.
- `exists(cls, project, name, assetType)`: Checks if an asset exists based on its project, name, and type.
- `findFilesOfType(cls, path, filetype)`: Finds files of a specific type within the given directory path.
- `splitpath(cls, filepath)`: Splits a file path into all its components.
- `getAssetIdFromFile(cls, filepath)`: Derives the asset's project, type, and name from a given file path.
- `componentPathFromType(self, componentType)`: Retrieves the full path of a component based on its type.
- `versionAsset(self)`: Versions the entire asset to a folder.

### 🏷️ `GLOBAL VARIABLE` :: `PROJECT_DIR`
- **Type:** str
- **Value/Purpose:** The root directory path for project files, set by the RIGGING_PROJECT_DIR environment variable.