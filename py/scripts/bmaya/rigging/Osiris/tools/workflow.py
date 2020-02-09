import json

import time

import maya.cmds as cmds


def toggleSkinMode():
    """Toggles skinning mode on the currently built rig."""
    
    characterNodes = cmds.ls('*.referenceMesh')
    
    for node in characterNodes:
        currentValue = cmds.getAttr(node)
        cmds.setAttr(node, not currentValue)
        cmds.setAttr('SKELETON.visibility', currentValue)


def getModuleNode(ctrl):
    if 'module' not in cmds.listAttr(ctrl):
        if any(attr in ['node', 'modType'] for attr in cmds.listAttr(ctrl)):
            # ctrl is a module
            return ctrl
        else:
            raise ValueError('Given control {0} is not connected to a module'.format(ctrl))
        
    mod = cmds.listConnections(ctrl + '.module')[0]

    return mod

def getCharacterNode(ctrl):

    mod = getModuleNode(ctrl)

    character = cmds.listConnections(mod + '.character')[0]

    return character

def getCharacterModules(characterNode):
    return cmds.listConnections(characterNode + '.modules')


def resetControl(ctrl):
    if 'defaultValues' not in cmds.listAttr(ctrl):
        raise ValueError('Control {0} has no default value attribute'.format(ctrl))
    
    defaultValues = cmds.getAttr(ctrl + '.defaultValues')
    
    defaultValues = json.loads(defaultValues)
    
    for attr, value in defaultValues.items():
        cmds.setAttr('{0}.{1}'.format(ctrl, attr), value)

def resetModule(mod):
    components = cmds.listConnections(mod + '.components')
    
    for component in components:
        resetControl(component)

    if 'defaultValues' not in cmds.listAttr(mod):
        raise ValueError('Module {0} has no default value attribute'.format(mod))
    
    defaultValues = cmds.getAttr(mod + '.defaultValues')
    
    defaultValues = json.loads(defaultValues)
    
    for attr, value in defaultValues.items():
        cmds.setAttr('{0}.{1}'.format(mod, attr), value)

def resetCharacter(ctrl):
    character = getCharacterNode(ctrl)

    modules = getCharacterModules(character)

    for module in modules:
        resetModule(module)