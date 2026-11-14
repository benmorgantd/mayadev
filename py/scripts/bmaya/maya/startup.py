"""The Maya layer's registration pass: fills the slots bmaya.core declares with Maya's implementations.

userSetup.py calls register() once per session, before bmaya.maya_ui.startup.register(). Nothing else fills a
slot, so every link from a lower layer to a higher one is in this file or in bmaya.maya_ui.startup (RigModules
design/mayadev-ui.md, D49). A slot's default works with nothing registered, so plain Python and tests skip this.
"""

from __future__ import annotations

import logging

import maya.api.OpenMaya as om
import maya.cmds as cmds

import bmaya.core.log


def register() -> None:
    """Fills core's slots for this session. Safe to call again: each call replaces what the last one registered.

    A GUI session logs to the script editor through MGlobal. A batch session keeps stdout, the default, which the
    batch framework captures."""
    if cmds.about(batch=True):
        bmaya.core.log.reset_writers()
        return
    bmaya.core.log.register_writers({
        logging.INFO: om.MGlobal.displayInfo,
        logging.WARNING: om.MGlobal.displayWarning,
        logging.ERROR: om.MGlobal.displayError,
    })
