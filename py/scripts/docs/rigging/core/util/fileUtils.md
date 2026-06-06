# Module: fileUtils

### Pipeline Intent
Provides automated versioning utilities for asset files using the standard library `os` and `shutil` modules. Handles directory generation asynchronously when creating nested version tracks.

### Technical Implementation
Exposes a single function, `versionFile`, which saves off a copy of the given file to a `<filename>.Versions` folder.

### Overview
The `fileUtils` module offers a simple way to manage versioning for assets in your Maya pipeline. This implementation uses the `os` and `shutil` modules to create a new directory structure for each versioned file, keeping track of previous versions.

### Cross-Module Dependencies
* **Internal Framework Links:** None

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

### Implementation Notes
Documentation Drift:
* No drift detected.