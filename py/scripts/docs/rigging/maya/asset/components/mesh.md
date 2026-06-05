# Module: mesh

### Pipeline Intent
Provides a MayaComponent that contains the model for an Asset. This class serves as a blueprint for modeling and organizing 3D assets within the studio's pipeline.

### Technical Implementation
Inherits from `MayaComponent` to leverage its base functionality. Initializes with asset information and component type, utilizing the `os.path.join` method to generate the relative path for the mesh model file.

### Overview
The Mesh class encapsulates the logic for creating and managing 3D models within Maya. It is designed to be used as a building block in the Asset pipeline, allowing developers to create reusable components that can be easily integrated into larger projects.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.component` (MayaComponent)
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: Mesh
**Purpose:** Contains the model for an Asset, serving as a blueprint for modeling and organizing 3D assets.

#### Methods
- `__init__(self, asset, componentType)`: Initializes the Mesh instance with asset information and component type.
- `@property relativePath(self)`: Returns the relative path of the mesh model file based on its type and extension.