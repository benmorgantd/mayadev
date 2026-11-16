"""rig.json and look.json: what a rig is built on and what a look can be worn by (RigModules D54).

    rigs/body/rig.json          {"formatVersion": 1, "skeleton": "default"}
    rigs/body_cine/rig.json     {"formatVersion": 1, "skeleton": "default", "source": "body"}
    looks/default/look.json     {"formatVersion": 1, "skeletons": ["default"]}

A skeleton or a rig in the same asset is named by a plain string. One in another asset is named by two fields,
never a joined string:

    {"skeleton": {"asset": "shooter\\main\\characters\\npc_male", "name": "default"}}
    {"source": {"asset": "shooter\\main\\characters\\hero", "rig": "body"}}

A template can't hold the skeleton, because templates are shared between assets, so the rig's folder holds this
small file. Each rig and each look has its own, so adding one adds files and edits nothing shared.
"""

from __future__ import annotations

import dataclasses

from . import assetid
from .project import ProjectError, read_json, write_json

FORMAT_VERSION = 1


class RecordError(RuntimeError):
    """A rig.json or look.json that can't be read, or a reference that breaks the rules."""


@dataclasses.dataclass(frozen=True)
class SkeletonRef:
    """A skeleton by name, in the asset that names it (asset None) or in another asset."""

    name: str
    asset: str | None = None

    def __post_init__(self):
        _check_name(self.name, "skeleton")
        if self.asset is not None:
            assetid.check(self.asset)

    def to_json(self) -> str | dict:
        return self.name if self.asset is None else {"asset": self.asset, "name": self.name}

    @classmethod
    def from_json(cls, value: object, where: str) -> "SkeletonRef":
        return cls(*_parse_reference(value, "name", where))


@dataclasses.dataclass(frozen=True)
class RigRef:
    """A rig by name, in the asset that names it (asset None) or in another asset."""

    rig: str
    asset: str | None = None

    def __post_init__(self):
        _check_name(self.rig, "rig")
        if self.asset is not None:
            assetid.check(self.asset)

    def to_json(self) -> str | dict:
        return self.rig if self.asset is None else {"asset": self.asset, "rig": self.rig}

    @classmethod
    def from_json(cls, value: object, where: str) -> "RigRef":
        return cls(*_parse_reference(value, "rig", where))


@dataclasses.dataclass(frozen=True)
class RigRecord:
    """rig.json. skeleton is what the rig's template is built on. source is the rig this one was copied from, whose
    poses and animations the library lists beside the copy's own (one level: a copy of a copy names the rig it was
    copied from)."""

    skeleton: SkeletonRef
    source: RigRef | None = None


@dataclasses.dataclass(frozen=True)
class LookRecord:
    """look.json. skeletons are the skeletons the look's meshes bind to: a rig of any of them can wear the look."""

    skeletons: tuple[SkeletonRef, ...]

    def __post_init__(self):
        if not self.skeletons:
            raise RecordError("A look names at least one skeleton.")


def read_rig(path: str) -> RigRecord:
    data = _read(path, {"skeleton"}, {"source"})
    try:
        source = RigRef.from_json(data["source"], "source") if "source" in data else None
        return RigRecord(SkeletonRef.from_json(data["skeleton"], "skeleton"), source)
    except (RecordError, assetid.AssetIdError) as error:
        raise RecordError(f"{path}: {error}") from None


def write_rig(path: str, record: RigRecord) -> None:
    data = {"formatVersion": FORMAT_VERSION, "skeleton": record.skeleton.to_json()}
    if record.source is not None:
        data["source"] = record.source.to_json()
    write_json(path, data)


def read_look(path: str) -> LookRecord:
    data = _read(path, {"skeletons"}, set())
    skeletons = data["skeletons"]
    if not isinstance(skeletons, list):
        raise RecordError(f"{path}: skeletons must be a list.")
    try:
        return LookRecord(tuple(SkeletonRef.from_json(value, f"skeletons[{index}]") for index, value in enumerate(skeletons)))
    except (RecordError, assetid.AssetIdError) as error:
        raise RecordError(f"{path}: {error}") from None


def write_look(path: str, record: LookRecord) -> None:
    write_json(path, {"formatVersion": FORMAT_VERSION, "skeletons": [skeleton.to_json() for skeleton in record.skeletons]})


def _read(path: str, required: set[str], optional: set[str]) -> dict:
    try:
        data = read_json(path)
    except ProjectError as error:
        raise RecordError(str(error)) from None
    if not isinstance(data, dict) or data.get("formatVersion") != FORMAT_VERSION:
        version = data.get("formatVersion") if isinstance(data, dict) else None
        raise RecordError(f"{path}: formatVersion {version!r} is not {FORMAT_VERSION}.")
    keys = set(data) - {"formatVersion"}
    if required - keys:
        raise RecordError(f"{path}: missing {sorted(required - keys)}.")
    if keys - required - optional:
        raise RecordError(f"{path}: unknown keys {sorted(keys - required - optional)}.")
    return data


def _parse_reference(value: object, name_key: str, where: str) -> tuple[str, str | None]:
    """(name, asset) of a reference: a plain string, or an object with "asset" and name_key."""
    if isinstance(value, str):
        return value, None
    if isinstance(value, dict) and set(value) == {"asset", name_key} and all(isinstance(item, str) for item in value.values()):
        return value[name_key], value["asset"]
    raise RecordError(f"{where} must be a name, or an object with 'asset' and {name_key!r}, not {value!r}.")


def _check_name(name: object, kind: str) -> None:
    if not assetid.is_valid_token(name):
        raise RecordError(f"The {kind} name {name!r} must be lowercase letters, digits and '_'.")
