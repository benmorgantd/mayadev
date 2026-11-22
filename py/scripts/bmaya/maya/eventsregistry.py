"""The one owner of bmaya's OpenMaya (API 2) callbacks: every Maya callback a bmaya tool needs goes through
EventsRegistry, so each is tracked by key, can be paused, and is removed when Maya exits.

What the registry guarantees, so a tool's callback can't take Maya down or starve another tool's:
    guarded      an exception in a callback is logged with its traceback and never reaches Maya
    no recursion a callback that triggers its own event (a selection callback that selects) is not called again
                 until it returns
    safe removal a callback removed or paused while any registry callback is running stops being called at once,
                 and is taken out of Maya once the outermost callback returns, never while Maya is calling it
    exiting      the registry holds the one kMayaExiting callback. The closing callbacks run from it, in the order
                 they were added, and then every callback is removed
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any

import maya.api.OpenMaya as om

import bmaya.core.log


class EventType(object):
    """The callback categories. pause_callbacks pauses by category."""

    MAYA_CLOSING = "maya_closing"
    NODE_ADDED = "node_added"
    SELECTION_CHANGED = "selection_changed"
    SCENE_NEW = "scene_new"
    SCENE_OPEN = "scene_open"


class EventsRegistry(object):
    """Singleton that registers, tracks, pauses and removes the session's Maya callbacks (see the module docstring).

    callbacks maps each key to its entry: id (the Maya callback id, None while paused and for a closing callback),
    type (an EventType), user_func, paused.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EventsRegistry, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._callbacks: dict[str, dict[str, Any]] = {}
        self._dispatch_depth = 0          # how many registry callbacks are running, nested
        self._pending_removals: list[int] = []
        self._shutdown_id = om.MSceneMessage.addCallback(om.MSceneMessage.kMayaExiting, self._on_maya_shutdown)
        self._initialized = True

    # ---- dispatch --------------------------------------------------------------------------

    def _guard(self, key: str, entry: dict[str, Any]) -> Callable[..., None]:
        """The function Maya calls for an entry. It calls the entry's user_func unless the entry was removed or
        paused, or is already running."""

        def guarded(*args):
            if entry["removed"] or entry["paused"] or entry["running"]:
                return
            entry["running"] = True
            self._dispatch_depth += 1
            try:
                entry["user_func"](*args)
            except Exception:
                bmaya.core.log.error(f"Callback {key} failed:\n{traceback.format_exc()}")
            finally:
                entry["running"] = False
                self._dispatch_depth -= 1
                if self._dispatch_depth == 0:
                    self._flush_removals()

        return guarded

    def _remove_from_maya(self, cb_id: int | None) -> None:
        """Takes a callback out of Maya, or queues it when a registry callback is running: Maya may be iterating
        the list it is in."""
        if cb_id is None:
            return
        if self._dispatch_depth > 0:
            self._pending_removals.append(cb_id)
            return
        try:
            om.MMessage.removeCallback(cb_id)
        except RuntimeError:
            pass   # Maya already dropped it (its node or context was torn down)

    def _flush_removals(self) -> None:
        pending, self._pending_removals = self._pending_removals, []
        for cb_id in pending:
            self._remove_from_maya(cb_id)

    def _on_maya_shutdown(self, *args) -> None:
        """Runs the closing callbacks, then removes every callback and this one."""
        bmaya.core.log.info("Maya shutdown detected. Cleaning up all pipeline callbacks.")
        for key, entry in list(self._callbacks.items()):
            if entry["type"] == EventType.MAYA_CLOSING:
                self._guard(key, entry)(*args)
        self.unregister_all()
        if self._shutdown_id is not None:
            try:
                om.MMessage.removeCallback(self._shutdown_id)
            except RuntimeError:
                pass
            self._shutdown_id = None

    # ---- registering -----------------------------------------------------------------------

    def _register_core(self, key: str, cb_type: str, user_func: Callable[..., None],
                       register: Callable[[Callable[..., None]], int] | None) -> int | None:
        """Tracks user_func under key and registers it with Maya through register, which takes the guarded function
        and returns the callback id. register is None for a closing callback, which the registry calls itself.
        A key that exists is replaced. Returns the Maya callback id."""
        if key in self._callbacks:
            bmaya.core.log.warning(f"Callback key '{key}' already exists. Overwriting current callback.")
            self.unregister(key)

        entry = {"id": None, "type": cb_type, "user_func": user_func, "register": register,
                 "paused": False, "running": False, "removed": False}
        entry["guarded"] = self._guard(key, entry)
        if register is not None:
            try:
                entry["id"] = register(entry["guarded"])
            except Exception as error:
                bmaya.core.log.error(f"Failed to register callback for key '{key}': {error}")
                raise
        self._callbacks[key] = entry
        bmaya.core.log.info(f"Registered callback {key} of type {cb_type}")
        return entry["id"]

    def add_maya_closing_callback(self, key, callback_func):
        """Maya is about to exit. Called from the registry's own kMayaExiting callback, before anything is removed."""
        return self._register_core(key, EventType.MAYA_CLOSING, callback_func, None)

    def add_maya_new_scene_callback(self, key, callback_func):
        """MSceneMessage kAfterNew: a new scene was made."""
        return self._register_core(
            key, EventType.SCENE_NEW, callback_func,
            lambda guarded: om.MSceneMessage.addCallback(om.MSceneMessage.kAfterNew, guarded))

    def add_maya_open_scene_callback(self, key, callback_func):
        """MSceneMessage kAfterOpen: a scene was opened."""
        return self._register_core(
            key, EventType.SCENE_OPEN, callback_func,
            lambda guarded: om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, guarded))

    def add_selection_changed_callback(self, key, callback_func):
        """MEventMessage SelectionChanged: the object or component selection changed."""
        return self._register_core(
            key, EventType.SELECTION_CHANGED, callback_func,
            lambda guarded: om.MEventMessage.addEventCallback("SelectionChanged", guarded))

    def add_node_added_callback(self, key, callback_func, node_type="dependNode"):
        """MDGMessage: a node of node_type was added to the dependency graph."""
        return self._register_core(
            key, EventType.NODE_ADDED, callback_func,
            lambda guarded: om.MDGMessage.addNodeAddedCallback(guarded, node_type))

    # ---- state -----------------------------------------------------------------------------

    def unregister(self, key):
        """Removes a callback from Maya and stops tracking it. Returns whether the key was registered."""
        entry = self._callbacks.pop(key, None)
        if entry is None:
            return False
        entry["removed"] = True
        self._remove_from_maya(entry["id"])
        entry["id"] = None
        bmaya.core.log.info(f"Unregistered callback {key}")
        return True

    def pause(self, key):
        """Takes a callback out of Maya and keeps it tracked, for resume. Returns whether it changed anything."""
        entry = self._callbacks.get(key)
        if entry is None or entry["paused"]:
            return False
        entry["paused"] = True
        self._remove_from_maya(entry["id"])
        entry["id"] = None
        return True

    def resume(self, key):
        """Registers a paused callback with Maya again. Returns whether it changed anything. A failed registration
        is logged and leaves the callback paused, so a caller resuming several goes on to the next."""
        entry = self._callbacks.get(key)
        if entry is None or not entry["paused"]:
            return False
        if entry["register"] is not None:
            try:
                entry["id"] = entry["register"](entry["guarded"])
            except Exception as error:
                bmaya.core.log.error(f"Failed to resume callback {key}: {error}")
                return False
        entry["paused"] = False
        return True

    def unregister_all(self):
        """Removes every callback the registry tracks. The registry's own kMayaExiting callback stays."""
        for key in list(self._callbacks.keys()):
            self.unregister(key)

    @property
    def callbacks(self):
        """The tracked entries by key. Read only: register and remove through the methods."""
        return self._callbacks

    @property
    def active_callbacks(self):
        """The keys that aren't paused."""
        return [k for k, v in self._callbacks.items() if not v["paused"]]


def pause_callbacks(callback_types):
    """Decorator that pauses every callback of the listed EventType categories while the function runs, and resumes
    them in a finally, so an error can't leave one paused. Use it around code that makes many nodes."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            registry = EventsRegistry()
            paused_keys = [key for key, data in list(registry.callbacks.items())
                           if data["type"] in callback_types and registry.pause(key)]
            try:
                return func(*args, **kwargs)
            finally:
                for key in paused_keys:
                    registry.resume(key)

        return wrapper

    return decorator
