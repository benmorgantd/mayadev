"""Assets: a folder below the projects root that holds an asset.json.

asset.json holds only what a person decides about the asset: its type. It changes rarely, so under Perforce
it is rarely checked out. Everything else is found on disk (RigModules D54): skeletons are the folders that hold
a skeleton.json, rigs the folders that hold a rig.json, looks the folders that hold a look.json, and publishes are
folders that are only ever added. Adding any of them adds files and edits nothing shared.
The id is not stored either: it is the folder's path, so a copied or moved folder can't carry a stale
id. Reading paths never touches the disk. Folders are made only when something is written.

    hero = Asset("shooter\\main\\characters\\hero")
    hero.skeletons, hero.rigs, hero.looks        # ["default"], ["body", "body_cine"], ["default", "winter"]
    hero.path("shapes", "body")                  # rigs/body/shapes.json
    hero.path("weights", "winter")               # looks/winter/weights
    hero.skeleton_of("body")                     # (the asset that holds the rig's skeleton, "default")
"""

from __future__ import annotations

import os
import typing

import bmaya.core.log

from . import assetid, records, sourcecontrol
from .project import Project, ProjectError, projects_root, read_json, write_json
from .records import LookRecord, RigRecord, RigRef, SkeletonRef

ASSET_FILE = "asset.json"
FORMAT_VERSION = 2


class AssetError(RuntimeError):
    """An asset that doesn't exist, already exists, or would break the layout rules."""


class AssetLook(typing.NamedTuple):
    """A look of an asset and whether its files are in the workspace. A look that is not local is only a name: its
    look.json can't be read until it is synced."""
    name: str
    local: bool


