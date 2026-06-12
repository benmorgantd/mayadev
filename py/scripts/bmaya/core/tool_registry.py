"""Base class for a user-facing tool which can be kept within a registry and shown in different views."""

import os
import json
import uuid
from typing import Any
from . import log


class Tool(object):
    """Encapsulates the core data configuration and execution logic for a single tool."""

    def __init__(
        self,
        name: str,
        script: str,
        short_name: str | None = None,
        icon: str | None = None,
        enabled: bool = True,
        guid: str | None = None,
    ) -> None:
        self.guid = guid or str(uuid.uuid4())
        self.name = name
        self.short_name = short_name or name
        self.script = script
        self.icon = icon
        self.enabled = enabled

    def to_dict(self) -> dict[str, object]:
        """Serializes the tool instances to a primitive dictionary."""
        return {
            "guid": self.guid,
            "name": self.name,
            "short_name": self.short_name,
            "script": self.script,
            "icon": self.icon,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tool":
        """Deserializes a dictionary configuration into a Tool instance."""
        return cls(
            name=data["name"],
            script=data["script"],
            short_name=data.get("short_name"),
            icon=data.get("icon"),
            enabled=data.get("enabled", True),
            guid=data.get("guid"),
        )


class ToolRegistry(object):
    """Manages the source of truth database containing all production tools."""

    def __init__(self) -> None:
        self.tools = {}

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.guid] = tool

    def load_registry(self, filepath: str) -> bool:
        """Loads and parses the master tool tracking file."""
        if not os.path.exists(filepath):
            return False

        with open(filepath, "r") as f:
            data = json.load(f)

        for tool_data in data.get("tools", []):
            tool = Tool.from_dict(tool_data)
            self.register_tool(tool)

        log.info("Initialized the Tools Registry")
        return True

    def save_registry(self, filepath: str) -> None:
        """Saves current memory state out to the master JSON manifest."""
        data = {"tools": [tool.to_dict() for tool in self.tools.values()]}
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
