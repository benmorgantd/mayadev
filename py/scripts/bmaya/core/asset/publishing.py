"""The publish gates and the publish step for a rig and a look (RigModules D70).

Plain Python with no Maya import. A build never fails over source data, so strictness lives here, at the publish:

- A look publish is refused while any mesh the rig wears was not loaded as saved (it was folded or bound rigid) or is
  stale (look_blockers). It needs the look status of the scene (bmaya.core.asset.lookstatus), so it is checked by the
  Maya side and the files are copied here.
- A rig publish is checked against the last publish of that rig when there is one, the baseline that animation, other
  rigs and engine exports may depend on (breaking_skeleton_changes). Adding a joint is fine (D29: a variant may add and
  never remove). A removed joint, a changed parent, a changed name, a changed rest or rotate order is breaking, and the
  publish needs it acknowledged. A rig with no publish yet is a draft: nothing to compare, nothing is refused.

What a publish holds is the copies of its inputs, next to publish.json (publishes.create): for a rig its skeleton.json,
template.json, rig.json, shapes.json and postops.py, for a look its look.json, model, weights, textures and shaders.
The built rig scene is not written by this step.
"""

from __future__ import annotations

import os
import shutil

from . import publishes, sourcecontrol
from .asset import Asset, AssetError
from .lookstatus import LOADED, LookStatus
from .project import read_json

SKELETON_FILE = "skeleton.json"
REST_GRID = 1e-4   # RigModules' skeleton hash rounds a rest to this step, so a moved-back joint is the same


# ---- the gates -----------------------------------------------------------------------------------------------------

def look_blockers(status: LookStatus | None, worn_look: str | None, look: str) -> list[str]:
    """Why the look can't be published from the rig in the scene, one line each, or []. The rig must wear the look, and
    every mesh must read as loaded and not stale: Save Skin Weights as they are, or skin the mesh, to clear one."""
    if worn_look != look:
        return [f"The rig wears {'no look' if worn_look is None else repr(worn_look)}, not {look!r}. Build the rig in it first."]
    if status is None:
        return [f"The look {look!r} was not applied in this session, so there is no status to check. Apply it first."]
    blockers = []
    for mesh in status.meshes:
        if mesh.result != LOADED:
            blockers.append(f"{mesh.mesh_name} was {mesh.result}: " + "; ".join(mesh.reasons))
        if mesh.stale_skeleton:
            blockers.append(f"{mesh.mesh_name}'s weight file was saved from another skeleton.")
    if status.skeleton_stale:
        blockers.append("The look's skeleton file is not the rig's.")
    return blockers


def breaking_skeleton_changes(baseline: dict, working: dict) -> list[str]:
    """What the working skeleton.json changed that the baseline's animation, rigs and exports may depend on, one line
    each, or []. A joint is its (side, usage) markup. Joints only the working skeleton has are not listed."""
    old = {tuple(joint["markup"]): joint for joint in baseline.get("joints", [])}
    new = {tuple(joint["markup"]): joint for joint in working.get("joints", [])}
    changes = []
    for key, joint in old.items():
        label = f"[{key[0]}, {key[1]}]"
        if key not in new:
            changes.append(f"{label} was removed")
            continue
        other = new[key]
        if joint.get("parent") != other.get("parent"):
            changes.append(f"{label} has another parent ({_selector(joint.get('parent'))} became {_selector(other.get('parent'))})")
        if joint.get("name") != other.get("name"):
            changes.append(f"{label} was renamed ({joint.get('name')} became {other.get('name')})")
        if joint.get("rotateOrder") != other.get("rotateOrder"):
            changes.append(f"{label} has another rotate order")
        if _rest(joint) != _rest(other):
            changes.append(f"{label} has another rest")
    return changes


def _selector(value: object) -> str:
    return "none" if value is None else f"[{value[0]}, {value[1]}]"


def _rest(joint: dict) -> list[int]:
    return [round(value / REST_GRID) for value in joint.get("restLocal", [])]


# ---- the files a publish copies ------------------------------------------------------------------------------------

