# Module: constants

### Pipeline Intent
Provides a centralized storage for critical file path and directory locations essential to the Maya rigging pipeline. This module serves as a namespace for frequently used constant values.

### Technical Implementation
Utilizes raw string literals (r"") to define file system paths, allowing for efficient concatenation and handling of backslashes (`\`) on Windows.

### Overview
This module houses fundamental constants that govern the rigging process. It ensures consistency across different operating systems by defining OS-specific directory structures and template locations.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.rigging.constants`, other modules in the rigging pipeline (e.g., `buildio`, `rigTools`)

## API Taxonomy Reference

### 🏷️ `GLOBAL VARIABLE` :: `TEMPLATES_PATH`
- **Type:** str
- **Value/Purpose:** Path to template files used during rigging and animation setup.

```python
TEMPLATES_PATH = r"C:\Users\morga\Documents\mayadev\py\scripts\bmaya3\maya\rigging\templates"
```

Please note that the documentation follows the provided template, with a focus on clarity, consistency, and accuracy. If you have any questions or concerns about this document or its creation process, feel free to ask!