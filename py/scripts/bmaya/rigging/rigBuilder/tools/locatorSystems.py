import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.core import mayanode
#reload(mayanode)

"""
Locator Systems are classes that can be used to create module build data 
from scratch or from existing locators.
"""


class LocatorSystem(object):
    def __init__(self, moduleName, parentSystem=None, parentLocator=None, 
                locatorData=None, side='L'):
        self.moduleName = moduleName
        self.parentSystem = parentSystem

        self.parentLocator = None
        if parentLocator:
            if isinstance(parentLocator, basestring):
                self.parentLocator = mayanode.Locator(parentLocator)
            elif isinstance(parentLocator, mayanode.Locator):
                self.parentLocator = parentLocator
        self.locatorData = locatorData
        self.side = side
        self.attachmentPoints = {}
        self.locators = {}

        self.setup()

    @property
    def moduleType(self):
        if cmds.objExists(self.moduleName + '.moduleType'):
            return cmds.getAttr(self.moduleName + '.moduleType')
        else:
            return None

    @moduleType.setter
    def moduleType(self, value):
        if not cmds.objExists(self.moduleName + '.moduleType'):
            cmds.addAttr(self.systemGroup.name, longName='moduleType', dataType='string')

        cmds.setAttr(self.systemGroup.name + '.moduleType', value, type='string')

    @property
    def data(self):
        data = {}

        for locator in self.locators.keys():
            # get information from the Transform and Locator objects in self.locators
            thisLocatorDict = {}
            # the maya name for this locator
            thisLocatorDict['name'] = self.locators[locator].name
            thisLocatorDict['parent'] = self.locators[locator].parent.name or None
            worldPosition = self.locators[locator].worldPosition
            thisLocatorDict['worldPosition'] = [worldPosition.x, worldPosition.y, worldPosition.z]
            quaternion = self.locators[locator].quaternion
            thisLocatorDict['worldRotation'] = [quaternion.x, quaternion.y, quaternion.z, quaternion.w]
            thisLocatorDict['scale'] = self.locators[locator].scale

            data[locator] = thisLocatorDict

        return data

    def setup(self):
        
        # Create the system group node
        if not cmds.objExists(self.moduleName):
            systemGroup = cmds.createNode('transform', name=self.moduleName)
        else:
            systemGroup = self.moduleName

        if self.locatorData and self.locatorData['systemGroup']:
            self.systemGroup = self.makeTransform(self.locatorData['systemGroup'])
        else:
            self.systemGroup = mayanode.Transform(systemGroup)

        self.locators['systemGroup'] = self.systemGroup

        self.moduleType = self.__class__.__name__

        # Subclasses would then declare their class's locators

    def makeTransform(self, data):
        xform = mayanode.Transform(name=data['name'])
        xform.parent = data['parent']
        xform.worldPosition = data['worldPosition']
        xform.quaternion = data['worldRotation']
        xform.scale = data['scale']

        return xform

    def makeLocator(self, data):
        loc = mayanode.Locator(name=data['name'])
        loc.parent = data['parent']
        loc.worldPosition = data['worldPosition']
        loc.quaternion = data['worldRotation']
        loc.scale = data['scale']

        return loc
    
    def makeJoint(self, count, matchWith, rotateOrder='xyz', suffix='JNT'):
        # we can change this method to change naming conventions
        # We'll always use the module name and the module's side in this convention
        cmds.select(clear=True)
        name = '_'.join([self.moduleName, str(count).zfill(2), self.side, suffix])

        jnt = cmds.joint(name=name, rotationOrder=rotateOrder, radius=1)
        cmds.delete(cmds.parentConstraint(matchWith, jnt, maintainOffset=False))
        cmds.makeIdentity(jnt, apply=True, translate=True, rotate=True)

        return jnt


class SingleJoint(LocatorSystem):
    def __init__(self, moduleName, parentSystem=None, parentLocator=None, 
                locatorData=None, side='L'):
        super(SingleJoint, self).__init__(moduleName, parentSystem, parentLocator, 
                                          locatorData, side)

        if not self.locatorData:
            # Initiate from scratch with no existing data
            self.startLocator = mayanode.Locator(name=self.moduleName + 'Start')
            self.startLocator.parent = self.moduleName

        elif isinstance(self.locatorData, dict):
            # initiating from data loaded from a single joint module
            self.startLocator = self.makeLocator(self.locatorData['startLocator'])

        self.locators['startLocator'] = self.startLocator

    def toJoints(self, rotateOrder='xyz'):
        """Make the resulting bind joints for this system"""

        if not cmds.objExists('SKELETON'):
            cmds.createNode('transform', name='SKELETON')

        cmds.select(clear=True)

        # we could always name these joints using a different convention now
        startJoint = self.makeJoint(0, self.startLocator.name, rotateOrder=rotateOrder)

        # *** give the pairing of this new joint to what locator it was made from
        self.attachmentPoints[self.startLocator.name] = startJoint

        if self.parentSystem and self.parentLocator:
            cmds.parent(startJoint, self.parentSystem.attachmentPoints[self.parentLocator.name])
        else:
            cmds.parent(startJoint, 'SKELETON')

