"""Source control for asset writes, behind one small interface.

Under Perforce, workspace files are read-only until checked out, and new files need an add. Asset code
calls checkout() before it overwrites a file and add() after it writes a new one. The default does
nothing, so saves work the same with no source control. A Perforce adapter (P4Python or the p4 command
line) can be set with set_current() later without touching the asset code.

list_folders() and sync() are for folders that exist in the depot but not in the workspace (RigModules D54 phase 6):
an asset lists its looks without syncing them all, and syncs one when it is chosen.

path is a file or a folder. For a folder file type (weights, textures) the adapter handles everything
under it: in Perforce terms, <folder>/...
"""

from __future__ import annotations


class SourceControl:
    """No source control: every call does nothing."""

    def checkout(self, path: str) -> None:
        """Make an existing path writable for editing."""

    def add(self, path: str) -> None:
        """Mark a newly written path for adding."""

    def list_folders(self, path: str) -> list[str] | None:
        """The names of the folders directly under path, whether or not they are synced to the workspace. None means
        this adapter can't tell and the caller scans the disk, which is what the default does. May raise when the
        server can't be reached: the caller falls back to the disk scan."""
        return None

    def sync(self, path: str) -> None:
        """Brings a folder (everything under it) into the workspace. Raises when it can't."""


_current: SourceControl = SourceControl()


def current() -> SourceControl:
    return _current


def set_current(adapter: SourceControl) -> None:
    global _current
    _current = adapter
