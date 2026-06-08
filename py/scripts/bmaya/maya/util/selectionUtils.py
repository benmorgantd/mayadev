"""Purpose:
Utility functions for working with selections in maya. These are used by various components to perform common tasks that involve selections,
such as getting the selected joints, etc.
"""

import maya.cmds as cmds


def get_selection(ofType=None):
    return (
        cmds.ls(selection=True, type=ofType)
        if ofType is not None
        else cmds.ls(selection=True)
    )


sl1 = lambda: get_selection()[0]
selected = lambda: get_selection()
