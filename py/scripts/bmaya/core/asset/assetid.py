"""Asset ids: the asset folder's path below RIGGING_PROJECT_DIR, with SEPARATOR between folders.

"shooter\\main\\characters\\hero" is the folder <RIGGING_PROJECT_DIR>/shooter/main/characters/hero.
Any depth. Each token is a folder name of letters, digits and "_". Ids compare without case and are
stored as authored. The rules match RigModules' core/AssetId (D29 in RigModules' decisions.md).

Every place that splits or joins an id goes through this module, so a later change of separator
is a change here.
"""

from __future__ import annotations

import os
import re

SEPARATOR = "\\"

_TOKEN = re.compile(r"[A-Za-z0-9_]+")


class AssetIdError(ValueError):
    """An asset id that breaks the rules above."""


def is_valid_token(token: str) -> bool:
    """One folder name of an id. Rig variant names follow the same rule."""
    return isinstance(token, str) and bool(_TOKEN.fullmatch(token))


def is_valid(asset_id: str) -> bool:
    if not isinstance(asset_id, str) or not asset_id:
        return False
    return all(is_valid_token(token) for token in asset_id.split(SEPARATOR))


def check(asset_id: str) -> str:
    """Returns asset_id unchanged, or raises AssetIdError."""
    if not is_valid(asset_id):
        raise AssetIdError(
            f"Asset id {asset_id!r} must be {SEPARATOR!r}-separated folder names of letters, digits and '_'."
        )
    return asset_id


def tokens(asset_id: str) -> list[str]:
    return check(asset_id).split(SEPARATOR)


def name(asset_id: str) -> str:
    """The last token: "hero". The default namespace of a rig built for the asset."""
    return tokens(asset_id)[-1]


def key(asset_id: str) -> str:
    """The form ids are compared and looked up by."""
    return check(asset_id).casefold()


def equals(a: str, b: str) -> bool:
    return key(a) == key(b)


def to_relative_path(asset_id: str) -> str:
    return os.path.join(*tokens(asset_id))


def from_relative_path(relative_path: str) -> str:
    """The id of a folder given relative to the projects root."""
    parts = [part for part in os.path.normpath(relative_path).split(os.sep) if part not in ("", ".")]
    if not parts or ".." in parts:
        raise AssetIdError(f"{relative_path!r} is not a folder below the projects root.")
    return check(SEPARATOR.join(parts))
