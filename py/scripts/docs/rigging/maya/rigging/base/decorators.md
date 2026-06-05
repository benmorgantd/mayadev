# Module: decorators

### Pipeline Intent
Provides a set of decorator functions for rigging operations that allow the user to run code before and after the main logic of a function.

### Technical Implementation
Uses Maya's standalone module for initializing and uninitializing, as well as Python's decorators syntax for wrapping functions.

### Overview
This module exposes two primary decorators: `wrapStandalone` and `wrapBuild`. The first is designed to initialize and terminate Maya's standalone mode before and after executing the main logic. The second is intended for rigging operations that require setup and teardown of various components, such as making nodes, setting attributes, and locking transforms.

### Cross-Module Dependencies
* **Internal Framework Links:** `bmaya.maya.standalone`, `bmaya.maya.cmds`
* **External Dependencies:** None

## API Taxonomy Reference

### 🏷️ `CLASS` :: `None`
**Purpose:** N/A  
*Inherits from:* N/A

#### No methods

---

### 🏷️ `FUNCTION` :: `wrapStandalone`
**Signature:**
```python
def wrapStandalone(fn):
```
#### Arguments
- fn (function): The function to be wrapped.

#### Returns
- A wrapper function that initializes Maya's standalone mode before executing the original function and then uninitializes after execution.

---

### 🏷️ `FUNCTION` :: `wrapBuild`
**Signature:**
```python
def wrapBuild(fn):
```
#### Arguments
- fn (function): The function to be wrapped.
- self (object): The object instance being processed (e.g., a rig component).
- *args, **kwargs: Additional positional and keyword arguments passed to the original function.

#### Returns
- A wrapper function that sets up and tears down various components before and after executing the original function. This includes making nodes, setting attributes, locking transforms, and capturing component defaults.

---

### 🏷️ `GLOBAL VARIABLE` :: None
None