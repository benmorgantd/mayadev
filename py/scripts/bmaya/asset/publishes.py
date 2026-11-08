"""Publishes: one new folder per publish, never edited after it is made.

    variants/game/publish/20261108T142012Z_bmorgan/
        publish.json        who, when, and what the publish step records (plugin version, inputs...)
        ...                 the built rig and copies of its inputs, written by the publish step

Nothing shared changes on a publish, so two people publishing never edit the same file. The id is a UTC
timestamp and the user, so ids never collide between people and sort in time order: the latest publish
is the last id. A rig built from a publish stores the id in its rig root's publishVersion.
"""

from __future__ import annotations

import datetime
import getpass
import os
import re

from . import sourcecontrol
from .asset import Asset, AssetError
from .project import read_json, write_json

PUBLISH_FILE = "publish.json"
FORMAT_VERSION = 1

_ID = re.compile(r"\d{8}T\d{6}Z_[A-Za-z0-9_]+")


def make_id(user: str | None = None, when: datetime.datetime | None = None) -> str:
    when = (when or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
    user = re.sub(r"[^A-Za-z0-9_]", "_", user or getpass.getuser()) or "unknown"
    return f"{when:%Y%m%dT%H%M%S}Z_{user}"


def _folder(asset: Asset, variant: str) -> str:
    return asset.path("publish", variant)


def list_ids(asset: Asset, variant: str) -> list[str]:
    """Every publish id of a variant, oldest first."""
    folder = _folder(asset, variant)
    if not os.path.isdir(folder):
        return []
    return sorted(
        entry.name for entry in os.scandir(folder)
        if entry.is_dir() and _ID.fullmatch(entry.name) and os.path.isfile(os.path.join(entry.path, PUBLISH_FILE))
    )


def latest(asset: Asset, variant: str) -> str | None:
    ids = list_ids(asset, variant)
    return ids[-1] if ids else None


def info(asset: Asset, variant: str, publish_id: str) -> dict:
    return read_json(os.path.join(_folder(asset, variant), publish_id, PUBLISH_FILE))


def create(asset: Asset, variant: str, data: dict | None = None, user: str | None = None) -> str:
    """Makes a new publish folder with its publish.json and returns the folder. The caller writes the
    built rig and input copies into it, then the whole folder is added to source control."""
    if variant not in asset.variants:
        raise AssetError(f"{asset.id} has no rig variant {variant!r}. Known: {asset.variants}.")
    publish_id = make_id(user)
    folder = os.path.join(_folder(asset, variant), publish_id)
    try:
        os.makedirs(folder)
    except FileExistsError:
        raise AssetError(f"Publish {publish_id} of {asset.id} {variant} already exists.") from None
    record = dict(data or {})
    record.update({"formatVersion": FORMAT_VERSION, "id": publish_id, "user": publish_id.split("_", 1)[1]})
    path = os.path.join(folder, PUBLISH_FILE)
    write_json(path, record)
    sourcecontrol.current().add(path)
    return folder
