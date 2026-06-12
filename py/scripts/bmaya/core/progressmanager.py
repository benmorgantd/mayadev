"""Singleton class for tracking the progress of different tasks, which a UI can watch to update itself."""

import traceback
from typing import Optional, Callable
from . import log


class ProgressManager:
    _instance: Optional["ProgressManager"] = None

    def __new__(cls) -> "ProgressManager":
        if cls._instance is None:
            cls._instance = super(ProgressManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self) -> None:
        """Initialize the singleton state variables."""
        self.active: bool = False
        self.status_text: str = "Ready"
        self.current_value: int = 0
        self.max_value: int = 100
        self._on_update_callback: Optional[Callable[[], None]] = None

    def start(self, status: str, max_value: int = 100) -> None:
        """Explicitly kick off a progress tracking session."""
        self.status_text = status
        self.max_value = max_value
        self.current_value = 0
        self.active = True
        self._trigger_update()

    def update(self, value: int, status: Optional[str] = None) -> None:
        """Update progress value and optionally the status text from anywhere."""
        if not self.active:
            return
        self.current_value = min(value, self.max_value)
        if status is not None:
            self.status_text = status
        log.debug(f"[ProgressManager] {value}% - {status}")
        self._trigger_update()

    def increment(self, amount: int = 1, status: Optional[str] = None) -> None:
        """Increment current progress by a specific amount."""
        self.update(self.current_value + amount, status)

    def end(self) -> None:
        """Clean up state and signal that progress is finished."""
        self.active = False
        self.current_value = 0
        self._trigger_update()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Hook for the UI to listen for updates."""
        self._on_update_callback = callback

    def _trigger_update(self) -> None:
        if self._on_update_callback:
            self._on_update_callback()

    # --- Context Manager Support for Exception Handling ---
    def __enter__(self) -> "ProgressManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Ensures that progress resets/ends cleanly even if an exception occurs."""
        if exc_type is not None:
            # Optional: Log the failure details locally before closing down
            log.error(f"[ProgressManager] Execution failed {exc_val}")

        self.end()
        return False  # Do not suppress the exception; let Maya handle or display it
