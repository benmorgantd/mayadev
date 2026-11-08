"""Local version copies: before a save overwrites a file, the old one is copied outside the workspace.

    <projects root>\\shooter\\main\\characters\\hero\\variants\\game\\shapes.json
    ->  <versions root>\\shooter\\main\\characters\\hero\\variants\\game\\shapes.v007.json

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
