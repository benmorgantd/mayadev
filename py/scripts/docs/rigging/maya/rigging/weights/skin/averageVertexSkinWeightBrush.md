# Module: averageVertexSkinWeightBrush

### Pipeline Intent
Provides a custom brush for animators to adjust skin weights in Maya. This module exposes a script-based solution for painting vertex weights.

### Technical Implementation
Uses the `maya.mel` and `maya.cmds` modules to execute MEL scripts within Maya. The code defines three global procedures: `init_averageVertexWeightBrush`, `set_averageVertexSkinWeightsBrush`, and `averageVertexWeightBrush`.

### Overview
This module provides a script-based solution for painting vertex weights in Maya. It allows animators to adjust skin weights using a custom brush.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.asset.components.skin` (not explicitly imported, but likely used internally)
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `initPaint`
**Signature:**
```python
def initPaint():
```

#### Description
Initializes the paint tool by defining three global procedures.

---

### 🏷️ `FUNCTION` :: `paint`
**Signature:**
```python
def paint():
```

#### Description
Activates the script-based paint tool in Maya.

---

### 🏷️ `GLOBAL VARIABLE` :: `pluginFileName`
- **Type:** str
- **Value/Purpose:** The name of the plugin file used by this module.