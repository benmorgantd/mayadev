"""Projects: the nearest folder above an asset that holds a project.json.

project.json holds the project's asset types and file types. Every asset under the folder belongs to
the project, down to the next project.json.
"""

from __future__ import annotations

import copy
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass

from . import assetid

PROJECTS_ROOT_ENV = "RIGGING_PROJECT_DIR"
PROJECT_FILE = "project.json"
FORMAT_VERSION = 3

# The parts of an asset a file can belong to (RigModules D54). A file type's path names at most one of them as a
# field: "rigs/{rig}/shapes.json" belongs to a rig. A path with none belongs to the asset.
OWNER_KINDS = ("skeleton", "rig", "look")

# A new project's project.json. Paths are relative to the asset folder. {name} is the asset id's last token.
# An asset holds skeletons, rigs and looks: a skeleton is its skeleton.json (the only form a skeleton is stored in),
# a rig is a template built on one skeleton, and a look is the meshes and weights a rig of that skeleton wears.
DEFAULT_PROJECT = {
    "formatVersion": FORMAT_VERSION,
    "assetTypes": ["Prop", "Character", "Vehicle", "Head", "Weapon", "VFX", "Light", "Environment", "Skeleton", "Other"],
    "fileTypes": {
        "skeleton": {"path": "skeletons/{skeleton}/skeleton.json"},
        "exports": {"path": "skeletons/{skeleton}/exports", "folder": True},
        "riginfo": {"path": "rigs/{rig}/rig.json"},
        "template": {"path": "rigs/{rig}/template.json"},
        "shapes": {"path": "rigs/{rig}/shapes.json"},
        "postops": {"path": "rigs/{rig}/postops.py"},
        "rig": {"path": "rigs/{rig}/{name}_{rig}_rig.ma"},
        "rigpublish": {"path": "rigs/{rig}/publish", "folder": True},
        "controlposes": {"path": "rigs/{rig}/controlposes", "folder": True},
        "controlanims": {"path": "rigs/{rig}/controlanims", "folder": True},
        "lookinfo": {"path": "looks/{look}/look.json"},
        "model": {"path": "looks/{look}/model/{name}_{look}_model.ma"},
        "textures": {"path": "looks/{look}/textures", "folder": True},
        "shaders": {"path": "looks/{look}/shaders", "folder": True},
        "weights": {"path": "looks/{look}/weights", "folder": True},
        "lookpublish": {"path": "looks/{look}/publish", "folder": True},
        "sources": {"path": "sources", "folder": True},
    },
    # The pose and animation library's vocabularies (RigModules D51). A studio edits them in project.json.
    "rig": {"regions": ["lowerBody", "upperBody", "head", "hands"]},
    "library": {"statuses": ["scratch", "review", "final"]},
}

_FIELD = re.compile(r"{(\w+)}")


class ProjectError(RuntimeError):
    """A missing or broken project.json, or a request it can't answer."""


def projects_root() -> str:
    root = os.environ.get(PROJECTS_ROOT_ENV)
    if not root:
        raise ProjectError(f"{PROJECTS_ROOT_ENV} is not set. Point it at the folder that holds every game's projects.")
    return os.path.normpath(root)


@dataclass(frozen=True)
class FileType:
    key: str
    pattern: str
    folder: bool = False

    @property
    def owner(self) -> str | None:
        """What the file belongs to: "skeleton", "rig" or "look", or None for the asset itself."""
        kinds = sorted(set(_FIELD.findall(self.pattern)) & set(OWNER_KINDS))
        if len(kinds) > 1:
            raise ProjectError(f"File type {self.key!r} names {' and '.join(kinds)} in its path {self.pattern!r}: a file belongs to one.")
        return kinds[0] if kinds else None

    def check(self) -> None:
        """Raises ProjectError for a path that can't be used: an unknown field, or more than one owner."""
        unknown = set(_FIELD.findall(self.pattern)) - {"name", *OWNER_KINDS}
        if "variant" in unknown:
            raise ProjectError(
                f"File type {self.key!r} still uses {{variant}} in its path {self.pattern!r}. Variants became rigs and looks: "
                f"edit the path in {PROJECT_FILE} to use {{skeleton}}, {{rig}} or {{look}}.")
        if unknown:
            raise ProjectError(f"File type {self.key!r} uses unknown fields {sorted(unknown)} in its path {self.pattern!r}.")
        self.owner

    def owner_parent(self) -> str:
        """The folder below the asset that holds one folder per owner: "rigs" for "rigs/{rig}/template.json"."""
        owner = self.owner
        head, marker, _tail = self.pattern.partition("{%s}" % owner)
        if not marker or not head.endswith("/") or "{" in head:
            raise ProjectError(f"File type {self.key!r} needs a path of the form '<folder>/{{skeleton, rig or look}}/...'.")
        return os.path.normpath(head)

    def relative_path(self, name: str, owner: str | None = None) -> str:
        """The path below the asset folder. owner is the name of the skeleton, rig or look the file belongs to."""
        self.check()
        kind = self.owner
        fields = {"name": name}
        if kind:
            if not owner:
                raise ProjectError(f"File type {self.key!r} belongs to a {kind}: pass its name.")
            if not assetid.is_valid_token(owner):
                raise ProjectError(f"The {kind} name {owner!r} must be lowercase letters, digits and '_'.")
            fields[kind] = owner
        elif owner:
            raise ProjectError(f"File type {self.key!r} belongs to the asset, not to {owner!r}.")
        return os.path.normpath(self.pattern.format(**fields))


