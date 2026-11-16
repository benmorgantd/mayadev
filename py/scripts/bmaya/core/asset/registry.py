"""The project registry: an index of every asset in a project, built by scanning the workspace.

It answers questions about many assets without opening Maya: assets of a type, assets sharing a
skeleton (whose poses and animations can be shared, and which need a batch update when that skeleton
changes), and the latest publish of each variant (for the out-of-date check on imported rigs).

The index lives in memory and is never written anywhere, so it is never checked out, submitted or
merged, and every workspace (every branch) indexes the files it actually has. Registry.of(project)
returns one shared index per project per session. refresh() rescans after files change on disk.

The scan stops at each asset folder, so texture and weight folders are never walked. That's also why
nesting is checked when an asset is created rather than here.
"""

from __future__ import annotations

import os

from . import assetid, publishes
from .asset import ASSET_FILE, Asset
from .project import PROJECT_FILE, Project, ProjectError, projects_root

_SHARED: dict[tuple[str, str], "Registry"] = {}


class Registry:
    def __init__(self, project: Project, root: str | None = None):
        """root is the projects root the asset ids are relative to. RIGGING_PROJECT_DIR when left out."""
        self.project = project
        self.root = os.path.normpath(root) if root else projects_root()
        self._assets: dict[str, dict] | None = None
        self._errors: list[str] = []

    def __repr__(self) -> str:
        return f"Registry({self.project.root!r})"

    @classmethod
    def of(cls, project: Project, root: str | None = None) -> "Registry":
        """The session's shared index of a project, scanned on first use."""
        registry = cls(project, root)
        key = (os.path.normcase(project.root), os.path.normcase(registry.root))
        return _SHARED.setdefault(key, registry)

    # ---- reads -----------------------------------------------------------------------------

    @property
    def assets(self) -> dict[str, dict]:
        if self._assets is None:
            self.refresh()
        return self._assets

    @property
    def errors(self) -> list[str]:
        """Problems the last scan found: folders whose path is not a valid id, and unreadable asset.json files."""
        self.assets
        return list(self._errors)

    def ids(self) -> list[str]:
        return sorted(self.assets)

    def get(self, asset_id: str) -> dict | None:
        entry = self.assets.get(assetid.check(asset_id))
        return dict(entry) if entry is not None else None

    def find(self, asset_type: str | None = None, skeleton: str | None = None) -> list[str]:
        """Ids matching every filter given. skeleton matches the asset that owns it and every asset using it."""
        result = []
        for asset_id, entry in self.assets.items():
            if asset_type is not None and entry["assetType"] != asset_type:
                continue
            if skeleton is not None and entry["skeleton"] != skeleton:
                continue
            result.append(asset_id)
        return sorted(result)

    def latest_publish(self, asset_id: str, variant: str) -> str | None:
        """The id of a variant's latest publish, or None when it was never published."""
        entry = self.get(asset_id)
        if entry is None:
            raise ProjectError(f"{asset_id} is not in the project at {self.project.root}.")
        return entry["latestPublish"].get(variant)

    # ---- scan ------------------------------------------------------------------------------

    def refresh(self) -> "Registry":
        """Rescans the project's folders for assets."""
        assets: dict[str, dict] = {}
        errors: list[str] = []
        for folder in self._asset_folders():
            try:
                asset = Asset(assetid.from_relative_path(os.path.relpath(folder, self.root)), self.root)
                assets[asset.id] = _entry(asset)
            except (assetid.AssetIdError, ProjectError, RuntimeError, KeyError) as error:
                errors.append(f"{folder}: {error}")
        self._assets, self._errors = assets, errors
        return self

    def _asset_folders(self):
        """Every folder with an asset.json, without descending into assets or other projects."""
        pending = [self.project.root]
        while pending:
            folder = pending.pop()
            try:
                entries = list(os.scandir(folder))
            except OSError:
                continue
            if folder != self.project.root and any(e.name == ASSET_FILE and e.is_file() for e in entries):
                yield folder
                continue
            for entry in entries:
                if entry.is_dir() and not os.path.isfile(os.path.join(entry.path, PROJECT_FILE))                         and not self._is_user_folder(entry.path):
                    pending.append(entry.path)

    def _is_user_folder(self, folder: str) -> bool:
        """The projects root's top-level "user" folder: each user's own library files, never assets (assetid.RESERVED_ROOT)."""
        return os.path.normcase(folder) == os.path.normcase(os.path.join(self.root, assetid.RESERVED_ROOT))


def _entry(asset: Asset) -> dict:
    info = asset.info
    variants = asset.variants
    return {
        "assetType": info["assetType"],
        "skeleton": info.get("skeleton") or asset.id,
        "variants": variants,
        "latestPublish": {v: p for v in variants if (p := publishes.latest(asset, v))},
    }

