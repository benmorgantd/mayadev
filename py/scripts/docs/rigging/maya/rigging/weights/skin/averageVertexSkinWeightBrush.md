Here is the documentation for the module:

# Module: averageVertexSkinWeightBrush
### Pipeline Intent
Average vertex skin weight brush plugin for Maya.

### Technical Implementation
This module implements a custom brush plugin for Maya. The plugin allows users to manipulate average vertex skin weights in their scene.

### Overview
The `averageVertexSkinWeightBrush` module is responsible for managing the average vertex skin weight brush plugin. It provides two primary functions: `initPaint()` and `paint()`.

## API Taxonomy Reference

### FUNCTION :: initPaint
**Signature:** `def initPaint():`
**Purpose:** Initializes the average vertex skin weight brush plugin.

#### Implementation:
The function sets up the necessary commands to initialize the brush plugin, including defining global variables and procedures.

### FUNCTION :: paint
**Signature:** `def paint():`
**Purpose:** Paints the average vertex skin weight brush in the Maya UI.

#### Implementation:
The function executes a script that paints the average vertex skin weight brush in the Maya UI. It uses the `ScriptPaintTool` class to create the brush and then sets the current context to the brush using the `artUserPaintCtx` command.

### GLOBAL VARIABLE :: pluginFileName
**Type:** string
**Value/Purpose:** The name of the plugin file, used to load or check if the plugin is already loaded.