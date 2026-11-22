"""Local version copies: before a save overwrites a file, the old one is copied outside the workspace.

    <projects root>\\shooter\\main\\characters\\hero\\rigs\\body\\shapes.json
    ->  <versions root>\\shooter\\main\\characters\\hero\\rigs\\body\\shapes.v007.json

This is the undo for a save between source control submits, and the only one without source control.
The copies are private to the machine and never submitted, so they stay out of the depot.

The versions root is BMAYA_VERSIONS_DIR, or %LOCALAPPDATA%\\bmaya\\versions when it isn't set. Point
BMAYA_VERSIONS_DIR at a synced folder to keep the copies with the files on a synced drive.

The next number is the highest existing number plus one, so deleting an old copy never reuses a number.
A folder (weights) is copied whole: weights.v003\\.
"""

from __future__ import annotations

import os
import re
import shutil

VERSIONS_DIR_ENV = "BMAYA_VERSIONS_DIR"


def versions_root() -> str:
    configured = os.environ.get(VERSIONS_DIR_ENV)
    if configured:
        return os.path.normpath(configured)
    local = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(local, "bmaya", "versions")


def versions_folder(path: str, root: str) -> str:
    """Where the copies of path go: its folder's place below root, mirrored under the versions root."""
    folder = os.path.dirname(os.path.normpath(os.path.abspath(path)))
    relative = os.path.relpath(folder, root)
    if relative == os.curdir:
        relative = ""
    elif relative.startswith(os.pardir):
        raise ValueError(f"{path} is not below {root}.")
    return os.path.join(versions_root(), relative)


def _split(path: str) -> tuple[str, str]:
    """(stem, extension). A folder has no extension."""
    base = os.path.basename(os.path.normpath(path))
    if os.path.isdir(path):
        return base, ""
    stem, extension = os.path.splitext(base)
    return stem, extension


def list_versions(path: str, root: str) -> list[tuple[int, str]]:
    """(number, path) of every version copy of path, oldest first. root is the projects root."""
    folder = versions_folder(path, root)
    if not os.path.isdir(folder):
        return []
    stem, extension = _split(path)
    pattern = re.compile(re.escape(stem) + r"\.v(\d+)" + re.escape(extension))
    found = []
    for entry in os.listdir(folder):
        match = pattern.fullmatch(entry)
        if match:
            found.append((int(match.group(1)), os.path.join(folder, entry)))
    return sorted(found)


def version(path: str, root: str) -> str | None:
    """Copies path to its versions folder and returns the copy, or None when there's nothing to copy yet."""
    if not os.path.exists(path):
        return None
    existing = list_versions(path, root)
    number = existing[-1][0] + 1 if existing else 1
    stem, extension = _split(path)
    folder = versions_folder(path, root)
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, f"{stem}.v{number:03d}{extension}")
    if os.path.isdir(path):
        shutil.copytree(path, target)
    else:
        shutil.copy2(path, target)
    return target


def version_if_changed(path: str, root: str) -> str | None:
    """version(), unless path is a file that is byte for byte the newest copy already. Returns the new copy, or None
    when there was nothing to copy or nothing new. For a file about to be edited by hand, so its state before the edit
    is kept without a copy for every look at it."""
    existing = list_versions(path, root)
    if existing and os.path.isfile(path) and os.path.isfile(existing[-1][1]):
        with open(path, "rb") as current, open(existing[-1][1], "rb") as newest:
            if current.read() == newest.read():   # not filecmp: it caches by size and time, which an edit can keep
                return None
    return version(path, root)


def find_version(path: str, root: str, number: int) -> str:
    """The copy that is version number of path. Raises ValueError for a number path has no copy of, naming the ones it
    has."""
    copies = dict(list_versions(path, root))
    if number not in copies:
        have = ", ".join(str(found) for found in copies) or "none"
        raise ValueError(f"{os.path.basename(os.path.normpath(path))} has no local version {number}. It has: {have}.")
    return copies[number]


def restore(path: str, root: str, number: int) -> str:
    """Copies version number of path back over path, replacing it, and returns path. A folder is replaced whole. The
    restored file is dated now, like a save, not by the copy it came from. Keep a version of path first (version())
    when it should survive. Raises ValueError as find_version does."""
    source = find_version(path, root, number)
    if os.path.isdir(source):
        if os.path.isdir(path):
            shutil.rmtree(path)
        shutil.copytree(source, path, copy_function=shutil.copy)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        shutil.copy(source, path)
    return path
