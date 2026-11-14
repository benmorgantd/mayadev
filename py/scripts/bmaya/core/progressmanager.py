"""The progress of the current task, as a view-model any number of views can watch through its changed Event."""

from __future__ import annotations

from typing import Optional

from . import log
from .observable import Event


class ProgressManager:
    """A singleton: one task's status text and value. Views connect to changed. In mayapy nothing listens and
    progress goes to the debug log."""

    _instance: Optional["ProgressManager"] = None

    def __new__(cls) -> "ProgressManager":
        if cls._instance is None:
            cls._instance = super(ProgressManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self) -> None:
        self.active: bool = False
        self.status_text: str = "Ready"
        self.current_value: int = 0
        self.max_value: int = 100
        self.changed = Event()

    def start(self, status: str, max_value: int = 100) -> None:
        """Starts tracking a task."""
        self.status_text = status
        self.max_value = max_value
        self.current_value = 0
        self.active = True
        self.changed.emit()

    def update(self, value: int, status: Optional[str] = None) -> None:
        """Sets the value and, when given, the status text. Does nothing while no task is active."""
        if not self.active:
            return
        self.current_value = min(value, self.max_value)
        if status is not None:
            self.status_text = status
        log.debug(f"[ProgressManager] {value}% - {status}")
        self.changed.emit()

    def increment(self, amount: int = 1, status: Optional[str] = None) -> None:
        self.update(self.current_value + amount, status)

    def end(self) -> None:
        """Ends the task."""
        self.active = False
        self.current_value = 0
        self.changed.emit()

    def __enter__(self) -> "ProgressManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Ends the task even when it raised, and lets the exception through."""
        if exc_type is not None:
            log.error(f"[ProgressManager] Execution failed {exc_val}")
        self.end()
        return False
