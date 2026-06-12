# Reference Component: `bmaya.maya.eventsregistry`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference (Dynamic Introspection)

### 🏷️ `CLASS` :: **EventType**

**Description Summary:**
Enum-like class defining supported callback categories for pipeline organization.

Using class attributes provides autocomplete support and centralized tracking 
for the EventRegistry and its associated decorators.

#### Methods & Interceptors


---
### 🏷️ `CLASS` :: **EventsRegistry**

**Description Summary:**
Singleton registry responsible for managing OpenMaya API 2.0 callbacks.

Tracks, groups, pauses, and safely unregisters callbacks within a Maya session
to prevent memory leaks, execution loops, and scene corruption. Automatically 
cleans up all managed callbacks when Maya exits.

#### Methods & Interceptors

#### 🛠️ `__init__(self)`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `_register_core(self, key, cb_type, api_reg_func, user_func, *args, **kwargs)`

```text
Core registration handler ensuring safe tracking and avoiding duplicates.

Args:
    key (str): Unique identifier for tracking the callback.
    cb_type (str): A category value from the EventType class.
    api_reg_func (callable): The OpenMaya function used to register the callback.
    user_func (callable): The callable target executed when the event triggers.

Returns:
    int: The callback ID assigned by OpenMaya.
```


#### 🛠️ `add_maya_closing_callback(self, key, callback_func)`

```text
MSceneMessage: Track when Maya is about to close / exit.
```


#### 🛠️ `add_node_added_callback(self, key, callback_func, node_type='dependNode')`

```text
MDGMessage: Track when a specific type of node is added to the dependency graph.
```


#### 🛠️ `add_selection_changed_callback(self, key, callback_func)`

```text
MEventMessage: Track interactive object/component selection shifts in Maya.
```


#### 🛠️ `pause(self, key)`

```text
Temporarily detaches the callback from Maya while retaining configuration data.

Args:
    key (str): The unique tracker string key for the callback.

Returns:
    bool: True if the callback was successfully paused, False otherwise.
```


#### 🛠️ `resume(self, key)`

```text
Re-evaluates and registers a paused callback back into Maya's engine.

Args:
    key (str): The unique tracker string key for the callback.

Returns:
    bool: True if the callback was successfully resumed, False otherwise.
```


#### 🛠️ `unregister(self, key)`

```text
Completely removes a callback from Maya and untracks it from the registry.

Args:
    key (str): The unique tracker string key for the callback.

Returns:
    bool: True if unregistration succeeded, False otherwise.
```


#### 🛠️ `unregister_all(self)`

```text
Flushes all registered pipeline callbacks safely.
```



---
### 🛠️ `pause_callbacks(callback_types)`

```text
Decorator to temporarily pause execution of specific callback categories.

Uses a try-finally architecture to ensure that even if the decorated function 
encounters a critical error during execution, the target callbacks are guaranteed 
to resume functionality.

Args:
    callback_types (list): A list of EventType string variables to pause (e.g., [EventType.NODE_ADDED])
```
