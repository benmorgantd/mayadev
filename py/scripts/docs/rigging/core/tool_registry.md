Here is the Markdown documentation for the `tool_registry` module:

# Module: tool_registry
## Pipeline Intent
Manage and persistently store a collection of production tools, providing a centralized registry for easy access and manipulation.

## Technical Implementation
The `ToolRegistry` class serves as the central hub for managing a set of registered tools. Each `Tool` instance encapsulates essential data configuration and execution logic, allowing for serialization to primitive dictionaries using the `to_dict` method. Conversely, the `from_dict` method enables deserialization from dictionary configurations into tool instances.

## Overview
This module provides an API for registering, loading, and saving a collection of production tools. It uses a JSON-based storage format to store the registry data, allowing for easy persistence across sessions or system restarts.

## Cross-Module Dependencies
* **Internal Framework Links:** `log` (from `bmaya.core.log`)
* **External Dependencies:** None

### 🏷️ `CLASS` :: `Tool`
**Purpose:** Encapsulates the core data configuration and execution logic for a single tool.
*Inherits from:* `object`

#### Methods
- `__init__(self, name, script, short_name=None, icon=None, enabled=True, guid=None)`: Initializes a new Tool instance with provided settings.
- `to_dict(self)`: Serializes the tool instances to a primitive dictionary.
- `@classmethod` `from_dict(cls, data)`: Deserializes a dictionary configuration into a Tool instance.

### 🏷️ `CLASS` :: `ToolRegistry`
**Purpose:** Manages the source of truth database containing all production tools.
*Inherits from:* `object`

#### Methods
- `__init__(self)`: Initializes an empty tool registry.
- `register_tool(self, tool)`: Registers a new tool instance into the registry.
- `load_registry(self, filepath)`: Loads and parses the master tool tracking file.
- `save_registry(self, filepath)`: Saves current memory state out to the master JSON manifest.

Please let me know if this meets your requirements!