class Project:
    def __init__(self, root: str):
        self.root = os.path.normpath(root)
        self._data = _read_project(os.path.join(self.root, PROJECT_FILE))
        self.asset_types: list[str] = list(self._data.get("assetTypes", []))
        # The library's vocabularies. Files that use a value outside them are the browser's warning, not an error.
        self.rig_regions: list[str] = list(self._data.get("rig", {}).get("regions", []))
        self.library_statuses: list[str] = list(self._data.get("library", {}).get("statuses", []))
        self.file_types: dict[str, FileType] = {
            key: FileType(key, value["path"], bool(value.get("folder", False)))
            for key, value in self._data.get("fileTypes", {}).items()
        }
        for file_type in self.file_types.values():
            try:
                file_type.check()
            except ProjectError as error:
                raise ProjectError(f"{os.path.join(self.root, PROJECT_FILE)}: {error}") from None

    def __repr__(self) -> str:
        return f"Project({self.root!r})"

    @classmethod
    def find(cls, path: str) -> "Project":
        """The project of a path: the nearest folder at or above it with a project.json. The path need not exist."""
        folder = os.path.normpath(os.path.abspath(path))
        while True:
            if os.path.isfile(os.path.join(folder, PROJECT_FILE)):
                return cls(folder)
            parent = os.path.dirname(folder)
            if parent == folder:
                raise ProjectError(f"No {PROJECT_FILE} at or above {path}.")
            folder = parent

    @classmethod
    def create(cls, root: str, data: dict | None = None) -> "Project":
        """Writes a project.json (DEFAULT_PROJECT unless data is given) and returns the project."""
        path = os.path.join(root, PROJECT_FILE)
        if os.path.exists(path):
            raise ProjectError(f"{path} already exists.")
        os.makedirs(root, exist_ok=True)
        write_json(path, copy.deepcopy(data if data is not None else DEFAULT_PROJECT))
        return cls(root)

    def file_type(self, key: str) -> FileType:
        try:
            return self.file_types[key]
        except KeyError:
            raise ProjectError(f"{self.root} has no file type {key!r}. Known: {sorted(self.file_types)}.") from None

    def check_asset_type(self, asset_type: str) -> str:
        if asset_type not in self.asset_types:
            raise ProjectError(f"Asset type {asset_type!r} is not one of {self.asset_types} ({self.root}).")
        return asset_type


def _add_library_folders(data: dict) -> None:
    """Version 1 to 2. A version 1 project made before the pose and animation library (RigModules D42, D51)
    has none of its folders or vocabularies. Adds what is missing and never replaces what a studio edited.

    A step is frozen: it spells out the values it adds and never reads DEFAULT_PROJECT, which moves on
    with every version. A later default goes in a later step."""
    file_types = data.setdefault("fileTypes", {})
    if not isinstance(file_types, dict):
        raise ProjectError("fileTypes must be an object.")
    for key in ("controlposes", "controlanims", "exports", "sources"):
        file_types.setdefault(key, {"path": key, "folder": True})
    data.setdefault("rig", {"regions": ["lowerBody", "upperBody", "head", "hands"]})
    data.setdefault("library", {"statuses": ["scratch", "review", "final"]})


