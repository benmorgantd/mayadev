# Reference Component: `bmaya.core.tool_registry`

## Module Level Context
No module documentation provided.

---
## Object Taxonomy Reference

### 🏷️ `CLASS` :: **Tool**

**Description Summary:**
Encapsulates the core data configuration and execution logic for a single tool.

#### Methods & Interceptors

#### 🛠️ `__init__(self, name: str, script: str, short_name: str | None = None, icon: str | None = None, enabled: bool = True, guid: str | None = None) -> None`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `to_dict(self) -> dict[str, object]`

```text
Serializes the tool instances to a primitive dictionary.
```



---
### 🏷️ `CLASS` :: **ToolRegistry**

**Description Summary:**
Manages the source of truth database containing all production tools.

#### Methods & Interceptors

#### 🛠️ `__init__(self) -> None`

```text
Initialize self.  See help(type(self)) for accurate signature.
```


#### 🛠️ `load_registry(self, filepath: str) -> bool`

```text
Loads and parses the master tool tracking file.
```


#### 🛠️ `register_tool(self, tool: bmaya.core.tool_registry.Tool) -> None`

```text
No functional arguments or usage blocks specified.
```


#### 🛠️ `save_registry(self, filepath: str) -> None`

```text
Saves current memory state out to the master JSON manifest.
```



---