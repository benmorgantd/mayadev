"""Change notification without Qt, so view-models in bmaya.core and bmaya.maya can tell a view what changed
(RigModules design/mayadev-ui.md, D49)."""

from __future__ import annotations

import inspect
import weakref
from collections.abc import Callable


class Event:
    """A list of listeners called in the order they connected. A Python bound method is held weakly, so a closed
    view drops out without disconnecting. Anything else (a function, a lambda, a built-in method) is held
    strongly. A listener that raises doesn't stop the ones after it."""

    def __init__(self) -> None:
        self._listeners: list[weakref.WeakMethod | Callable[..., None]] = []

    def connect(self, listener: Callable[..., None]) -> None:
        if listener not in self.listeners():
            # Only a Python bound method can be held weakly. A built-in one (list.append) is held strongly.
            self._listeners.append(weakref.WeakMethod(listener) if inspect.ismethod(listener) else listener)

    def disconnect(self, listener: Callable[..., None]) -> None:
        self._listeners = [entry for entry in self._listeners if self._resolve(entry) not in (listener, None)]

    def listeners(self) -> list[Callable[..., None]]:
        """The live listeners. Dead weak references are dropped."""
        live = []
        kept = []
        for entry in self._listeners:
            listener = self._resolve(entry)
            if listener is not None:
                live.append(listener)
                kept.append(entry)
        self._listeners = kept
        return live

    def emit(self, *args) -> None:
        """Calls every listener, even after one raises, so one broken view can't leave the others stale. The first
        error is raised again once the last listener has run."""
        error: BaseException | None = None
        for listener in self.listeners():
            try:
                listener(*args)
            except Exception as raised:
                if error is None:
                    error = raised
        if error is not None:
            raise error

    @staticmethod
    def _resolve(entry: weakref.WeakMethod | Callable[..., None]) -> Callable[..., None] | None:
        return entry() if isinstance(entry, weakref.WeakMethod) else entry
