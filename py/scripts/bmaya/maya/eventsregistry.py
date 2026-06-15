import maya.api.OpenMaya as om
from bmaya.core import log
from functools import wraps


class EventType(object):
    """Enum-like class defining supported callback categories for pipeline organization.

    Using class attributes provides autocomplete support and centralized tracking
    for the EventRegistry and its associated decorators.
    """

    MAYA_CLOSING = "maya_closing"
    NODE_ADDED = "node_added"
    SELECTION_CHANGED = "selection_changed"
    SCENE_NEW = "scene_new"
    SCENE_OPEN = "scene_open"


class EventsRegistry(object):
    """Singleton registry responsible for managing OpenMaya API 2.0 callbacks.

    Tracks, groups, pauses, and safely unregisters callbacks within a Maya session
    to prevent memory leaks, execution loops, and scene corruption. Automatically
    cleans up all managed callbacks when Maya exits.
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

        # Internal storage: { key_string: { id, type, api_reg_func, user_func, args, kwargs, paused } }
        self._callbacks = {}
        self._initialized = True

        # Register automatic teardown on Maya shutdown
        self._shutdown_id = om.MSceneMessage.addCallback(
            om.MSceneMessage.kMayaExiting, self._on_maya_shutdown
        )

    def _on_maya_shutdown(self, *args, **kwargs):
        """Internal cleanup method triggered automatically when Maya exits."""
        log.info("Maya shutdown detected. Cleaning up all pipeline callbacks.")
        self.unregister_all()
        if self._shutdown_id is not None:
            try:
                om.MMessage.removeCallback(self._shutdown_id)
            except RuntimeError:
                pass
            self._shutdown_id = None

    def _register_core(self, key, cb_type, api_reg_func, user_func, *args, **kwargs):
        """Core registration handler ensuring safe tracking and avoiding duplicates.

        Args:
            key (str): Unique identifier for tracking the callback.
            cb_type (str): A category value from the EventType class.
            api_reg_func (callable): The OpenMaya function used to register the callback.
            user_func (callable): The callable target executed when the event triggers.

        Returns:
            int: The callback ID assigned by OpenMaya.
        """
        if key in self._callbacks:
            log.warning(
                f"Callback key '{key}' already exists. Overwriting current callback."
            )
            self.unregister(key)

        try:
            cb_id = api_reg_func(*args, **kwargs)
        except Exception as e:
            log.error(f"Failed to register callback for key '{key}': {e}")
            raise

        self._callbacks[key] = {
            "id": cb_id,
            "type": cb_type,
            "api_reg_func": api_reg_func,
            "user_func": user_func,
            "args": args,
            "kwargs": kwargs,
            "paused": False,
        }

        log.info(f"Registered callback {key} of type {cb_type}")

        return cb_id

    # --- Specific Public API Wrappers ---

    ### Scene Message ###

    def add_maya_closing_callback(self, key, callback_func):
        """MSceneMessage: Track when Maya is about to close / exit."""
        return self._register_core(
            key,
            EventType.MAYA_CLOSING,
            om.MSceneMessage.addCallback,
            callback_func,
            om.MSceneMessage.kMayaExiting,
            callback_func,
            None,
        )

    def add_maya_new_scene_callback(self, key, callback_func):
        """MSceneMessage: Track when a new scene is created."""
        return self._register_core(
            key,
            EventType.SCENE_NEW,
            om.MSceneMessage.addCallback,
            callback_func,
            om.MSceneMessage.kAfterNew,
            callback_func,
            None,
        )

    def add_maya_open_scene_callback(self, key, callback_func):
        """MSceneMessage: Fires after a scene is opened."""
        return self._register_core(
            key,
            EventType.SCENE_OPEN,
            om.MSceneMessage.addCallback,
            callback_func,
            om.MSceneMessage.kAfterOpen,
            callback_func,
            None,
        )

    ### Event Message ###

    def add_selection_changed_callback(self, key, callback_func):
        """MEventMessage: Track interactive object/component selection shifts in Maya."""
        return self._register_core(
            key,
            EventType.SELECTION_CHANGED,
            om.MEventMessage.addEventCallback,
            callback_func,
            "SelectionChanged",
            callback_func,
            None,
        )

    ### DG Message ###

    def add_node_added_callback(self, key, callback_func, node_type="dependNode"):
        """MDGMessage: Track when a specific type of node is added to the dependency graph."""
        return self._register_core(
            key,
            EventType.NODE_ADDED,
            om.MDGMessage.addNodeAddedCallback,
            callback_func,
            callback_func,
            node_type,
            None,
        )

    # --- State Control Operations ---

    def unregister(self, key):
        """Completely removes a callback from Maya and untracks it from the registry.

        Args:
            key (str): The unique tracker string key for the callback.

        Returns:
            bool: True if unregistration succeeded, False otherwise.
        """
        if key not in self._callbacks:
            return False

        cb_data = self._callbacks[key]
        if cb_data["id"] is not None:
            try:
                om.MMessage.removeCallback(cb_data["id"])
                log.info(f"Unregistered callback {key}")
            except RuntimeError:
                # Handle cases where the node/context was already torn down by Maya
                pass

        del self._callbacks[key]
        return True

    def pause(self, key):
        """Temporarily detaches the callback from Maya while retaining configuration data.

        Args:
            key (str): The unique tracker string key for the callback.

        Returns:
            bool: True if the callback was successfully paused, False otherwise.
        """
        if key not in self._callbacks:
            return False

        cb_data = self._callbacks[key]
        if cb_data["paused"] or cb_data["id"] is None:
            return False

        try:
            om.MMessage.removeCallback(cb_data["id"])
        except RuntimeError:
            pass

        cb_data["id"] = None
        cb_data["paused"] = True
        return True

    def resume(self, key):
        """Re-evaluates and registers a paused callback back into Maya's engine.

        Args:
            key (str): The unique tracker string key for the callback.

        Returns:
            bool: True if the callback was successfully resumed, False otherwise.
        """
        if key not in self._callbacks:
            return False

        cb_data = self._callbacks[key]
        if not cb_data["paused"]:
            return False

        api_func = cb_data["api_reg_func"]
        args = cb_data["args"]
        kwargs = cb_data["kwargs"]

        # Re-register using preserved tracking data
        cb_data["id"] = api_func(*args, **kwargs)
        cb_data["paused"] = False
        return True

    def unregister_all(self):
        """Flushes all registered pipeline callbacks safely."""
        for key in list(self._callbacks.keys()):
            self.unregister(key)

    @property
    def callbacks(self):
        """Provides access to the raw internal registry tracking dictionary."""
        return self._callbacks

    @property
    def active_callbacks(self):
        """Returns list of all currently active callback keys."""
        return [k for k, v in self._callbacks.items() if not v["paused"]]


# --- Decorator Implementation ---


def pause_callbacks(callback_types):
    """Decorator to temporarily pause execution of specific callback categories.

    Uses a try-finally architecture to ensure that even if the decorated function
    encounters a critical error during execution, the target callbacks are guaranteed
    to resume functionality.

    Args:
        callback_types (list): A list of EventType string variables to pause (e.g., [EventType.NODE_ADDED])
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            registry = EventsRegistry()
            paused_keys = []

            # Identify and suspend target categories
            for key, data in registry.callbacks.items():
                if data["type"] in callback_types and not data["paused"]:
                    if registry.pause(key):
                        paused_keys.append(key)

            try:
                return func(*args, **kwargs)
            finally:
                # Guaranteed cleanup/resume operations
                for key in paused_keys:
                    registry.resume(key)

        return wrapper

    return decorator