class Asset:
    def __init__(self, asset_id: str, root: str | None = None):
        self.id = assetid.check(asset_id)
        self.root = os.path.normpath(root) if root else projects_root()
        self.folder = os.path.join(self.root, assetid.to_relative_path(asset_id))
        self._project: Project | None = None

    def __repr__(self) -> str:
        return f"Asset({self.id!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Asset) and self.id == other.id and self.root == other.root

    def __hash__(self) -> int:
        return hash((self.id, self.root))

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
        return _read_info(self.info_path)

    @property
    def asset_type(self) -> str:
        return self.info["assetType"]

    @property
    def skeletons(self) -> list[str]:
        """The skeletons: folders that hold a skeleton.json, the only form a skeleton is stored in."""
        return self._owners("skeleton")

    @property
    def rigs(self) -> list[str]:
        """The rigs: folders that hold a rig.json. Adding a rig adds files and edits nothing."""
        return self._owners("riginfo")

    @property
    def looks(self) -> list[str]:
        """The looks: folders that hold a look.json. A look-only asset has looks and no skeletons or rigs."""
        return self._owners("lookinfo")

    def all_looks(self) -> list[AssetLook]:
        """Every look of the asset, sorted by name, including those that exist in source control but are not synced
        (local False). With no source control, or when it fails (a warning is logged), it is the local scan:
        everything in `looks`, all local. looks stays the local scan, so a caller that reads a look's files can't
        be handed one that isn't there."""
        local = self.looks
        remote: list[str] | None = None
        parent = os.path.join(self.folder, self.project.file_type("lookinfo").owner_parent())
        try:
            remote = sourcecontrol.current().list_folders(parent)
        except Exception as error:   # a server that is down must not empty the library
            bmaya.core.log.warning(f"Source control could not list the looks of {self.id}, so only the synced ones are "
                                   f"shown: {error}")
        names = set(local) | {name for name in remote or () if assetid.is_valid_token(name)}
        return [AssetLook(name, name in local) for name in sorted(names)]

    def sync_look(self, name: str) -> None:
        """Brings a look that is not local into the workspace. Does nothing for a local look. Raises AssetError when
        source control can't sync it or the folder holds no look.json afterwards."""
        if not assetid.is_valid_token(name):
            raise AssetError(f"{name!r} is not a look name.")
        if self.file_exists("lookinfo", name):
            return
        folder = os.path.dirname(self.path("lookinfo", name))
        try:
            sourcecontrol.current().sync(folder)
        except Exception as error:
            raise AssetError(f"Could not sync the look {name!r} of {self.id}: {error}") from error
        if not self.file_exists("lookinfo", name):
            raise AssetError(f"The look {name!r} of {self.id} has no look.json after syncing {folder}.")

    def _owners(self, file_type: str) -> list[str]:
        parent = os.path.join(self.folder, self.project.file_type(file_type).owner_parent())
        if not os.path.isdir(parent):
            return []
        return sorted(
            entry.name for entry in os.scandir(parent)
            if entry.is_dir() and assetid.is_valid_token(entry.name) and self.file_exists(file_type, entry.name))

    def path(self, file_type: str, owner: str | None = None) -> str:
        """Where a file type lives for this asset. owner is the skeleton, rig or look the file belongs to, for a
        file type that belongs to one. Pure: never checks or creates anything."""
        relative = self.project.file_type(file_type).relative_path(self.name, owner)
        return os.path.join(self.folder, relative)

    def file_exists(self, file_type: str, owner: str | None = None) -> bool:
        return os.path.exists(self.path(file_type, owner))

    def rig(self, name: str) -> RigRecord:
        """A rig's rig.json: the skeleton it is built on, and the rig it was copied from."""
        if not self.file_exists("riginfo", name):
            raise AssetError(f"{self.id} has no rig {name!r}. It has: {', '.join(self.rigs) or 'none'}.")
        return records.read_rig(self.path("riginfo", name))

    def look(self, name: str) -> LookRecord:
        """A look's look.json: the skeletons its meshes bind to."""
        if not self.file_exists("lookinfo", name):
            raise AssetError(f"{self.id} has no look {name!r}. It has: {', '.join(self.looks) or 'none'}.")
        return records.read_look(self.path("lookinfo", name))

    def resolve_skeleton(self, reference: SkeletonRef) -> tuple["Asset", str]:
        """The asset that holds a skeleton this asset names, and the skeleton's name. Pure: nothing is checked."""
        return (Asset(reference.asset, self.root) if reference.asset else self), reference.name

    def resolve_rig(self, reference: RigRef) -> tuple["Asset", str]:
        """The asset that holds a rig this asset names, and the rig's name. Pure: nothing is checked."""
        return (Asset(reference.asset, self.root) if reference.asset else self), reference.rig

    def skeleton_of(self, rig: str) -> tuple["Asset", str]:
        """The skeleton a rig is built on: the asset that holds it and its name."""
        return self.resolve_skeleton(self.rig(rig).skeleton)

    def parent_of(self, rig: str) -> tuple["Asset", str] | None:
        """The rig a rig attaches to: the asset that holds it and its name, or None for a rig that attaches to nothing."""
        parent = self.rig(rig).parent
        return None if parent is None else self.resolve_rig(parent)

    def look_fits(self, look: str, rig: str) -> bool:
        """Whether a rig can wear a look: the look names the rig's skeleton."""
        wanted = self._skeleton_key(self.rig(rig).skeleton)
        return any(self._skeleton_key(reference) == wanted for reference in self.look(look).skeletons)

    def _skeleton_key(self, reference: SkeletonRef) -> tuple[str, str]:
        return reference.asset or self.id, reference.name

    # ---- writes ----------------------------------------------------------------------------

    @classmethod
    def create(cls, asset_id: str, asset_type: str, root: str | None = None) -> "Asset":
        """Makes the asset folder and its asset.json, and marks the file for add in source control."""
        asset = cls(asset_id, root)
        if asset.exists():
            raise AssetError(f"{asset.id} already exists at {asset.folder}.")
        project = asset.project
        project.check_asset_type(asset_type)
        _check_not_nested(asset, project)

        os.makedirs(asset.folder, exist_ok=True)
        write_json(asset.info_path, {"formatVersion": FORMAT_VERSION, "assetType": asset_type})
        sourcecontrol.current().add(asset.info_path)
        return asset

    def add_rig(self, name: str, skeleton: SkeletonRef, source: RigRef | None = None,
                parent: RigRef | None = None) -> RigRecord:
        """Writes a new rig's rig.json. The skeleton needn't exist yet: a rig can be set up before its skeleton is
        saved, and the build reports a missing one. The same goes for the parent, which has to exist when the rig is
        built. A rig can't attach to itself, and following parents must end, across assets too."""
        record = RigRecord(skeleton, source, parent)
        if parent is not None:
            self.check_parent(name, parent)
        self._add_record("riginfo", name, "rig", lambda path: records.write_rig(path, record))
        return record

    def check_parent(self, name: str, parent: RigRef) -> None:
        """Raises when a rig of this asset called name can't attach to parent: following parents from it must not come
        back to it. A parent that has no rig.json yet ends the walk. add_rig checks this, and a tool checks it before
        it writes anything else."""
        me = (self.id, name)
        asset, rig = self.resolve_rig(parent)
        seen = [me]
        while True:
            key = (asset.id, rig)
            if key == me:
                chain = " -> ".join(f"{a}:{r}" for a, r in seen + [key])
                raise AssetError(f"The rig {name!r} of {self.id} can't attach to itself, directly or through its parents: {chain}.")
            if key in seen or not asset.file_exists("riginfo", rig):
                return
            seen.append(key)
            following = asset.rig(rig).parent
            if following is None:
                return
            asset, rig = asset.resolve_rig(following)

    def add_look(self, name: str, skeletons: typing.Sequence[SkeletonRef]) -> LookRecord:
        """Writes a new look's look.json."""
        record = LookRecord(tuple(skeletons))
        self._add_record("lookinfo", name, "look", lambda path: records.write_look(path, record))
        return record

    def _add_record(self, file_type: str, name: str, kind: str, write: typing.Callable[[str], None]) -> None:
        if not self.exists():
            raise AssetError(f"{self.id} has no {ASSET_FILE} at {self.folder}.")
        path = self.path(file_type, name)
        if os.path.exists(path):
            raise AssetError(f"{self.id} already has a {kind} {name!r}: {path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write(path)
        sourcecontrol.current().add(path)

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


def _read_info(path: str) -> dict:
    """asset.json at the current version. A version 1 file is updated in memory and written back, as project.json is:
    a file that can't be written (read-only in source control) stays as it is and is updated again next time."""
    data = read_json(path)
    version = data.get("formatVersion")
    if version == 1:
        # Version 1 named a whole asset as "skeleton". A rig and a look now name their own skeleton (RigModules D54).
        data.pop("skeleton", None)
        data["formatVersion"] = FORMAT_VERSION
        try:
            write_json(path, data)
        except OSError:
            pass
    elif version != FORMAT_VERSION:
        raise AssetError(f"{path}: formatVersion {version!r} is not {FORMAT_VERSION}.")
    return data


def _check_not_nested(asset: Asset, project: Project) -> None:
    """Assets never nest, so a folder is an asset or holds assets, never both. Checked here, where assets
    are made, so the registry scan can stop at each asset folder."""
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
