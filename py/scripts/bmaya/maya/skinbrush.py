"""The skin brush's settings: the view-model of the brush settings panel, and the one place that makes and activates
the RigModules skin brush context (RigModules D65).

No Qt. The context holds the settings: radius, strength, the operation and through mesh. This reads them with
`cmds.skinBrushCtx(query=True)` and writes them with `edit=True`, so a Ctrl + drag resize in the viewport shows in a
panel that calls `refresh`. Maya creates no contexts without a GUI, so everything here raises in batch.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import maya.cmds as cmds

import bmaya.core.observable

CONTEXT_NAME = "rigmodulesSkinBrushCtx"
# The operations RigModules' skinBrushCtx accepts (its brushOperationNames). Add a name here when it adds a brush.
FALLOFFS = ("surface", "volume")   # how the radius is measured: along the mesh, or in space
OPERATIONS = ("smooth",)
MIN_RADIUS = 0.001


@dataclasses.dataclass(frozen=True)
class BrushSettings:
    """What the context holds. radius is a length over the mesh surface (with the surface falloff), strength is above 0 and at most 1."""

    operation: str
    radius: float
    strength: float
    falloff: str
    through_mesh: bool


class SkinBrushSession:
    """Reads and writes the brush context's settings, and makes it the active tool. commands is `maya.cmds`, or
    anything with its `about`, `contextInfo`, `skinBrushCtx` and `setToolTo`, which is how the tests run it."""

    def __init__(self, commands: Any = cmds) -> None:
        self.commands = commands
        self.changed = bmaya.core.observable.Event()
        self.settings: BrushSettings | None = None
        self.refresh()

    def exists(self) -> bool:
        return bool(self.commands.contextInfo(CONTEXT_NAME, exists=True))

    def ensure_context(self) -> str:
        """Makes the context the first time and keeps it, so the radius and strength a user set stay. Raises in batch."""
        if self.commands.about(batch=True):
            raise RuntimeError("The skin brush needs a GUI Maya: Maya creates no tool contexts in batch.")
        if not self.exists():
            self.commands.skinBrushCtx(CONTEXT_NAME)
        return CONTEXT_NAME

    def refresh(self) -> None:
        """Reads the settings again, and emits changed when they differ from the last read. None until the context
        exists."""
        settings = self._read() if self.exists() else None
        if settings != self.settings:
            self.settings = settings
            self.changed.emit()

    def apply(self, *, operation: str | None = None, radius: float | None = None, strength: float | None = None,
              falloff: str | None = None, through_mesh: bool | None = None) -> BrushSettings:
        """Writes the settings that are given, making the context first. Raises ValueError for one that is not valid
        and RuntimeError when Maya refuses it, leaving the old value."""
        if operation is not None and operation not in OPERATIONS:
            raise ValueError(f"{operation} is not a brush operation: {', '.join(OPERATIONS)}.")
        if falloff is not None and falloff not in FALLOFFS:
            raise ValueError(f"{falloff} is not a falloff: {', '.join(FALLOFFS)}.")
        if radius is not None and radius < MIN_RADIUS:
            raise ValueError(f"The brush radius must be at least {MIN_RADIUS}.")
        if strength is not None and not 0.0 < strength <= 1.0:
            raise ValueError("The brush strength must be above 0 and at most 1.")
        name = self.ensure_context()
        changes = {"operation": operation, "radius": radius, "strength": strength, "falloff": falloff,
                   "throughMesh": through_mesh}
        changes = {key: value for key, value in changes.items() if value is not None}
        if changes:
            self.commands.skinBrushCtx(name, edit=True, **changes)
        self.refresh()
        return self.settings

    def activate(self) -> str:
        """Makes the brush the active tool and returns the context's name."""
        name = self.ensure_context()
        self.commands.setToolTo(name)
        self.refresh()
        return name

    def _read(self) -> BrushSettings:
        query = self.commands.skinBrushCtx
        return BrushSettings(operation=query(CONTEXT_NAME, query=True, operation=True),
                             radius=query(CONTEXT_NAME, query=True, radius=True),
                             strength=query(CONTEXT_NAME, query=True, strength=True),
                             falloff=query(CONTEXT_NAME, query=True, falloff=True),
                             through_mesh=bool(query(CONTEXT_NAME, query=True, throughMesh=True)))
