"""Source control for asset writes, behind one small interface.

Under Perforce, workspace files are read-only until checked out, and new files need an add. Asset code
calls checkout() before it overwrites a file and add() after it writes a new one. The default does
nothing, so saves work the same with no source control. A Perforce adapter (P4Python or the p4 command
line) can be set with set_current() later without touching the asset code.

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


_current: SourceControl = SourceControl()


def current() -> SourceControl:
    return _current


def set_current(adapter: SourceControl) -> None:
    global _current
    _current = adapter
