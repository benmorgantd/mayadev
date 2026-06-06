# Module: assetCreator

### Pipeline Intent
Provides a user interface for creating new assets in Maya. This module offers a Qt-based application that initiates the creation process by prompting users to input project name, asset type, and asset name.

### Technical Implementation
Utilizes the Qt framework through `QtWidgets.QMainWindow` and `QtCompat.load_ui()` to load UI designs from `.ui` files. Interacts with Maya's OpenMaya API for creating assets using the `rig.Rig()` function.

### Overview
This module is responsible for handling user input, validating asset existence, and initiating the creation process when prompted.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.core.asset`, `bmaya.maya.rigging.base`
* **External Dependencies:** Maya's OpenMaya API (`maya.OpenMaya as om`)

## API Taxonomy Reference

### 🏷️ `CLASS` :: `AssetCreator`

**Purpose:** Initiates the creation process for new assets in Maya.

#### Methods
- `__init__(self, parent=None, designerFile=None, title='Asset Creator')`: Initializes the asset creator window.
    * `parent` (None): Optional parent widget.
    * `designerFile` (str): Path to a Qt Designer file to load as the main UI component. Defaults to None.
    * `title` (str): Title for the asset creator window. Defaults to 'Asset Creator'.

- `createAsset(self)`: Creates a new asset in Maya based on user input.

---

### 🏷️ `FUNCTION` :: `createAsset`
**Signature:**
```python
def createAsset(self):
    ...
```

#### Arguments
- None

#### Returns
- None