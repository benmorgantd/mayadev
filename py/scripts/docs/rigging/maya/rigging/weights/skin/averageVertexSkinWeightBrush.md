# Module: averageVertexSkinWeightBrush

### Pipeline Intent
Provides a custom brush for skinning tools that can paint vertex weights in Maya.

### Technical Implementation
Uses the Maya scripting API to create a global procedure that handles painting of vertex skin weights. The procedure utilizes an internal buffer to store selected vertices and their corresponding skin weights.

### Overview
This module provides a script-based implementation of a custom brush for painting vertex skin weights in Maya. It can be used as a part of a larger toolkit for character rigging and skinning operations.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.skin`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

#### Methods
None

---

### 🏷️ `FUNCTION` :: `initPaint`
**Signature:**
```python
def initPaint():
```
#### Description
Initializes the custom brush by defining global procedures for painting vertex skin weights.

---

### 🏷️ `FUNCTION` :: `paint`
**Signature:**
```python
def paint():
```
#### Description
Activates the custom brush and sets it as the current tool in Maya's UI.

---

### 🏷️ `GLOBAL VARIABLE` :: N/A

* **Type:** N/A
* **Value/Purpose:** None

Documentation Drift:
None