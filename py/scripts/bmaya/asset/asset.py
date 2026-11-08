"""Assets: a folder below the projects root that holds an asset.json.

asset.json is the source of truth for one asset. Its id is not stored: it is the folder's path, so a
copied or moved folder can't carry a stale id. Reading paths never touches the disk. Folders are made
only when something is written.
"""

from __future__ import annotations

import os

from . import assetid
from .project import Project, ProjectError, projects_root, read_json, write_json

ASSET_FILE = "asset.json"
FORMAT_VERSION = 1


class AssetError(RuntimeError):
    """An asset that doesn't exist, already exists, or would break the layout rules."""


class Asset:
    def __init__(self, asset_id: str, root: str | None = None):
        self.id = assetid.check(asset_id)
        self.root = os.path.normpath(root) if root else projects_root()
        self.folder = os.path.join(self.root, assetid.to_relative_path(asset_id))
        self._project: Project | None = None

    def __repr__(self) -> str:
        return f"Asset({self.id!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Asset) and assetid.equals(self.id, other.id) and self.root == other.root

    def __hash__(self) -> int:
        return hash((assetid.key(self.id), self.root))

    @property
    def name(self) -> str:
        return assetid.name(self.id)

    @property
    def info_path(self) -> str:
        return os.path.join(self.folder, ASSET_FILE)

    @property
    def project(self) -> Project:
        if self._project is None:
            self._project = Project.find(self.folder)
        return self._project

    def exists(self) -> bool:
        return os.path.isfile(self.info_path)

    @property
    def info(self) -> dict:
        """The parsed asset.json. Read each time, so it never goes stale."""
        if not self.exists():
            raise AssetError(f"{self.id} has no {ASSET_FILE} at {self.folder}.")
        data = read_json(self.info_path)
        if data.get("formatVersion") != FORMAT_VERSION:
            raise AssetError(f"{self.info_path}: formatVersion {data.get('formatVersion')!r} is not {FORMAT_VERSION}.")
        return data

    @property
    def asset_type(self) -> str:
        return self.info["assetType"]

    @property
    def rigs(self) -> list[str]:
        return list(self.info.get("rigs", []))

    @property
    def skeleton(self) -> str:
        """The id of the asset whose skeleton this asset uses: its own id unless asset.json names another.
        Assets with the same skeleton can share poses and animations."""
        return self.info.get("skeleton") or self.id

    def latest_publish(self, variant: str) -> int:
        """The latest publish of a variant, 0 when it was never published."""
        return int(self.info.get("publishes", {}).get(variant, 0))

    def path(self, file_type: str, variant: str | None = None) -> str:
        """Where a file type lives for this asset. Pure: never checks or creates anything."""
        relative = self.project.file_type(file_type).relative_path(self.name, variant)
        return os.path.join(self.folder, relative)

    def file_exists(self, file_type: str, variant: str | None = None) -> bool:
        return os.path.exists(self.path(file_type, variant))

    # ---- writes ----------------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        asset_id: str,
        asset_type: str,
        skeleton: str | None = None,
        rigs: tuple[str, ...] | list[str] = (),
        root: str | None = None,
    ) -> "Asset":
        """Makes the asset folder and its asset.json, and adds it to the project registry."""
        asset = cls(asset_id, root)
        if asset.exists():
            raise AssetError(f"{asset.id} already exists at {asset.folder}.")
        project = asset.project
        project.check_asset_type(asset_type)
        _check_not_nested(asset, project)

        data = {"formatVersion": FORMAT_VERSION, "assetType": asset_type, "rigs": []}
        if skeleton is not None:
            data["skeleton"] = assetid.check(skeleton)
        for variant in rigs:
            _add_variant(data, variant)

        os.makedirs(asset.folder, exist_ok=True)
        asset._write_info(data)
        return asset

    @classmethod
    def from_path(cls, path: str, root: str | None = None) -> "Asset":
        """The asset a file or folder belongs to: the nearest folder at or above it with an asset.json."""
        root = os.path.normpath(root) if root else projects_root()
        folder = os.path.normpath(os.path.abspath(path))
        while True:
            if os.path.isfile(os.path.join(folder, ASSET_FILE)):
                return cls(assetid.from_relative_path(os.path.relpath(folder, root)), root)
            parent = os.path.dirname(folder)
            if parent == folder or os.path.normcase(folder) == os.path.normcase(root):
                raise AssetError(f"{path} is not inside an asset below {root}.")
            folder = parent

    def add_rig(self, variant: str) -> None:
        data = self.info
        _add_variant(data, variant)
        self._write_info(data)

    def record_publish(self, variant: str, version: int) -> None:
        """Records a variant's latest publish. Called by the publish step, which also stamps the rig root."""
        if variant not in self.rigs:
            raise AssetError(f"{self.id} has no rig variant {variant!r}. Known: {self.rigs}.")
        if version <= self.latest_publish(variant):
            raise AssetError(f"{self.id} {variant}: publish {version} is not newer than {self.latest_publish(variant)}.")
        data = self.info
        data.setdefault("publishes", {})[variant] = int(version)
        self._write_info(data)

    def _write_info(self, data: dict) -> None:
        write_json(self.info_path, data)
        from .registry import Registry  # registry imports Asset

        Registry(self.project, self.root).update(self)


def _add_variant(data: dict, variant: str) -> None:
    if not assetid.is_valid_token(variant):
        raise AssetError(f"Variant {variant!r} must be letters, digits and '_'.")
    if variant in data["rigs"]:
        raise AssetError(f"Variant {variant!r} already exists.")
    data["rigs"].append(variant)


def _check_not_nested(asset: Asset, project: Project) -> None:
    """Assets never nest, so a folder is an asset or holds assets, never both."""
    if os.path.normcase(asset.folder) == os.path.normcase(project.root):
        raise AssetError(f"{asset.id} can't be its own project folder {project.root}.")
    folder = os.path.dirname(asset.folder)
    while os.path.normcase(folder) != os.path.normcase(project.root):
        if os.path.isfile(os.path.join(folder, ASSET_FILE)):
            raise AssetError(f"{asset.id} would sit inside the asset at {folder}.")
        parent = os.path.dirname(folder)
        if parent == folder:
            raise ProjectError(f"{asset.folder} is not below its project {project.root}.")
        folder = parent
    if os.path.isdir(asset.folder):
        for current, _dirs, files in os.walk(asset.folder):
            if ASSET_FILE in files:
                raise AssetError(f"{asset.id} would hold the asset at {current}.")
