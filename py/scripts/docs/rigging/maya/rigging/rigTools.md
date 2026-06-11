Here is the Markdown documentation for the `rigTools` module:

# Module: rigTools
## Purpose:
Utility functions for working with rigs in maya. These are used by the rig components and postops to perform common tasks on rigs, such as toggling skinning mode, matching ik to fk, etc.

## Technical Implementation:
The `rigTools` module is designed to provide a set of utility functions that can be used to interact with Maya rigs. The functions in this module are used by the rig components and postops to perform common tasks on rigs, such as toggling skinning mode, matching ik to fk, etc.

## Overview:
The `rigTools` module provides a set of functions that can be used to work with Maya rigs. These functions include:

* `toggle_skin_mode()`: Toggles skinning mode on the currently built rig.
* `size_joints()`: Sizes the joints in the rig based on their type and location.
* `label_joints()`: Labels the joints in the rig with their corresponding names.
* `get_module_node(ctrl)`: Returns the module node associated with a given control.
* `get_character_node(ctrl)`: Returns the character node associated with a given control.
* `get_character_modules(characterNode)`: Returns a list of modules associated with a given character node.
* `reset_control(ctrl)`: Resets the attributes of a given control to their default values.
* `reset_module(mod)`: Resets the attributes of a given module to their default values.
* `reset_character(ctrl)`: Resets the attributes of a given character to their default values.
* `select_module(ctrl)`: Selects a given module in the Maya scene.
* `key_all(ctrl)`: Sets keyframes for all attributes of a given control.
* `key_ik(ctrl)`: Sets keyframes for the ik controls associated with a given control.
* `key_fk(ctrl)`: Sets keyframes for the fk controls associated with a given control.
* `match_ik_to_fk(ctrl)`: Matches the ik controls to the fk controls in a given rig.
* `match_fk_to_ik(ctrl)`: Matches the fk controls to the ik controls in a given rig.
* `bake_fk_to_ik(ctrl, bakeRange=None)`: Bakes the fk controls to the ik controls in a given rig over a specified time range.
* `bake_ik_to_fk(ctrl, bakeRange=None)`: Bakes the ik controls to the fk controls in a given rig over a specified time range.

## Cross-Module Dependencies:
* `bmaya.core.log`: Provides logging functionality for the module.
* `bmaya.core.constants`: Provides constants and utility functions for working with Maya rigs.
* `mayajs.cmds`: Provides access to the Maya cmds API.
* `mathUtils`: Provides mathematical utility functions for working with Maya rigs.

Note: The `rigTools` module is designed to be used in conjunction with other modules in the `bmaya` package, such as the `core` and `maya` modules.