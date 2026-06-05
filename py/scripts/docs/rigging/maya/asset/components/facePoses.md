# Module: facePoses

### Pipeline Intent
Provides a mechanism for animators to hand-animate facial poses on the rig and save these off as a Maya file. This module serves as a component for storing and managing these pose animations.

### Technical Implementation
Faces the challenge of creating a localized directory structure for storing facial pose animations, utilizing Python's built-in `os` module to ensure platform independence.

### Overview
The FacePoses module is part of the larger Maya asset pipeline, enabling animators to create and save custom facial pose animations. By inheriting from the base `MayaComponent` class, this component can leverage shared functionality for managing asset data and directory paths.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.mayaComponent`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `FacePoses`

**Purpose:** A Maya file component for storing facial pose animations.

#### Methods

- `__init__(self, asset, componentType)`: Initializes the FacePoses component with an asset and a component type.
- `@property relativePath(self)`: Returns the relative path of the facial pose animation file based on its type and extension.