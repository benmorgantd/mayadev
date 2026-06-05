# Module: assetCreator

### Pipeline Intent
Provides a graphical interface for animators to initiate the creation of new assets in Maya. This module serves as a foundation for building and managing character rigs, providing a streamlined workflow for artists.

### Technical Implementation
Utilizes the PyQt framework for creating a Qt-based user interface, allowing for seamless integration with Maya's UI components. The `AssetCreator` class inherits from `QtWidgets.QMainWindow`, enabling the creation of a windowed application with a central widget area.

### Overview
The `assetCreator` module is designed to facilitate the process of creating new assets in Maya by providing an intuitive interface for animators. It does so by offering features such as project name, asset type, and asset name input fields, which enable users to specify the properties of their desired asset.

### Cross-Module Dependencies
* **Internal Framework Links:**
	+ `bmaya3.lib.Qt`: Importing Qt modules for UI development.
	+ `bmaya3.rigging.base`: Importing rigging module classes for asset creation.
	+ `bmaya3.core.asset`: Importing asset-related utilities from the core module.

## API Taxonomy Reference

### 🏷️ `CLASS` :: `AssetCreator`
**Purpose:** A graphical interface for creating new assets in Maya, providing a streamlined workflow for animators.

*Inherits from:* `QtWidgets.QMainWindow`

#### Methods
- `__init__(self, parent=None, designerFile=None, title='Asset Creator')`: Initializes the asset creator window.
- `createAsset(self)`: Creates a new asset based on user input and closes the window.

---

### 🏷️ `FUNCTION` :: None

(no functions documented)

---

### 🏷️ `GLOBAL VARIABLE` :: None

(no global variables documented)

Note: Documentation Drift:
* The `createAsset` method's lambda function is not explicitly documented, but its purpose can be inferred from the surrounding code.