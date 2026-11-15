"""Projects: the nearest folder above an asset that holds a project.json.

project.json holds the project's asset types and file types. Every asset under the folder belongs to
the project, down to the next project.json.
"""

from __future__ import annotations

import copy
import json
import os
import re
from dataclasses import dataclass

from . import assetid

PROJECTS_ROOT_ENV = "RIGGING_PROJECT_DIR"
PROJECT_FILE = "project.json"
FORMAT_VERSION = 1

# A new project's project.json. Paths are relative to the asset folder. {name} is the asset id's last
# token, {variant} a rig variant. Everything that can differ between variants lives under variants/.
DEFAULT_PROJECT = {
    "formatVersion": FORMAT_VERSION,
    "assetTypes": ["Prop", "Character", "Vehicle", "Head", "Weapon", "VFX", "Light", "Environment", "Skeleton", "Other"],
    "fileTypes": {
        "skeleton": {"path": "skeleton/{name}_skeleton.ma"},
        "model": {"path": "variants/{variant}/model/{name}_{variant}_model.ma"},
        "textures": {"path": "variants/{variant}/textures", "folder": True},
        "shaders": {"path": "variants/{variant}/shaders", "folder": True},
        "template": {"path": "variants/{variant}/template.json"},
        "shapes": {"path": "variants/{variant}/shapes.json"},
        "weights": {"path": "variants/{variant}/weights", "folder": True},
        "postops": {"path": "variants/{variant}/postops.py"},
        "rig": {"path": "variants/{variant}/{name}_{variant}_rig.ma"},
        "publish": {"path": "variants/{variant}/publish", "folder": True},
        "controlposes": {"path": "controlposes", "folder": True},
        "controlanims": {"path": "controlanims", "folder": True},
        "exports": {"path": "exports", "folder": True},
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
    def per_variant(self) -> bool:
        return "variant" in _FIELD.findall(self.pattern)

    def variant_parent(self) -> str:
        """The folder below the asset that holds one folder per variant: "variants" for
        "variants/{variant}/template.json"."""
        head, marker, _tail = self.pattern.partition("{variant}")
        if not marker or not head.endswith("/") or "{" in head:
            raise ProjectError(f"File type {self.key!r} needs a path of the form '<folder>/{{variant}}/...'.")
        return os.path.normpath(head)

    def relative_path(self, name: str, variant: str | None = None) -> str:
        """The path below the asset folder."""
        if self.per_variant:
            if not variant:
                raise ProjectError(f"File type {self.key!r} is per variant: pass a variant.")
            if not assetid.is_valid_token(variant):
                raise ProjectError(f"Variant {variant!r} must be letters, digits and '_'.")
        elif variant:
            raise ProjectError(f"File type {self.key!r} belongs to the asset, not a variant.")
        fields = {"name": name, "variant": variant}
        unknown = set(_FIELD.findall(self.pattern)) - set(fields)
        if unknown:
            raise ProjectError(f"File type {self.key!r} uses unknown fields {sorted(unknown)}.")
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


def _read_project(path: str) -> dict:
    data = read_json(path)
    if data.get("formatVersion") != FORMAT_VERSION:
        raise ProjectError(f"{path}: formatVersion {data.get('formatVersion')!r} is not {FORMAT_VERSION}.")
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
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp, path)
