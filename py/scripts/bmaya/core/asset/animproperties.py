"""Animation properties: the engine's data about one exported clip, <name>.animproperties.json (RigModules D42).

An export folder holds the clip's FBX (what the joints do), its ControlAnim (what the rig did) and this file, which
is read only by the engine importer: how the clip plays and what rides on it. It never names a rig, a control or a
RigModules node, so it stays valid when the rig changes. Maya-free, like the rest of bmaya.core.asset.

    {
        "formatVersion": 1,
        "loop": false,
        "rootMotion": false,
        "additive": "none",
        "events": [ { "name": "footstep", "frame": 12.0 } ],
        "curves": [ { "name": "footLock_l", "keys": [ [1.0, 0.0], [12.0, 1.0] ] } ]
    }

additive is "none", "local" (relative to a reference pose, in each joint's space) or "mesh" (relative, in mesh space).
Frames are the clip's own frame numbers, the ones in its FBX. Curves are engine float curves (a foot lock, a blend
weight), not joint animation: each is a name and keys of [frame, value], in increasing frame order.
"""

from __future__ import annotations

import dataclasses
import json
import math
import os

FORMAT_VERSION = 1
ADDITIVE_TYPES = ("none", "local", "mesh")
FILE_SUFFIX = ".animproperties.json"


class AnimPropertiesError(ValueError):
    """A properties file or value that can't be used. The message lists every problem found."""


@dataclasses.dataclass(frozen=True)
class AnimEvent:
    name: str
    frame: float


@dataclasses.dataclass(frozen=True)
class AnimCurve:
    name: str
    keys: tuple[tuple[float, float], ...]


@dataclasses.dataclass(frozen=True)
class AnimProperties:
    """The properties of a clip. The defaults are a one-shot clip with no root motion, nothing additive and no events
    or curves."""

    loop: bool = False
    root_motion: bool = False
    additive: str = "none"
    events: tuple[AnimEvent, ...] = ()
    curves: tuple[AnimCurve, ...] = ()

    def __post_init__(self) -> None:
        problems = _check(self.to_json())
        if problems:
            raise AnimPropertiesError("; ".join(problems))

    def to_json(self) -> dict:
        return {
            "formatVersion": FORMAT_VERSION,
            "loop": self.loop,
            "rootMotion": self.root_motion,
            "additive": self.additive,
            "events": [{"name": event.name, "frame": event.frame} for event in self.events],
            "curves": [{"name": curve.name, "keys": [list(key) for key in curve.keys]} for curve in self.curves],
        }

    @staticmethod
    def from_json(data: object) -> AnimProperties:
        """Raises AnimPropertiesError listing every problem found."""
        problems = _check(data)
        if problems:
            raise AnimPropertiesError("; ".join(problems))
        return AnimProperties(
            loop=data["loop"],
            root_motion=data["rootMotion"],
            additive=data["additive"],
            events=tuple(AnimEvent(event["name"], float(event["frame"])) for event in data["events"]),
            curves=tuple(
                AnimCurve(curve["name"], tuple((float(frame), float(value)) for frame, value in curve["keys"]))
                for curve in data["curves"]),
        )


def get_path(fbx: str) -> str:
    """The properties file of the clip whose FBX is fbx."""
    return os.path.splitext(fbx)[0] + FILE_SUFFIX


def read(path: str) -> AnimProperties:
    """The properties in the file at path. Raises FileNotFoundError, and AnimPropertiesError."""
    with open(path, encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as error:
            raise AnimPropertiesError(f"{path} is not valid JSON: {error}") from error
    try:
        return AnimProperties.from_json(data)
    except AnimPropertiesError as error:
        raise AnimPropertiesError(f"{path}: {error}") from error


def write(path: str, properties: AnimProperties) -> None:
    """Writes properties to path. A failed write leaves an existing file as it was."""
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(properties.to_json(), handle, indent=4)
    os.replace(temp, path)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["the top level is not an object"]
    problems = []
    expected = {"formatVersion", "loop", "rootMotion", "additive", "events", "curves"}
    if data.get("formatVersion") != FORMAT_VERSION or isinstance(data.get("formatVersion"), bool):
        problems.append(f"formatVersion is {data.get('formatVersion')!r}, not {FORMAT_VERSION}")
    for key in sorted(set(data) - expected):
        problems.append(f"unknown key {key!r}")
    for key in ("loop", "rootMotion"):
        if not isinstance(data.get(key), bool):
            problems.append(f"{key} is missing or not a bool")
    if data.get("additive") not in ADDITIVE_TYPES:
        problems.append(f"additive is {data.get('additive')!r}, not one of {', '.join(ADDITIVE_TYPES)}")

    events = data.get("events")
    if not isinstance(events, list):
        problems.append("events is missing or not a list")
    else:
        for index, event in enumerate(events):
            if not isinstance(event, dict) or set(event) != {"name", "frame"}:
                problems.append(f"events[{index}] is not an object with name and frame")
                continue
            if not isinstance(event["name"], str) or not event["name"]:
                problems.append(f"events[{index}].name is empty or not a string")
            if not _is_number(event["frame"]):
                problems.append(f"events[{index}].frame is not a number")

    curves = data.get("curves")
    if not isinstance(curves, list):
        problems.append("curves is missing or not a list")
    else:
        names = []
        for index, curve in enumerate(curves):
            if not isinstance(curve, dict) or set(curve) != {"name", "keys"}:
                problems.append(f"curves[{index}] is not an object with name and keys")
                continue
            if not isinstance(curve["name"], str) or not curve["name"]:
                problems.append(f"curves[{index}].name is empty or not a string")
            elif curve["name"] in names:
                problems.append(f"curves[{index}].name {curve['name']!r} is used twice")
            names.append(curve["name"])
            keys = curve["keys"]
            if not isinstance(keys, list) or not keys:
                problems.append(f"curves[{index}].keys is missing, empty or not a list")
            elif not all(isinstance(key, (list, tuple)) and len(key) == 2 and all(_is_number(n) for n in key) for key in keys):
                problems.append(f"curves[{index}].keys has a key that is not [frame, value]")
            elif any(later[0] <= earlier[0] for earlier, later in zip(keys, keys[1:])):
                problems.append(f"curves[{index}].keys are not in increasing frame order")
    return problems
