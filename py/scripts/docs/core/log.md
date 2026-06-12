# Reference Component: `bmaya.core.log`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference (Dynamic Introspection)

### ⚙️ Global Constants & Configurations

| Constant Name | Live Runtime Value | Type / Category |
| :--- | :--- | :--- |
| `_LOGGER` | `None` | Runtime Extracted Value |

---
### 🏷️ `CLASS` :: **MayaLogHandler**

**Description Summary:**
Redirects standard Python logging records to native Maya GUI elements.

#### Methods & Interceptors

#### 🛠️ `__init__(self, level=0)`

```text
Initializes the instance - basically setting the formatter to None
and the filter list to empty.
```


#### 🛠️ `acquire(self)`

```text
Acquire the I/O thread lock.
```


#### 🛠️ `addFilter(self, filter)`

```text
Add the specified filter to this handler.
```


#### 🛠️ `close(self)`

```text
Tidy up any resources used by the handler.

This version removes the handler from an internal map of handlers,
_handlers, which is used for handler lookup by name. Subclasses
should ensure that this gets called from overridden close()
methods.
```


#### 🛠️ `createLock(self)`

```text
Acquire a thread lock for serializing access to the underlying I/O.
```


#### 🛠️ `emit(self, record: logging.LogRecord) -> None`

```text
Do whatever it takes to actually log the specified logging record.

This version is intended to be implemented by subclasses and so
raises a NotImplementedError.
```


#### 🛠️ `filter(self, record)`

```text
Determine if a record is loggable by consulting all the filters.

The default is to allow the record to be logged; any filter can veto
this and the record is then dropped. Returns a zero value if a record
is to be dropped, else non-zero.

.. versionchanged:: 3.2

   Allow filters to be just callables.
```


#### 🛠️ `flush(self)`

```text
Ensure all logging output has been flushed.

This version does nothing and is intended to be implemented by
subclasses.
```


#### 🛠️ `format(self, record)`

```text
Format the specified record.

If a formatter is set, use it. Otherwise, use the default formatter
for the module.
```


#### 🛠️ `get_name(self)`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `handle(self, record)`

```text
Conditionally emit the specified logging record.

Emission depends on filters which may have been added to the handler.
Wrap the actual emission of the record with acquisition/release of
the I/O thread lock. Returns whether the filter passed the record for
emission.
```


#### 🛠️ `handleError(self, record)`

```text
Handle errors which occur during an emit() call.

This method should be called from handlers when an exception is
encountered during an emit() call. If raiseExceptions is false,
exceptions get silently ignored. This is what is mostly wanted
for a logging system - most users will not care about errors in
the logging system, they are more interested in application errors.
You could, however, replace this with a custom handler if you wish.
The record which was being processed is passed in to this method.
```


#### 🛠️ `release(self)`

```text
Release the I/O thread lock.
```


#### 🛠️ `removeFilter(self, filter)`

```text
Remove the specified filter from this handler.
```


#### 🛠️ `setFormatter(self, fmt)`

```text
Set the formatter for this handler.
```


#### 🛠️ `setLevel(self, level)`

```text
Set the logging level of this handler.  level must be an int or a str.
```


#### 🛠️ `set_name(self, name)`

```text
No functional arguments or usage blocks specified.
```



---
### 🛠️ `debug(msg, *args, **kwargs) -> None`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `error(msg, *args, **kwargs) -> None`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `get_logger() -> logging.Logger`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `info(msg, *args, **kwargs) -> None`

```text
No functional arguments or usage blocks specified.
```

### 🛠️ `init_logger() -> logging.Logger`

```text
Explicitly initializes and configures the master bmaya logger.
```

### 🛠️ `warning(msg, *args, **kwargs) -> None`

```text
No functional arguments or usage blocks specified.
```
