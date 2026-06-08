"""Purpose:
Utility functions for working with selections in maya. These are used by various components to perform common tasks that involve selections,
such as getting the selected joints, etc.
"""
import maya.cmds as cmds


def getSelection(ofType=None):
    return cmds.ls(
        selection=True,
        type=ofType) if ofType is not None else cmds.ls(
        selection=True)


sl1 = getSelection()[0]
selected = getSelection()
selectedJoints = getSelection(ofType='joint')
selectedTransforms = getSelection(ofType='transform')
