# Module: decorators

### Pipeline Intent
Provides a means to decorate rigging operations with pre- and post-processing logic, allowing for the initialization and uninitialization of maya.standalone, as well as running code before and after building a rig.

### Technical Implementation
Exposes two decorator functions: `wrapStandalone` and `wrapBuild`. These decorators provide a way to wrap arbitrary function calls with custom logic, enabling features like locking attributes, capturing component defaults, and more.

### Overview
The `decorators` module offers a flexible mechanism for adding context-specific code before and after the main logic of a rigging operation. This allows developers to enforce specific behaviors or constraints without modifying the underlying code.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** maya.standalone, maya.cmds

## API Taxonomy Reference

### 🏷️ `CLASS` :: N/A

#### Methods
None

---

### 🏷️ `FUNCTION` :: wrapStandalone
**Signature:**
```python
def wrapStandalone(fn):
```
#### Description:
Wraps a function with logic that initializes maya.standalone and uninitializes it after the main logic is executed.

---

### 🏷️ `FUNCTION` :: wrapBuild
**Signature:**
```python
def wrapBuild(fn):
```
#### Description:
Wraps a function with logic that performs various tasks before and after the main rigging operation, including building a limb type, checking contracts, making nodes, capturing component defaults, and locking attributes.

---

### 🏷️ `GLOBAL VARIABLE` :: None

Note: There are no global variables in this module.