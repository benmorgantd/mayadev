# Module: buildio
### Pipeline Intent
Gives the logic for saving and loading the build component, which is a json file that contains the rig structure.

### Technical Implementation
This module utilizes Python's built-in `json` library to load and save data in JSON format. The `load` function reads in a JSON file at the specified filepath and returns the parsed data. The `save` function takes in a dictionary of build data and writes it to a JSON file at the specified filepath.

### Overview
This module provides two functions: `load` and `save`, which allow you to read from and write to a JSON file containing the rig structure. This is useful for storing and retrieving the build component's configuration.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** `json`, `os`

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `load`
**Signature:**
```python
def load(filepath):
```
#### Arguments
- filepath (str): The path to the JSON file.

#### Returns
- build_data (dict): The parsed data from the JSON file.

---

### 🏷️ `FUNCTION` :: `save`
**Signature:**
```python
def save(filepath, data):
```
#### Arguments
- filepath (str): The path to write the JSON file.
- data (dict): The dictionary of build data to be written to the JSON file.

#### Returns
None