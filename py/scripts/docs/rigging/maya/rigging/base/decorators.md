Here is the generated Markdown documentation:

# Module: decorators

### Pipeline Intent
Decorators for rigging operations that allow the user to run code before and after the main logic of a function, such as initializing and uninitializing maya.standalone, or running code before and after building a rig. That code can include things like locking attributes, capturing component defaults, etc.

### Technical Implementation

This module provides two decorators: `wrapStandalone` and `wrapBuild`. These decorators allow the user to run custom code before and after executing a function.

### Overview
The `decorator` module is designed to simplify the process of running setup and teardown logic for various rigging operations. By wrapping functions with these decorators, users can ensure that their code runs consistently and reliably, without worrying about manual initialization or clean-up.

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `wrapStandalone`
**Signature:**
```python
def wrapStandalone(fn):
```
#### Arguments
- fn (function): The function to be wrapped.

#### Returns
- wrapper (function): A new function that runs the original function with maya.standalone initialized and unitialized.

---

### 🏷️ `FUNCTION` :: `wrapBuild`
**Signature:**
```python
def wrapBuild(fn):
```
#### Arguments
- fn (function): The function to be wrapped.
- self (object): The object instance being operated on.

#### Returns
- wrapper (function): A new function that runs the original function with various setup and teardown logic performed before and after execution. This includes logging, attribute locking, and component default capturing.

---

That's it! Let me know if you have any further requests or questions.