Here is the Markdown documentation for the `constants` module:

# Module: constants
### Pipeline Intent
This module provides a collection of constant values used throughout the rigging pipeline.

### Technical Implementation
The implementation involves setting environment variables as global constants using the `os.environ` dictionary.

### Overview
This module contains two globally accessible constants that are used to store important directory paths for the rigging project. These constants are essential for maintaining consistency and organization in the project's file structure.

### Cross-Module Dependencies
* **Internal Framework Links:** None

## API Taxonomy Reference

### 🏷️ `GLOBAL VARIABLE` :: `RIG_TEMPLATES_DIR`
- **Type:** str
- **Value/Purpose:** Path to the rig templates directory, accessed through environment variables.
  * Line: 3

### 🏷️ `GLOBAL VARIABLE` :: `RIGGING_PROJECT_DIR`
- **Type:** str
- **Value/Purpose:** Path to the rigging project directory, accessed through environment variables.
  * Line: 4