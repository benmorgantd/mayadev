# Module: fileUtils

### Pipeline Intent
Provides a utility function for safely saving off versions of files in a designated directory. This feature allows animators to manage their character rig performance files by automatically creating incremental versions.

### Technical Implementation
Utilizes the standard library `os` and `shutil` modules to perform file system operations, such as creating directories and copying files.

### Overview
The `versionFile` function takes a file path as input and creates a copy of that file with an incremented version number. The original file remains unchanged, while the new version is saved in a designated directory.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** Maya.cmds (not used), OpenMaya (not used)

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `versionFile`
**Signature:**
```python
def versionFile(filepath):
```
#### Arguments
- filepath (str): The file to version.

#### Returns
None

---

Note: There is no documentation drift detected.