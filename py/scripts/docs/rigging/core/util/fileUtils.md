# Module: fileUtils
### Pipeline Intent
Provide utility functions for handling files and directories in the Maya pipeline.

### Technical Implementation
This module utilizes Python's built-in `os` and `shutil` modules to interact with the file system. It also imports the `log` module from `bmaya.core` to facilitate logging functionality.

### Overview
The `fileUtils` module contains a single function, `version_file`, which saves off a copy of the given file to a `<filename>.Versions` folder.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** `os`, `shutil`, `bmaya.core.log`

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `version_file`
**Signature:**
```python
def version_file(filepath: str) -> None:
```
#### Arguments
- filepath (str): The file to version.

#### Returns
None

#### Purpose
Saves off a copy of the given file to a `<filename>.Versions` folder. If the folder does not exist, it is created. The function then copies the original file to a new filename with the extension and a version number appended.

---

Please note that there are no classes defined in this module.