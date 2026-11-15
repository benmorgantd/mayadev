"""Pose tools for RigModules rigs, behind the RigModules menu's pose submenu (RigModules D34).

The *_ui functions act on the selected rig controls, or on the whole active rig (bmaya.maya.activerig) when no
control is selected, so an animator can work on a limb or on everything with the same tool. Save and Load Pose
work on files in the asset, so they live in bmaya.maya.assettools. The pose commands set values and key
nothing, so keying is a separate tool.
"""

from __future__ import annotations

import maya.cmds as cmds
import rigmodules.pose
import rigmodules.query

import bmaya.core.log
import bmaya.maya.activerig


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


def zero_pose(scope: list[str]) -> int:
    """Sets the controls of scope (rig controls, or a rig root for the whole rig) to their rest. Returns how many
    controls changed."""
    changed = cmds.zeroRigControls(*scope) or []
    bmaya.core.log.info(f"Zeroed {len(changed)} control(s).")
    return len(changed)


def mirror_pose(scope: list[str], left_to_right: bool | None = None) -> int:
    """Mirrors the pose of scope onto the other side. left_to_right None lets the command pick the source side:
    the side of the controls when they share one, else Left. Returns how many controls changed."""
    kwargs = {} if left_to_right is None else {"leftToRight": left_to_right}
    changed = cmds.mirrorRigPose(*scope, **kwargs) or []
    bmaya.core.log.info(f"Mirrored the pose onto {len(changed)} control(s).")
    return len(changed)


def flip_pose(scope: list[str]) -> int:
    """Swaps the pose of each control in scope with its mirror. Returns how many controls changed."""
    changed = cmds.flipRigPose(*scope) or []
    bmaya.core.log.info(f"Flipped {len(changed)} control(s).")
    return len(changed)


def load_pose(scope: list[str], file: str, mirror: bool = False) -> list[str]:
    """Loads a ControlPose file onto scope (a rig root, or controls of one rig) in one undo step. mirror puts the file's
    Left side on the Right and its Right on the Left before it is written. Returns the controls it changed."""
    cmds.undoInfo(openChunk=True, chunkName="Load pose")
    try:
        changed = cmds.loadRigPose(*scope, file=file.replace("\\", "/"), mirror=mirror) or []
    finally:
        cmds.undoInfo(closeChunk=True)
    bmaya.core.log.info(f"Loaded the pose onto {len(changed)} control(s){' mirrored' if mirror else ''}: {file}")
    return changed


def load_animation(scope: list[str], file: str, offset: float = 0, mirror: bool = False) -> list[str]:
    """Loads a ControlAnim file onto scope in one undo step. The keys land on the frames they were saved on, moved by
    offset frames. mirror puts the file's Left side's keys on the Right and the Right's on the Left. Returns the
    controls it changed."""
    cmds.undoInfo(openChunk=True, chunkName="Load animation")
    try:
        changed = cmds.loadRigAnimation(*scope, file=file.replace("\\", "/"), offset=offset, mirror=mirror) or []
    finally:
        cmds.undoInfo(closeChunk=True)
    bmaya.core.log.info(f"Loaded the animation onto {len(changed)} control(s){' mirrored' if mirror else ''}: {file}")
    return changed


def zero_pose_interactive() -> None:
    zero_pose(get_scope())


def mirror_pose_interactive(left_to_right: bool | None = None) -> None:
    """Mirrors the pose across the rig. left_to_right None lets the command pick the source side: the side of the
    selected controls when they share one, else Left."""
    mirror_pose(get_scope(), left_to_right)


def flip_pose_interactive() -> None:
    flip_pose(get_scope())


def select_all_controls_interactive() -> None:
    """Selects every control of the active rig."""
    rig_root = bmaya.maya.activerig.get_active_rig().rig_root
    cmds.select(cmds.getRigControls(rig_root), replace=True)


def select_mirror_controls_interactive() -> None:
    """Selects the controls on the other side of the selected controls."""
    controls = cmds.ls(selection=True, type=rigmodules.query.RIG_CONTROL_TYPE)
    if not controls:
        raise RuntimeError("Select rig controls.")
    cmds.select([cmds.getRigMirrorControl(control) for control in controls], replace=True)


def key_all_controls_interactive() -> None:
    count = rigmodules.pose.key_rig(bmaya.maya.activerig.get_active_rig().rig_root)
    bmaya.core.log.info(f"Keyed {count} channel(s) on every control of the active rig.")


def key_selected_modules_interactive() -> None:
    rig_root = bmaya.maya.activerig.get_active_rig().rig_root
    modules = get_selected_modules(rig_root)
    count = rigmodules.pose.key_modules(rig_root, modules)
    bmaya.core.log.info(f"Keyed {count} channel(s) on the controls of {len(modules)} module(s).")
