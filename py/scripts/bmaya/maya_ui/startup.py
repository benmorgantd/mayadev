"""The UI layer's registration pass: fills the slots a GUI session adds, in bmaya.core and bmaya.maya.

userSetup.py calls register() after bmaya.maya.startup.register(), and only when Maya isn't in batch. Nothing else
fills a slot (RigModules design/mayadev-ui.md, D49).
"""

from __future__ import annotations

import bmaya.core.prompts
import bmaya.maya.devreload
import bmaya.maya_ui.host
import bmaya.maya_ui.menus
import bmaya.maya_ui.prompter


def register() -> None:
    """Fills the slots for a GUI session. Safe to call again: each call replaces what the last one registered."""
    bmaya.core.prompts.register_prompter(
        bmaya.maya_ui.prompter.QtPrompter(parent_window=bmaya.maya_ui.host.parent_window))
    bmaya.maya.devreload.register_hooks(
        before_unload=bmaya.maya_ui.menus.delete_plugin_menus,
        after_load=bmaya.maya_ui.menus.build_menus,
    )
