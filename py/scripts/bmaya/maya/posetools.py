"""Pose tools for RigModules rigs, behind the RigModules menu's pose submenu (RigModules D34).

The *_ui functions act on the selected rig controls, or on the whole active rig (bmaya.maya.activerig) when no
control is selected, so an animator can work on a limb or on everything with the same tool. Save and Load Pose ask
for a pose file. The pose commands set values and key nothing, so keying is a separate tool.
"""

from __future__ import annotations

import maya.cmds as cmds
import rigmodules.pose
import rigmodules.query

import bmaya.core.log
import bmaya.maya.activerig

POSE_FILTER = "Pose files (*.json)"


def get_scope() -> list[str]:
    """What the pose commands act on: the selected rig controls, else the active rig's root."""
    controls = cmds.ls(selection=True, type=rigmodules.query.RIG_CONTROL_TYPE)
    return controls or [bmaya.maya.activerig.get_active_rig().rig_root]


def get_selected_modules(rig_root: str) -> list[str]:
    """The modules of the rig that the selection names: a selected module node, or the module of a selected
    control. Raises RuntimeError when it names none."""
    module_nodes = {cmds.ls(control.module, long=True)[0]: control.module
                    for control in rigmodules.query.get_rig_controls(rig_root)}
    modules = []
    for node in cmds.ls(selection=True, objectsOnly=True, long=True):
        control = rigmodules.query.find_control(node)
        module = module_nodes.get(node) or (control.module if control else None)
        if module and module not in modules:
            modules.append(module)
    if not modules:
        raise RuntimeError("Select modules or controls of the active rig.")
    return modules


def zero_pose_ui() -> None:
    changed = cmds.zeroRigControls(*get_scope()) or []
    bmaya.core.log.info(f"Zeroed {len(changed)} control(s).")


def mirror_pose_ui(left_to_right: bool | None = None) -> None:
    """Mirrors the pose across the rig. left_to_right None lets the command pick the source side: the side of the
    selected controls when they share one, else Left."""
    kwargs = {} if left_to_right is None else {"leftToRight": left_to_right}
    changed = cmds.mirrorRigPose(*get_scope(), **kwargs) or []
    bmaya.core.log.info(f"Mirrored the pose onto {len(changed)} control(s).")


def flip_pose_ui() -> None:
    changed = cmds.flipRigPose(*get_scope()) or []
    bmaya.core.log.info(f"Flipped {len(changed)} control(s).")


def save_pose_ui() -> str | None:
    """Saves the pose of the scope to a file chosen in a dialog. Returns the path, or None when cancelled."""
    path = _ask_file("Save Pose", save=True)
    if path:
        saved = cmds.saveRigPose(*get_scope(), file=path)
        bmaya.core.log.info(f"Saved the pose of {len(saved)} control(s): {path}")
    return path


def load_pose_ui() -> str | None:
    """Loads a pose file chosen in a dialog onto the scope. Returns the path, or None when cancelled."""
    path = _ask_file("Load Pose", save=False)
    if path:
        changed = cmds.loadRigPose(*get_scope(), file=path) or []
        bmaya.core.log.info(f"Loaded the pose onto {len(changed)} control(s): {path}")
    return path


def key_all_controls_ui() -> None:
    count = rigmodules.pose.key_rig(bmaya.maya.activerig.get_active_rig().rig_root)
    bmaya.core.log.info(f"Keyed {count} channel(s) on every control of the active rig.")


def key_selected_modules_ui() -> None:
    rig_root = bmaya.maya.activerig.get_active_rig().rig_root
    modules = get_selected_modules(rig_root)
    count = rigmodules.pose.key_modules(rig_root, modules)
    bmaya.core.log.info(f"Keyed {count} channel(s) on the controls of {len(modules)} module(s).")


def _ask_file(caption: str, save: bool) -> str | None:
    paths = cmds.fileDialog2(caption=caption, fileFilter=POSE_FILTER, fileMode=0 if save else 1)
    return paths[0] if paths else None
