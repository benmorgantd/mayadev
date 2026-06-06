# Module: boundingBoxUtils

### Pipeline Intent
Provides utilities for working with bounding boxes in Maya. These methods are used by various components to perform common tasks that involve bounding boxes, such as framing the scene.

### Technical Implementation
Utilizes the OpenMaya API (om) and Maya's built-in functions (MFn) to interact with the scene DAGs and retrieve their bounding boxes.

### Overview
This module offers two primary methods: `getSceneBoundingBox` and `getBoundingBoxCenter`. The first method retrieves the overall bounding box of all DAGs in the scene, while the second method calculates the center point of a given bounding box.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** maya.OpenMaya (om)

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `getSceneBoundingBox`
**Signature:**
```python
def getSceneBoundingBox():
```
#### Purpose:
Returns the bounding box around the DAGs in the scene.

#### Returns:
A Maya OpenMaya (`om.MBoundingBox`) object representing the overall bounding box of all DAGs in the scene.

---

### 🏷️ `FUNCTION` :: `getBoundingBoxCenter`
**Signature:**
```python
def getBoundingBoxCenter(boundingBox):
```
#### Purpose:
Calculates and returns the center point of a given bounding box.

#### Arguments:
- `boundingBox`: The Maya OpenMaya (`om.MBoundingBox`) object for which to calculate the center point.

#### Returns:
A list containing the x, y, and z coordinates of the center point.