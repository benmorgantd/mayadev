"""The asset context: the asset a tool is working on, set once and kept (RigModules design/asset-editor.md, D61).

An AssetContext holds an asset id and the skeleton, rig and look chosen inside it. It exists only while the Asset Editor
is open: AssetContext.current() is None otherwise, and a menu tool that finds one offers its asset instead of asking
for an id. It changes only when someone sets it. Nothing in it follows a scene, so a new, opened or saved file leaves
it as it is. No Maya.

    context = AssetContext.start("shooter\\main\\characters\\hero")
    context.set_rig("body")
    context.stop()
"""

from __future__ import annotations

from typing import ClassVar

from bmaya.core.asset import assetid
from bmaya.core.asset.asset import Asset, AssetError
from bmaya.core.asset.project import ProjectError
from bmaya.core.observable import Event

DEFAULT_NAME = "default"   # the name of an asset's first skeleton and first look (RigModules D54)


class AssetContext:
    """The asset id and the chosen skeleton, rig and look. changed emits with no arguments after any of them changes."""

    _instance: ClassVar[AssetContext | None] = None

    def __init__(self, root: str | None = None) -> None:
        """root is the projects root the asset id is relative to: the environment's when left out."""
        self.changed = Event()
        self.root = root
        self.asset_id: str | None = None
        self.skeleton: str | None = None
        self.rig: str | None = None
        self.look: str | None = None

    @classmethod
    def current(cls) -> AssetContext | None:
        """The running context, or None when the Asset Editor is not open."""
        return cls._instance

    @classmethod
    def start(cls, asset_id: str | None = None, root: str | None = None) -> AssetContext:
        """Makes a new running context, replacing any earlier one, and sets its asset when asset_id is given."""
        context = cls(root)
        cls._instance = context
        if asset_id:
            context.set_asset(asset_id)
        return context

    def stop(self) -> None:
        """Clears the context and ends it: current() is None afterwards, when this was the running one."""
        self.asset_id = self.skeleton = self.rig = self.look = None
        if AssetContext._instance is self:
            AssetContext._instance = None
        self.changed.emit()

    @property
    def asset(self) -> Asset | None:
        """The asset, or None when no id is set. It may not exist on disk: check exists()."""
        if self.asset_id is None:
            return None
        return Asset(self.asset_id, self.root)

    def skeletons(self) -> list[str]:
        return self._owners("skeletons")

    def rigs(self) -> list[str]:
        return self._owners("rigs")

    def looks(self) -> list[str]:
        return self._owners("looks")

    def set_asset(self, asset_id: str | None) -> None:
        """Sets the asset, and picks its first skeleton, rig and look ("default" first for a skeleton and a look). An
        id that is not valid raises AssetIdError, and nothing changes. An asset with no folder yet is allowed: the
        owners are then empty."""
        if asset_id is not None:
            asset_id = assetid.check(asset_id)
        if asset_id == self.asset_id:
            return
        self.asset_id = asset_id
        self.skeleton = self._first(self.skeletons())
        self.rig = self._first(self.rigs(), prefer="")
        self.look = self._first(self.looks())
        self.changed.emit()

    def set_skeleton(self, name: str | None) -> None:
        self._set("skeleton", name, self.skeletons())

    def set_rig(self, name: str | None) -> None:
        self._set("rig", name, self.rigs())

    def set_look(self, name: str | None) -> None:
        self._set("look", name, self.looks())

    def refresh(self) -> None:
        """Reads the owners again, after a file was created or removed: a chosen one that is gone is replaced by the
        first that is left, and one chosen while none existed is picked when the first appears."""
        before = (self.skeleton, self.rig, self.look)
        for attribute, names, prefer in (("skeleton", self.skeletons(), DEFAULT_NAME), ("rig", self.rigs(), ""),
                                         ("look", self.looks(), DEFAULT_NAME)):
            if getattr(self, attribute) not in names:
                setattr(self, attribute, self._first(names, prefer))
        if (self.skeleton, self.rig, self.look) != before:
            self.changed.emit()

    def _set(self, attribute: str, name: str | None, names: list[str]) -> None:
        if name is not None and name not in names:
            raise AssetError(f"{self.asset_id} has no {attribute} {name!r}. It has: {', '.join(names) or 'none'}.")
        if getattr(self, attribute) != name:
            setattr(self, attribute, name)
            self.changed.emit()

    def _owners(self, parent: str) -> list[str]:
        """The names of the skeletons, rigs or looks of the asset, or none when there is no asset or it has no
        folder or project yet."""
        asset = self.asset
        if asset is None or not asset.exists():
            return []
        try:
            return {"skeletons": asset.skeletons, "rigs": asset.rigs, "looks": asset.looks}[parent]
        except (ProjectError, OSError):
            return []

    @staticmethod
    def _first(names: list[str], prefer: str = DEFAULT_NAME) -> str | None:
        if prefer and prefer in names:
            return prefer
        return names[0] if names else None


def exists(asset_id: str, root: str | None = None) -> bool:
    """Whether the asset id is valid and its asset.json is on disk. False, never an error, when there is no
    projects root."""
    try:
        return Asset(asset_id, root).exists()
    except (assetid.AssetIdError, ProjectError):
        return False


__all__ = ["AssetContext", "DEFAULT_NAME", "exists"]
