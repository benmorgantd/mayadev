import maya.cmds as cmds

def toggleSkinMode():
    """Toggles skinning mode on the currently built rig."""
    
    characterNodes = cmds.ls('*.referenceMesh')
    
    for node in characterNodes:
        currentValue = cmds.getAttr(node)
        cmds.setAttr(node, not currentValue)
        cmds.setAttr('SKELETON.visibility', currentValue)
    