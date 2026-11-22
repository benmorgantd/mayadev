"""Save and load by file type, kept apart from where the files live.

A FileHandler knows one format. Handlers are registered per file type key from project.json, by
whatever code owns the format (bmaya.maya.assethandlers registers the Maya ones). This module never
imports a handler, so it stays usable without Maya.

save() keeps a local version copy of the old file, makes the parent folders, and tells source control,
so a handler only writes its format. restore() puts a version copy back, keeping the replaced file as a version.
"""

from __future__ import annotations

import os

import bmaya.core.observable

from . import sourcecontrol, versions
from .asset import Asset

# Emits the file type after every save, restore and load, so a tool that shows the files can read them again
# without the code that saved or loaded knowing about it. bmaya.maya.assethandlers turns it into a Maya user event.
changed = bmaya.core.observable.Event()


class FileHandler:
    """Override save and load. The defaults raise, so a file type without a real handler fails loudly."""

    def save(self, asset: Asset, path: str, **context) -> None:
        raise NotImplementedError(f"{type(self).__name__} can't save {path}.")

    def load(self, asset: Asset, path: str, **context) -> object:
        raise NotImplementedError(f"{type(self).__name__} can't load {path}.")


_HANDLERS: dict[str, FileHandler] = {}


def register(file_type: str, handler: FileHandler) -> None:
    _HANDLERS[file_type] = handler


def unregister(file_type: str) -> None:
    _HANDLERS.pop(file_type, None)


def handler_for(file_type: str) -> FileHandler:
    try:
        return _HANDLERS[file_type]
    except KeyError:
        raise NotImplementedError(f"No handler is registered for file type {file_type!r}.") from None


def save(asset: Asset, file_type: str, owner: str | None = None, **context) -> str:
    """Saves a file type through its handler and returns the path. owner is the skeleton, rig or look the file
    belongs to, for a file type that belongs to one. A local version copy of the old file is kept first, and source
    control checks out an existing path or adds a new one."""
    handler = handler_for(file_type)
    path = asset.path(file_type, owner)
    existed = os.path.exists(path)
    if existed:
        versions.version(path, asset.root)
        sourcecontrol.current().checkout(path)
    folder = path if asset.project.file_type(file_type).folder else os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    handler.save(asset, path, owner=owner, **context)
    if not existed:
        sourcecontrol.current().add(path)
    changed.emit(file_type)
    return path


def restore(asset: Asset, file_type: str, owner: str | None, number: int) -> str:
    """Puts a local version copy of a file type back in place of the file and returns the path. The file it replaces
    is kept as a new version first, so a restore is undone by restoring that one, and source control checks out an
    existing path or adds a new one, as save() does. Nothing in the scene changes: load the file to see it. Raises
    ValueError for a version the file has no copy of."""
    path = asset.path(file_type, owner)
    versions.find_version(path, asset.root, number)   # an unknown version raises before anything changes
    existed = os.path.exists(path)
    if existed:
        versions.version(path, asset.root)
        sourcecontrol.current().checkout(path)
    versions.restore(path, asset.root, number)
    if not existed:
        sourcecontrol.current().add(path)
    changed.emit(file_type)
    return path


def load(asset: Asset, file_type: str, owner: str | None = None, **context) -> object:
    """Loads a file type through its handler and returns what the handler returns."""
    handler = handler_for(file_type)
    path = asset.path(file_type, owner)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{asset.id} has no {file_type} file at {path}.")
    loaded = handler.load(asset, path, owner=owner, **context)
    changed.emit(file_type)
    return loaded