def _split_variants_into_rigs_and_looks(data: dict) -> None:
    """Version 2 to 3 (RigModules D54). A variant was a rig with its own model and weights. An asset now holds
    skeletons, rigs and looks, so every path that was per variant moves under rigs/{rig} or looks/{look}, the skeleton
    becomes skeletons/{skeleton}/skeleton.json (there is no skeleton .ma), exports move under their skeleton, and
    the pose and animation folders move under their rig.

    Only a path that still equals its version 2 default is replaced. A path a studio edited is left alone: one that
    still uses {variant} then fails the project's load by name, because a guess at where it should go would be wrong
    silently. File types the defaults never had are untouched. Frozen, like every step."""
    file_types = data.setdefault("fileTypes", {})
    if not isinstance(file_types, dict):
        raise ProjectError("fileTypes must be an object.")
    moved = {
        "skeleton": ("skeleton/{name}_skeleton.ma", "skeletons/{skeleton}/skeleton.json"),
        "exports": ("exports", "skeletons/{skeleton}/exports"),
        "template": ("variants/{variant}/template.json", "rigs/{rig}/template.json"),
        "shapes": ("variants/{variant}/shapes.json", "rigs/{rig}/shapes.json"),
        "postops": ("variants/{variant}/postops.py", "rigs/{rig}/postops.py"),
        "rig": ("variants/{variant}/{name}_{variant}_rig.ma", "rigs/{rig}/{name}_{rig}_rig.ma"),
        "controlposes": ("controlposes", "rigs/{rig}/controlposes"),
        "controlanims": ("controlanims", "rigs/{rig}/controlanims"),
        "model": ("variants/{variant}/model/{name}_{variant}_model.ma", "looks/{look}/model/{name}_{look}_model.ma"),
        "textures": ("variants/{variant}/textures", "looks/{look}/textures"),
        "shaders": ("variants/{variant}/shaders", "looks/{look}/shaders"),
        "weights": ("variants/{variant}/weights", "looks/{look}/weights"),
    }
    for key, (old, new) in moved.items():
        entry = file_types.get(key)
        if isinstance(entry, dict) and entry.get("path") == old:
            entry["path"] = new
    # Publishes are per rig and per look, and a file type has one path, so the one type becomes two.
    publish = file_types.get("publish")
    if isinstance(publish, dict) and publish.get("path") == "variants/{variant}/publish":
        del file_types["publish"]
    file_types.setdefault("rigpublish", {"path": "rigs/{rig}/publish", "folder": True})
    file_types.setdefault("lookpublish", {"path": "looks/{look}/publish", "folder": True})
    file_types.setdefault("riginfo", {"path": "rigs/{rig}/rig.json"})
    file_types.setdefault("lookinfo", {"path": "looks/{look}/look.json"})


# Step n turns a version n file into a version n + 1 file, in place. Bump FORMAT_VERSION and add a step
# together, and add the new keys to DEFAULT_PROJECT. A step is never edited after it ships.
PROJECT_UPDATES: dict[int, Callable[[dict], None]] = {1: _add_library_folders, 2: _split_variants_into_rigs_and_looks}


def update_project_data(data: dict) -> bool:
    """Runs the steps from the file's formatVersion up to FORMAT_VERSION, in order, in place. Returns whether
    anything changed. Raises ProjectError for a version that isn't a whole number from 1, one written by a
    newer mayadev, or one with no step."""
    start = data.get("formatVersion")
    if isinstance(start, bool) or not isinstance(start, int) or start < 1:
        raise ProjectError(f"formatVersion {start!r} must be a whole number from 1.")
    if start > FORMAT_VERSION:
        raise ProjectError(f"formatVersion {start} was written by a newer mayadev (this one reads up to {FORMAT_VERSION}).")
    for version in range(start, FORMAT_VERSION):
        step = PROJECT_UPDATES.get(version)
        if step is None:
            raise ProjectError(f"formatVersion {version} is no longer read.")
        step(data)
        data["formatVersion"] = version + 1
    return start != FORMAT_VERSION


def _read_project(path: str) -> dict:
    """Reads a project.json at the current version. An older file is updated in memory, then written back so
    the file itself is current. A file that can't be written (read-only in source control, no access) stays as
    it is: this run uses the updated data and the next run updates it again."""
    data = read_json(path)
    try:
        updated = update_project_data(data)
    except ProjectError as error:
        raise ProjectError(f"{path}: {error}") from None
    if updated:
        try:
            write_json(path, data)
        except OSError:
            pass
    return data


def read_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        raise ProjectError(f"Can't read {path}: {error}") from None


def write_json(path: str, data: dict) -> None:
    """Writes through a temporary file, so a failed write never leaves half a file. Sorted keys and one
    item per line keep diffs small and Perforce merges clean."""
    temp = path + ".tmp"
    try:
        with open(temp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp, path)
    except BaseException:
        try:
            os.remove(temp)
        except OSError:
            pass
        raise
