import json
import inspect

import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.core import constants, name
from bmaya.rigging.shapes import shapelib

from decorators import wrapBuild

class Module(object):

    mirrorPairs = {'L': 'R', 'R': 'L', 'M': None}

    def __init__(self, character=None, name='module1', modType='Module', parent=None, side='L', 
                 mirror=False, shapeType='cube', alignWorld=None):

        self.character = character

        self.name = name
        self.modType = modType
        self.parent = self.determineParent(parent)
        self.side = side
        self.mirror = mirror
        self.shapeType = shapeType
        self.alignWorld = alignWorld

        self.components = []
        self.bindJoints = []

    @property
    def dict(self):
        return {key: value for key, value in self.__dict__.items() if '__' not in key}

    def build(self):
        # should get overridded by child class
        return

    def makeNode(self):
        # create the module node before anything gets built. 
        if not cmds.objExists(self.name + '_MOD'):
            # this creates a locator shape of the given name
            self.node = cmds.createNode('network', name=self.name + '_MOD')
            # holds all the parts of the module. Not for transforming
            self.modGrp = cmds.createNode('transform', name=self.name + '_GRP')
            # holds the components of the node. Transform this should not result in double xforms
            self.componentsGrp = cmds.createNode('transform', name=self.name + '_COMPONENTS')
            # holds the driver joints for the node
            self.driverGrp = cmds.createNode('transform', name=self.name + '_DRIVERS')
            cmds.hide(self.driverGrp)
            cmds.parent(self.driverGrp, self.componentsGrp)

            # print '>>> Created {0} node >> {1} <<'.format(self.modType, self.node)
        else:
            raise RuntimeError('Module of name {0} already exists.'.format(self.name + '_MOD'))
    
    def parseForMayaAttr(self, attr):

        if isinstance(attr, bool):
            mayaAttrType = 'bool'
            mayaAttrVal = attr

        elif isinstance(attr, basestring):
            mayaAttrType = 'string'
            mayaAttrVal = str(attr)

        elif isinstance(attr, list):
                cleanList = []

                for val in attr:
                    if isinstance(val, (basestring, int, float, bool)):
                        cleanList.append(val)
                    elif isinstance(val, shapelib.Shape):
                        cleanList.append(val.ctrl)

                mayaAttrType = 'string'
                mayaAttrVal = json.dumps(cleanList)

        elif isinstance(attr, dict):
            cleanDict = {}

            for key, value in attr.items():
                if isinstance(value, (basestring, int, float, bool)):
                    cleanDict[key] = value
                elif isinstance(value, shapelib.Shape):
                    cleanDict[key] = value.ctrl

            mayaAttrType = 'string'
            mayaAttrVal = json.dumps(cleanDict)
        
        elif not attr:
            mayaAttrType = 'string'
            mayaAttrVal = 'None'
        
        elif isinstance(attr, shapelib.Shape):
            mayaAttrType = 'string'
            mayaAttrVal = attr.ctrl
        
        else:
            mayaAttrType = 'string'
            mayaAttrVal = str(attr)

        return mayaAttrType, mayaAttrVal    

    def addNodeAttrs(self):
        if not self.node:
            raise RuntimeError('Module node does not exist yet for ' + self.name)

        for attrName, attrVal in self.__dict__.items():
            attrType = type(attrVal)
            
            mayaAttrType, mayaAttrVal = self.parseForMayaAttr(attrVal)

            # add the attribute
            
            if mayaAttrType == 'string':
                cmds.addAttr(self.node, ln=attrName, dt='string', keyable=False)
                cmds.setAttr(self.node + '.' + attrName, mayaAttrVal, type='string')
            elif mayaAttrType == 'bool':
                cmds.addAttr(self.node, ln=attrName, at='bool', dv=mayaAttrVal, keyable=False)
            elif mayaAttrType == 'message':
                cmds.addAttr(self.node, ln=attrName, at=mayaAttrType, keyable=False)
            else:
                try:
                    cmds.addAttr(self.node, ln=attrName, at=mayaAttrType, dv=mayaAttrVal, keyable=False)
                except TypeError:
                    print '--'
                    print 'type: ', mayaAttrType
                    print 'value: ', mayaAttrVal
                    print 'Warning: Failed to add attribute \'{0}\'\n--'.format(attrName)

    def findMirror(self, node):
        """Returns the mirrored node of the same type if it's in the scene.
        Else returns None"""

        if isinstance(node, (int, float)):
            # TODO: we could be mirroring vectors here maybe
            return node
        elif not node:
            return None
        
        mirrorSide = Module.mirrorPairs[self.side]

        if node in ['R', 'L']:
            return mirrorSide

        mirrorNode = node.replace(('_' + self.side + '_'), ('_' + mirrorSide + '_'))

        try:
            nodeType = cmds.objectType(node)
        except RuntimeError:
            return mirrorNode

        if mirrorNode in cmds.ls(type=nodeType):
            return mirrorNode
        else:
            return None

    def doMirror(self):

        if self.mirror:
            # get all the arguments needed to build self and find their mirrors 
            # before creating the instance
        
            mirroredInitArgs = {}

            for attr in inspect.getargspec(self.__init__).args:
                try:
                    value = getattr(self, attr)
                except AttributeError:
                    # could be trying to get the value of 'self'
                    continue

                if isinstance(value, basestring):
                    mirroredInitArgs[attr] = self.findMirror(value)
        
                elif isinstance(value, list):
                    mirrorList = []
                    for j in value:
                        mirrorList.append(self.findMirror(j))
                    mirroredInitArgs[attr] = mirrorList

                else:
                    mirroredInitArgs[attr] = value

            # we don't want to worry about a name convention for mirrored modules
            mirroredInitArgs['name'] = self.name + '_mirror'
            mirroredInitArgs['mirror'] = False

            mirrorSelf = self.__class__()

            for arg in mirroredInitArgs.keys():
                if arg != 'parent':
                    setattr(mirrorSelf, arg, mirroredInitArgs[arg])

            # set attribute manually for parent so that we know it has the startJoint variable set
            setattr(mirrorSelf, 'parent', mirrorSelf.determineParent(mirrorSelf.parent))

            mirrorSelf.build()
        
            return mirrorSelf
        else:
            return None

    def determineParent(self, parent):
        if parent and cmds.objExists(parent):
            return parent
        elif hasattr(self, 'startJoint'):
            parentTransform = cmds.listRelatives(self.startJoint, parent=True, type='joint')
            if parentTransform:
                parentTransform = parentTransform[0]
            else:
                parentTransform = constants.BOTTOM_LAYOUT_CONTROL
            
            return parentTransform
        else:
            return constants.BOTTOM_LAYOUT_CONTROL

    def parentModule(self):
        # check if a specific joint parent was given. If not then check the parent of the startJoint
        # This means every module except Root will need a startJoint

        if self.modType == 'Layout':
            cmds.parent(self.componentsGrp, self.modGrp)
            cmds.parent(self.modGrp, self.character.modulesGrp)
            return

        # parent the whole module's group into the module group for the character
        cmds.parent(self.modGrp, self.character.modulesGrp)
        cmds.parent(self.componentsGrp, self.modGrp)

        # we might give it a specific joint parent
        if self.parent:
            self.parentConstrain(self.parent, self.modGrp, maintainOffset=True)
        elif hasattr(self, 'startJoint'):
            parentTransform = cmds.listRelatives(self.startJoint, parent=True, type='joint')
            if parentTransform:
                parentTransform = parentTransform[0]
            else:
                parentTransform = constants.BOTTOM_LAYOUT_CONTROL

            # todo: this is where you could add a followSwitch option
            self.parentConstrain(parentTransform, self.modGrp, maintainOffset=True)
            
        elif self.modType != 'Layout':
            raise RuntimeError('Module must have a start joint.')

    def parentConstrain(self, parent=None, childList=None, maintainOffset=True):
        
        if isinstance(childList, basestring):
            childList = [childList]

        for child in childList:
            cmds.parentConstraint(parent, child, mo=maintainOffset)

    def lockTransforms(self, ctrls, attrs=['translate', 'rotate', 'scale'], lock=True):
        if isinstance(ctrls, basestring):
            ctrls = [ctrls]

        for ctrl in ctrls:
            for attr in attrs:
                if attr in ['translate', 'rotate', 'scale']:
                    for axis in ['X', 'Y', 'Z']:
                        cmds.setAttr('{0}.{1}{2}'.format(ctrl, attr, axis),
                                     lock=lock, keyable=False, channelBox=False)
                else:
                    cmds.setAttr('{0}.{1}'.format(ctrl, attr),
                                  lock=lock, keyable=False, channelBox=False)

    def checkContract(self):
        # TODO: Check by attribute types
        return True

        if not self.contract:
            return True

        nullValues = [v for v in self.contract if not v]

        if nullValues:
            raise RuntimeError('Contract for {0} not yet fulfilled.'.format(self.name))
        
        print '>>> Contract for {0} fulfilled'.format(self.modType)
        return True

    def connectComponents(self):
        """Connects the module's compenents to the module"""
        
        for ctrl in self.components:
            if not cmds.objExists(ctrl.ctrl + '.module'):
                cmds.addAttr(ctrl.ctrl, longName='module', attributeType='message')

            cmds.connectAttr(self.node + '.components', ctrl.ctrl + '.module', force=True)

            self.lockTransforms(ctrl.offsetGrp)

    def connectBindJoints(self):
        """Connects the module's bind joints to their control"""
        
        for jnt in self.bindJoints:
            if not cmds.objExists(jnt + '.module'):
                cmds.addAttr(jnt, longName='module', attributeType='message')
            else:
                raise RuntimeError('{0} already belongs to a module'.format(jnt))

            cmds.connectAttr(self.node + '.bindJoints', jnt + '.module')

    def findHierarchyJoints(self, shortestDistance=False, startJoint=None, endJoint=None):
        """Expands from a start joint and until it hits excluded joints."""

        if not startJoint:
            startJoint = self.startJoint
        if not endJoint:
            endJoint = self.endJoint

        sel = om.MSelectionList()
        bindJoints = []
        exclude = []

        if not startJoint:
            raise RuntimeError('Need a start joint.')
        if hasattr(self, 'exclude'):
            exclude = self.exclude

        sel.add(startJoint)
        dag = om.MDagPath()
        sel.getDagPath(0, dag)

        rootJnt = True

        itDag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kJoint)
        itDag.reset(dag, om.MItDag.kDepthFirst, om.MFn.kJoint)

        while not itDag.isDone():
            jnt = itDag.partialPathName()

            if jnt not in exclude:
                if jnt != endJoint:
                    jntChildren = cmds.listRelatives(jnt, type='joint', children=True, allDescendents=True) or []
                    if shortestDistance and endJoint not in jntChildren:
                        itDag.prune()
                    else:
                        bindJoints.append(jnt)
                else:
                    # add control on end joint then prune
                    bindJoints.append(jnt)
                    itDag.prune()
                rootJnt = False
            else:
                itDag.prune()

            itDag.next()
        
        return bindJoints

    def createDriveJoint(self, jnt, label='Driver', constrain=True):
        driver = cmds.duplicate(jnt, parentOnly=True, name=jnt.replace(constants.JOINT_SUFFIX, label))[0]
            
        jointParent = cmds.listRelatives(jnt, parent=True, type='joint')
        
        if jointParent:
            driverParent = jointParent[0].replace(constants.JOINT_SUFFIX, label)
            if cmds.objExists(driverParent):
                cmds.parent(driver, driverParent, absolute=True)

        if constrain:
            self.parentConstrain(driver, jnt, maintainOffset=False)

            # add a connection for driver and driven joint
            # only add this attribute if it's a direct constraint
            cmds.addAttr(jnt, longName='driver', attributeType='message')
            cmds.addAttr(driver, longName='driven', attributeType='message')
            cmds.connectAttr(driver + '.driven', jnt + '.driver')

        return driver

    def createDriveJoints(self, label='DRIVER', constrain=True):
        driveJoints = []

        for joint in self.bindJoints:
            driveJoints.append(self.createDriveJoint(joint, label=label, constrain=constrain))

        cmds.parent(driveJoints[0], self.driverGrp)
        
        return driveJoints

    def makeIkHandle(self, startJoint, endJoint, solverType, name):

        ik = cmds.ikHandle(startJoint=startJoint, endEffector=endJoint,
                          name=name, solver=solverType)[0]

        grp = cmds.group(empty=True, name=name + '_grp')

        cmds.delete(cmds.parentConstraint(ik, grp, maintainOffset=False))

        cmds.parent(ik, grp)

        return [ik, grp]

        
    def getDriver(self, joint):

        if 'driver' in cmds.listAttr(joint):
            driver = cmds.listConnections(joint + '.driver', source=True)
            if driver:
                return driver[0]
            else:
                raise ValueError('Driver connection lost on {0}'.format(joint))
        else:
            raise ValueError('Given joint {0} has no direct driver.'.format(joint))


    def blendChains(self, fkChain, ikChain, childChain, driveAttribute):

        # create the reverse node (name is now more vague)
        reverse = cmds.createNode('reverse', name=childChain[0] + '_REV')
        cmds.connectAttr(driveAttribute, reverse + '.inputX')
        reverseAttr = reverse + '.outputX'

        for i in range(len(fkChain)):
            const = cmds.parentConstraint(fkChain[i], ikChain[i], childChain[i], maintainOffset=True)[0]
            
            cmds.connectAttr(reverseAttr, '{0}.{1}W0'.format(const, fkChain[i]))
            cmds.connectAttr(driveAttribute, '{0}.{1}W1'.format(const, ikChain[i]))
            
            # set interpolation type to Shortest
            cmds.setAttr(const + '.interpType', 2)

            self.messageConnect(childChain[i], fkChain[i], 'fkDriver', 'driven')
            self.messageConnect(childChain[i], ikChain[i], 'ikDriver', 'driven')

        return reverseAttr
            
            # TODO: add a drive attribute on the module

    def messageConnect(self, nodeA, nodeB, longNameA, longNameB):
        
        if longNameA not in cmds.listAttr(nodeA):
            cmds.addAttr(nodeA, longName=longNameA, attributeType='message')
        if longNameB not in cmds.listAttr(nodeB):
            cmds.addAttr(nodeB, longName=longNameB, attributeType='message')

        cmds.connectAttr('{0}.{1}'.format(nodeA, longNameA), 
                         '{0}.{1}'.format(nodeB, longNameB))


    def captureComponentDefaults(self):
        # get the controls that are in the module
        for component in self.components:
            cmds.addAttr(component.ctrl, longName='defaultValues', dt='string')

            defaultValues = {}

            for attr in cmds.listAttr(component.ctrl, keyable=True):
                defaultValues[attr] = cmds.getAttr('{0}.{1}'.format(component.ctrl, attr))

            cmds.setAttr(component.ctrl + '.defaultValues', json.dumps(defaultValues), type='string')

        # capture defaults for keyable module attributes as well
        cmds.addAttr(self.node, longName='defaultValues', dt='string')

        defaultValues = {}

        for attr in cmds.listAttr(self.node, keyable=True) or []:
            defaultValues[attr] = cmds.getAttr('{0}.{1}'.format(self.node, attr))

        cmds.setAttr(self.node + '.defaultValues', json.dumps(defaultValues), type='string')
    
    def findJointName(self, node, identifier=None, count=0, suffix='DRIVER'):
        nodeSplit = node.split('_')
        if identifier:
            nodeSplit[0] += identifier
        if isinstance(count, int):
            nodeSplit[1] = str(count).zfill(2)
        
        jntName = '_'.join(nodeSplit[0:-1])

        suffix = suffix.replace('_', '')
        
        jntName = jntName + '_' + suffix

        return jntName


    def setupAlignWorld(self, component, defaultValue=0):
        if self.alignWorld == None:
            return

        const = cmds.orientConstraint(constants.BOTTOM_LAYOUT_CONTROL, component.spaceGrp, mo=1)[0]
        cmds.setAttr(const + '.interpType', 2)

        cmds.addAttr(component.ctrl, longName='alignWorld', defaultValue=defaultValue,
                     attributeType='bool', keyable=True)

        cmds.connectAttr(component.ctrl + '.alignWorld', const + '.' + constants.BOTTOM_LAYOUT_CONTROL + 'W0')

    def findTwistJoints(self, jnt):
        children = cmds.listRelatives(jnt, type='joint', children=True)

        twistJoints = []

        for c in children:
            if 'Twist' in c:
                twistJoints.append(c)
                
        # will ascend 00 -> 0x
        twistJoints.sort()

        return twistJoints