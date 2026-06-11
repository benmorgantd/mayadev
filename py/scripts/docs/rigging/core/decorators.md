Here is the documentation for the `decorators` module:

# Module: decorators
### Pipeline Intent
The `decorators` module provides a foundation for building reusable decorators that can be applied to functions, preserving metadata and facilitating logging.

### Technical Implementation
This module utilizes the `functools.wraps` decorator to preserve the metadata of wrapped functions. It also imports the `log` module from the parent package (`bmaya.core`) to facilitate logging.

### Overview
The `decorators` module contains two main components: `decorator_maker`, a base decorator that transforms a given function into a reusable decorator, and `log_fn_duration`, a decorator that measures the execution time of a wrapped function and logs the result.

## API Taxonomy Reference

### 🏷️ `FUNCTION` :: `decorator_maker`
**Signature:**
```python
def decorator_maker(meta_decorator):
```
#### Description:
A base decorator that wraps a function, transforming it into a reusable decorator that preserves metadata cleanly.

#### Parameters:

* `meta_decorator`: The original function to be wrapped and transformed.

### 🏷️ `FUNCTION` :: `log_fn_duration`
**Signature:**
```python
@decorator_maker
def log_fn_duration(func, *args, **kwargs):
```
#### Description:
Measures the execution time of a function and prints the duration.

#### Parameters:

* `func`: The target function to be executed and timed.
* `*args`, `**kwargs`: Optional arguments passed to the wrapped function.

### Cross-Module Dependencies
* **Internal Framework Links:** None
* **External Dependencies:** `functools.wraps` (from Python's standard library), `log` module from `bmaya.core`

Note: The code has been strictly formatted according to the provided guidelines.