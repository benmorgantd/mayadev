import maya.cmds as cmds
import maya.OpenMaya as om


def nameSelection(selection, name='joint', side='L', type='JNT'):
    
    if not selection:
        return
        
    
    selLen = len(selection)
    
    for i in range(selLen -1, -1, -1):
        newName = '_'.join([name, str(i).zfill(2), side, type])
        
        if cmds.objExists(newName) and newName not in selection:
            om.MGlobal.displayWarning('An object with the name \'{0}\' already exists'.format(newName))
        
        cmds.rename(selection[i], newName)
        
        