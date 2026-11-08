"""The project registry: registry.json next to project.json, a cache of every asset.json in the project.

It answers questions about many assets without walking the disk or opening Maya: assets of a type,
assets sharing a skeleton (whose poses and animations can be shared, and which need a batch update when
that skeleton changes), and the latest publish of a variant (for the out-of-date check on imported rigs).

asset.json files stay the source of truth. rebuild() regenerates the whole cache, and every write
through Asset updates that asset's entry.
"""

from __future__ import annotations

import os

from . import assetid
from .asset import ASSET_FILE, Asset
from .project import PROJECT_FILE, Project, ProjectError, projects_root, read_json, write_json

REGISTRY_FILE = "registry.json"
FORMAT_VERSION = 1


class Registry:
    def __init__(self, project: Project, root: str | None = None):
        """root is the projects root the asset ids are relative to. RIGGING_PROJECT_DIR when left out."""
        self.project = project
        self.root = os.path.normpath(root) if root else projects_root()
        self.path = os.path.join(project.root, REGISTRY_FILE)
        self._data: dict | None = None

    def __repr__(self) -> str:
        return f"Registry({self.path!r})"

    # ---- reads -----------------------------------------------------------------------------

    @property
    def data(self) -> dict:
        if self._data is None:
            if not os.path.isfile(self.path):
                return self.rebuild().data
            data = read_json(self.path)
            if data.get("formatVersion") != FORMAT_VERSION:
                return self.rebuild().data
            self._data = data
        return self._data

    @property
    def errors(self) -> list[str]:
        """Problems the last rebuild found: nested assets, ids that differ only in case, unreadable files."""
        return list(self.data.get("errors", []))

    def ids(self) -> list[str]:
        return sorted(self.data["assets"], key=str.casefold)

    def get(self, asset_id: str) -> dict | None:
        found = self._find_id(asset_id)
        return dict(self.data["assets"][found]) if found else None

    def find(self, asset_type: str | None = None, skeleton: str | None = None) -> list[str]:
        """Ids matching every filter given. skeleton matches the asset that owns it and every asset using it."""
        result = []
        for asset_id, entry in self.data["assets"].items():
            if asset_type is not None and entry["assetType"] != asset_type:
                continue
            if skeleton is not None and not assetid.equals(entry["skeleton"], skeleton):
                continue
            result.append(asset_id)
        return sorted(result, key=str.casefold)

    def latest_publish(self, asset_id: str, variant: str) -> int:
        entry = self.get(asset_id)
        if entry is None:
            raise ProjectError(f"{asset_id} is not in {self.path}.")
        return int(entry["publishes"].get(variant, 0))

    # ---- writes ----------------------------------------------------------------------------

    def rebuild(self) -> "Registry":
        """Walks the project for asset.json files and rewrites registry.json from them."""
        assets: dict[str, dict] = {}
        errors: list[str] = []
        for folder, dirs, files in os.walk(self.project.root):
            # A folder with its own project.json is another project.
            dirs[:] = sorted(d for d in dirs if not os.path.isfile(os.path.join(folder, d, PROJECT_FILE)))
            if ASSET_FILE not in files:
                continue
            try:
                asset = Asset(assetid.from_relative_path(os.path.relpath(folder, self.root)), self.root)
                outer = self._enclosing_asset(folder)
                if outer:
                    errors.append(f"{asset.id}: inside the asset at {outer}. Assets never nest.")
                    continue
                duplicate = _find_key(assets, asset.id)
                if duplicate:
                    errors.append(f"{asset.id}: differs from {duplicate} only in case.")
                    continue
                assets[asset.id] = self._entry(asset)
            except (assetid.AssetIdError, ProjectError, RuntimeError, KeyError) as error:
                errors.append(f"{folder}: {error}")
        self._save({"formatVersion": FORMAT_VERSION, "assets": assets, "errors": errors})
        return self

    def update(self, asset: Asset) -> None:
        """Refreshes one asset's entry from its asset.json."""
        if self._data is None and not os.path.isfile(self.path):
            self.rebuild()
            return
        data = self.data
        stale = self._find_id(asset.id)
        if stale:
            del data["assets"][stale]
        data["assets"][asset.id] = self._entry(asset)
        self._save(data)

    # ---- helpers ---------------------------------------------------------------------------

    def _entry(self, asset: Asset) -> dict:
        info = asset.info
        return {
            "assetType": info["assetType"],
            "skeleton": info.get("skeleton") or asset.id,
            "rigs": list(info.get("rigs", [])),
            "publishes": dict(info.get("publishes", {})),
            "files": self._existing_files(asset, info.get("rigs", [])),
        }

    def _existing_files(self, asset: Asset, variants: list[str]) -> list[str]:
        """Every file type path that exists, relative to the asset folder, with '/' separators."""
        found = []
        for file_type in self.project.file_types.values():
            for variant in variants if file_type.per_variant else [None]:
                relative = file_type.relative_path(asset.name, variant)
                if os.path.exists(os.path.join(asset.folder, relative)):
                    found.append(relative.replace(os.sep, "/"))
        return sorted(found)

    def _enclosing_asset(self, folder: str) -> str | None:
        parent = os.path.dirname(folder)
        while os.path.normcase(parent) != os.path.normcase(self.project.root):
            if os.path.isfile(os.path.join(parent, ASSET_FILE)):
                return parent
            parent = os.path.dirname(parent)
        return None

    def _find_id(self, asset_id: str) -> str | None:
        return _find_key(self.data["assets"], asset_id)

    def _save(self, data: dict) -> None:
        write_json(self.path, data)
        self._data = data


def _find_key(assets: dict, asset_id: str) -> str | None:
    wanted = assetid.key(asset_id)
    for existing in assets:
        if assetid.key(existing) == wanted:
            return existing
    return None
