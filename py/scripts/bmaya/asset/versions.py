"""Local version copies: before a save overwrites a file, the old one is copied to versions/ beside it.

    variants/game/shapes.json  ->  variants/game/versions/shapes.v007.json
    variants/game/weights/     ->  variants/game/versions/weights.v003/

This is the undo for a save between source control submits, and the only one without source control.
The next number is the highest existing number plus one, so deleting an old copy never reuses a number.
"""

from __future__ import annotations

import os
import re
import shutil

VERSIONS_FOLDER = "versions"


def versions_folder(path: str) -> str:
    return os.path.join(os.path.dirname(os.path.normpath(path)), VERSIONS_FOLDER)


def _split(path: str) -> tuple[str, str]:
    """(stem, extension). A folder has no extension."""
    base = os.path.basename(os.path.normpath(path))
    if os.path.isdir(path):
        return base, ""
    stem, extension = os.path.splitext(base)
    return stem, extension


def list_versions(path: str) -> list[tuple[int, str]]:
    """(number, path) of every version copy of path, oldest first."""
    folder = versions_folder(path)
    if not os.path.isdir(folder):
        return []
    stem, extension = _split(path)
    pattern = re.compile(re.escape(stem) + r"\.v(\d+)" + re.escape(extension) + "$")
    found = []
    for entry in os.listdir(folder):
        match = pattern.match(entry)
        if match:
            found.append((int(match.group(1)), os.path.join(folder, entry)))
    return sorted(found)


def version(path: str) -> str | None:
    """Copies path into its versions folder and returns the copy, or None when there's nothing to copy yet."""
    if not os.path.exists(path):
        return None
    existing = list_versions(path)
    number = existing[-1][0] + 1 if existing else 1
    stem, extension = _split(path)
    folder = versions_folder(path)
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, f"{stem}.v{number:03d}{extension}")
    if os.path.isdir(path):
        shutil.copytree(path, target)
    else:
        shutil.copy2(path, target)
    return target
