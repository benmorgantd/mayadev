import json
import os

import maya.cmds as cmds
from bmaya.core import mayanode
#reload(mayanode)

import locatorSystems
#reload(locatorSystems)

def load(filepath):

    if not os.path.exists(filepath):
        raise RuntimeError('Filepath does not exist.')
    
    with open(filepath, "r") as f:
        buildData = json.load(f)

    return buildData

def save(filepath, data):

    if not os.path.exists(os.path.dirname(filepath)):
        raise RuntimeError('Filepath does not exist.')

    with open(filepath, "w+") as f:
        json.dump(data, f, separators=(', ', ':'), indent=2, sort_keys=True)

def initLocatorsFromData(buildData):

    cmds.file(new=True, force=True)

    systems = []

    cmds.createNode('transform', name='Locators')
    # if we flattened our dictionary, this is the index this system would be at

    def loadChildren(module, parentSystem):
        for child in module['children']:
            systemName = child['name']
            systemType = child['modType']
            parentLocator = child['parent']
            systemLocators = child['locators']
            systemSide = child['side']

            # build a locator system of that type
            system = getattr(locatorSystems, systemType)(systemName, parentSystem, parentLocator,
                                                         systemLocators, systemSide)

            systems.append(system)

            loadChildren(child, system)

    for topLevelModule in buildData:
        systemName = topLevelModule['name']
        systemType = topLevelModule['modType']
        systemLocators = topLevelModule['locators']
        systemSide = topLevelModule['side']

        # build a locator system of that type
        system = getattr(locatorSystems, systemType)(systemName, None, None, systemLocators, systemSide)

        systems.append(system)

        if topLevelModule['children']:
            loadChildren(topLevelModule, system)

    return systems

def saveLocatorData(locatorSystems, buildData):
    modifiedData = buildData

    def addChildren(module, system):
        for child in module['children']:
            if child['name'] == system.moduleName:
                child['locators'] = system.data
                return
            else:
                addChildren(child, system)

    for system in locatorSystems:
        for topLevelModule in modifiedData:
            if topLevelModule['name'] == system.moduleName:
                topLevelModule['locators'] = system.data
            elif topLevelModule['children']:
                addChildren(topLevelModule, system)
    
    return modifiedData

def convertLocatorSystemsToJoints(locatorSystems):
    for system in locatorSystems:
        system.toJoints()

    cmds.delete('Locators')