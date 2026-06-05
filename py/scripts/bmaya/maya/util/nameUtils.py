"""Purpose:
Utility functions for working with names in maya. These are used by various components to perform common tasks 
that involve naming, such as naming joints and controls based on a consistent naming convention.
"""
import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.core import constants

def nameSelection(selection, name='joint', side='L', suffix='JNT'):
    
    if not selection:
        return
    
    selLen = len(selection)
    
    for i in range(selLen -1, -1, -1):
        newName = '_'.join([name, str(i).zfill(2), side, suffix])
        
        if cmds.objExists(newName) and newName not in selection:
            om.MGlobal.displayWarning('An object with the name \'{0}\' already exists'.format(newName))
        
        cmds.rename(selection[i], newName)

def findControlName(node, identifier=None):
        nodeSplit = node.split('_')
        if identifier:
            nodeSplit[0] += identifier

        ctrlName = '_'.join(nodeSplit[0:-1])
        
        ctrlName = '_'.join([ctrlName, constants.CTRL_SUFFIX])

        return ctrlName

def findJointName(node, identifier=None, count=0, suffix='DRIVER'):
    nodeSplit = node.split('_')
    if identifier:
        nodeSplit[0] += identifier
    if isinstance(count, int):
        nodeSplit[1] = str(count).zfill(2)
    
    jntName = '_'.join(nodeSplit[0:-1])

    suffix = suffix.replace('_', '')
    
    jntName = jntName + '_' + suffix

    return jntName


