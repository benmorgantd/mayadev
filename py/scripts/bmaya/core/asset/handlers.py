"""Save and load by file type, kept apart from where the files live.

A FileHandler knows one format. Handlers are registered per file type key from project.json, by
whatever code owns the format (bmaya.maya.assethandlers registers the Maya ones). This module never
imports a handler, so it stays usable without Maya.

save() keeps a local version copy of the old file, makes the parent folders, and tells source control,
so a handler only writes its format.
"""

from __future__ import annotations

import os

from . import sourcecontrol, versions
from .asset import Asset


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
    return path


def load(asset: Asset, file_type: str, owner: str | None = None, **context) -> object:
    """Loads a file type through its handler and returns what the handler returns."""
    handler = handler_for(file_type)
    path = asset.path(file_type, owner)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{asset.id} has no {file_type} file at {path}.")
    return handler.load(asset, path, owner=owner, **context)