def rig_inputs(asset: Asset, rig: str) -> dict[str, str]:
    """The files of a rig that a publish copies, by the name each has in the publish folder. Only those that exist."""
    skeleton_asset, skeleton = asset.skeleton_of(rig)
    candidates = {SKELETON_FILE: skeleton_asset.path("skeleton", skeleton),
                  "template.json": asset.path("template", rig), "rig.json": asset.path("riginfo", rig),
                  "shapes.json": asset.path("shapes", rig), "postops.py": asset.path("postops", rig)}
    return {name: path for name, path in candidates.items() if os.path.isfile(path)}


def rig_breaking_changes(asset: Asset, rig: str) -> list[str]:
    """What the rig's working skeleton would break against the rig's latest publish. [] for a rig never published, and
    for a publish with no skeleton copy."""
    latest = publishes.latest(asset, publishes.RIG, rig)
    skeleton_asset, skeleton = asset.skeleton_of(rig)
    working = skeleton_asset.path("skeleton", skeleton)
    if latest is None or not os.path.isfile(working):
        return []
    baseline = os.path.join(asset.path("rigpublish", rig), latest, SKELETON_FILE)
    if not os.path.isfile(baseline):
        return []
    return breaking_skeleton_changes(read_json(baseline), read_json(working))


def skeleton_breaking_changes(asset: Asset, skeleton: str) -> dict[str, list[str]]:
    """For each rig of the asset built on this skeleton that has a publish, what the skeleton as saved breaks. Rigs with
    nothing breaking are left out, so a skeleton that only grew gives {}."""
    found = {}
    for rig in asset.rigs:
        skeleton_asset, name = asset.skeleton_of(rig)
        if (skeleton_asset.id, name) == (asset.id, skeleton):
            changes = rig_breaking_changes(asset, rig)
            if changes:
                found[rig] = changes
    return found


# ---- the publish step ----------------------------------------------------------------------------------------------

def publish_rig(asset: Asset, rig: str, acknowledged: bool = False, data: dict | None = None, user: str | None = None) -> str:
    """Publishes the rig: a new folder with copies of its inputs. Raises AssetError, with nothing written, when the
    skeleton breaks the last publish and acknowledged is False. Returns the folder."""
    inputs = rig_inputs(asset, rig)
    if SKELETON_FILE not in inputs:
        raise AssetError(f"The rig {rig!r} of {asset.id} has no saved skeleton to publish. Save it first.")
    changes = rig_breaking_changes(asset, rig)
    if changes and not acknowledged:
        raise AssetError(f"The skeleton of the rig {rig!r} of {asset.id} breaks the last publish: " + "; ".join(changes)
                         + ". Publish again acknowledging it.")
    record = dict(data or {})
    record["inputs"] = sorted(inputs)
    if changes:
        record["breakingChanges"] = changes
    folder = publishes.create(asset, publishes.RIG, rig, record, user)
    for name, source in inputs.items():
        _copy(source, os.path.join(folder, name))
    return folder


def look_inputs(asset: Asset, look: str) -> dict[str, str]:
    """The files and folders of a look that a publish copies, by name in the publish folder. Only those that exist."""
    model = asset.path("model", look)
    candidates = {"look.json": asset.path("lookinfo", look), os.path.join("model", os.path.basename(model)): model,
                  "weights": asset.path("weights", look), "textures": asset.path("textures", look),
                  "shaders": asset.path("shaders", look)}
    return {name: path for name, path in candidates.items() if os.path.exists(path)}


def publish_look(asset: Asset, look: str, data: dict | None = None, user: str | None = None) -> str:
    """Publishes the look: a new folder with copies of its inputs. The caller checks look_blockers first, because the
    status it needs is the scene's. Returns the folder."""
    inputs = look_inputs(asset, look)
    if "look.json" not in inputs:
        raise AssetError(f"The look {look!r} of {asset.id} has no look.json to publish.")
    record = dict(data or {})
    record["inputs"] = sorted(inputs)
    folder = publishes.create(asset, publishes.LOOK, look, record, user)
    for name, source in inputs.items():
        _copy(source, os.path.join(folder, name))
    return folder


def _copy(source: str, destination: str) -> None:
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if os.path.isdir(source):
        shutil.copytree(source, destination)
    else:
        shutil.copyfile(source, destination)
    sourcecontrol.current().add(destination)
