"""Publishes: one new folder per publish, never edited after it is made.

    rigs/body/publish/20261108T142012Z_bmorgan/
        publish.json        who, when, and what the publish step records (plugin version, inputs...)
        ...                 the built rig and copies of its inputs, written by the publish step
    looks/winter/publish/20261109T090000Z_alice/

A rig and a look are published separately, each under its own folder, and an animation scene imports one of each
(RigModules D54). Every function takes a kind, "rig" or "look", and the rig's or look's name.

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

RIG = "rig"
LOOK = "look"
# The project.json file type that holds each kind's publishes.
FOLDER_TYPE = {RIG: "rigpublish", LOOK: "lookpublish"}

_ID = re.compile(r"\d{8}T\d{6}Z_[A-Za-z0-9_]+")


def make_id(user: str | None = None, when: datetime.datetime | None = None) -> str:
    when = (when or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
    user = re.sub(r"[^A-Za-z0-9_]", "_", user or getpass.getuser()) or "unknown"
    return f"{when:%Y%m%dT%H%M%S}Z_{user}"


def _folder(asset: Asset, kind: str, name: str) -> str:
    if kind not in FOLDER_TYPE:
        raise AssetError(f"A publish is of a {RIG!r} or a {LOOK!r}, not {kind!r}.")
    return asset.path(FOLDER_TYPE[kind], name)


def list_ids(asset: Asset, kind: str, name: str) -> list[str]:
    """Every publish id of a rig or a look, oldest first."""
    folder = _folder(asset, kind, name)
    if not os.path.isdir(folder):
        return []
    return sorted(
        entry.name for entry in os.scandir(folder)
        if entry.is_dir() and _ID.fullmatch(entry.name) and os.path.isfile(os.path.join(entry.path, PUBLISH_FILE))
    )


def latest(asset: Asset, kind: str, name: str) -> str | None:
    ids = list_ids(asset, kind, name)
    return ids[-1] if ids else None


def info(asset: Asset, kind: str, name: str, publish_id: str) -> dict:
    return read_json(os.path.join(_folder(asset, kind, name), publish_id, PUBLISH_FILE))


def create(asset: Asset, kind: str, name: str, data: dict | None = None, user: str | None = None) -> str:
    """Makes a new publish folder with its publish.json and returns the folder. The caller writes the
    built rig or look and copies of its inputs into it, then the whole folder is added to source control."""
    base = _folder(asset, kind, name)
    known = asset.rigs if kind == RIG else asset.looks
    if name not in known:
        raise AssetError(f"{asset.id} has no {kind} {name!r}. Known: {known}.")
    publish_id = make_id(user)
    folder = os.path.join(base, publish_id)
    try:
        os.makedirs(folder)
    except FileExistsError:
        raise AssetError(f"Publish {publish_id} of {asset.id} {kind} {name!r} already exists.") from None
    record = dict(data or {})
    record.update({"formatVersion": FORMAT_VERSION, "id": publish_id, "user": publish_id.split("_", 1)[1]})
    path = os.path.join(folder, PUBLISH_FILE)
    write_json(path, record)
    sourcecontrol.current().add(path)
    return folder
