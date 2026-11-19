"""Every asset id below the projects root, for a picker (RigModules design/asset-editor.md, D61).

The projects root holds one folder tree per game, and a folder with a project.json is a project. The registry scan
(bmaya.core.asset.registry) lists the assets of one project, and this finds the projects. Only the workspace on disk is
read, so an asset that exists in source control and is not synced is not listed. No Maya.
"""

from __future__ import annotations

import os

import bmaya.core.log
from bmaya.core.asset import assetid
from bmaya.core.asset.project import PROJECT_FILE, Project, ProjectError, projects_root
from bmaya.core.asset.registry import Registry


def project_folders(root: str | None = None) -> list[str]:
    """The folders below root that hold a project.json, sorted. The scan stops at a project, and skips the reserved
    `user` folder at the top of the root. root is the projects root when left out. A root that isn't a folder gives
    none."""
    root = os.path.normpath(root) if root else projects_root()
    found: list[str] = []
    pending = [root]
    while pending:
        folder = pending.pop()
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        if any(entry.name == PROJECT_FILE and entry.is_file() for entry in entries):
            found.append(folder)
            continue
        for entry in entries:
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if folder == root and entry.name == assetid.RESERVED_ROOT:
                continue
            pending.append(entry.path)
    return sorted(found, key=os.path.normcase)


def asset_ids(root: str | None = None) -> list[str]:
    """The id of every asset in every project below root, sorted. A project that can't be read, or an asset whose
    files can't, is logged as a warning and left out."""
    root = os.path.normpath(root) if root else projects_root()
    ids: set[str] = set()
    for folder in project_folders(root):
        try:
            registry = Registry(Project(folder), root).refresh()
        except ProjectError as error:
            bmaya.core.log.warning(f"The asset list skipped the project at {folder}: {error}")
            continue
        for error in registry.errors:
            bmaya.core.log.warning(f"The asset list skipped an asset: {error}")
        ids.update(registry.ids())
    return sorted(ids, key=str.lower)
