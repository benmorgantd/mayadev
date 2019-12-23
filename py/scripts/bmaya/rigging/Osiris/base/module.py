import json
import inspect

import maya.cmds as cmds
import maya.OpenMaya as om

# from .character import Character
from bmaya.rigging.shapes import shapelib

from decorators import wrapBuild

reload(shapelib)


class Module(object):

    mirrorPairs = {'L': 'R', 'R': 'L', 'M': None}

    def __init__(self, character=None, name='module1', modType='Module', parent=None, side='L', 
                 mirror=False, shapeType='cube', alignWorld=False):

        self.character = character

        self.name = name
        self.modType = modType
        self.parent = parent
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
            self.modGrp = cmds.createNode('transform', name=self.name + '_GRP')
            print '>>> Created {0} node >> {1} <<'.format(self.modType, self.node)
        else:
            raise RuntimeError('Module of name {0} already exists.'.format(self.name + '_MOD'))

    def addNodeAttrs(self):
        if not self.node:
            raise RuntimeError('Module node does not exist yet for ' + self.name)

        for attr in self.__dict__:
            attrVal = self.__dict__[attr]

            if isinstance(attrVal, bool):
                attrType = 'bool'
                attrVal = attrVal

            # elif isinstance(attrVal, Character):
            #     attrType = 'message'

            elif isinstance(attrVal, basestring):
                attrType = 'string'
                attrVal = str(attrVal)

            elif isinstance(attrVal, list):
                cleanList = []

                for val in attrVal:
                    if isinstance(val, (basestring, int, float, bool)):
                        cleanList.append(val)
                    # creates a circular import
                    # elif isinstance(val, Character):
                    #     cleanList.append(val.name)
                    elif isinstance(val, shapelib.Shape):
                        cleanList.append(val.ctrl)

                attrType = 'string'
                attrVal = json.dumps(cleanList)

            elif isinstance(attrVal, dict):
                cleanDict = {}

                for key in attrVal:
                    if isinstance(val, (basestring, int, float, bool)):
                        cleanDict[key] = attrVal[key]
                    # elif isinstance(attrVal[key], Character):
                    #     cleanDict[key] = attrVal[key].name
                    elif isinstance(attrVal[key], shapelib.Shape):
                        cleanDict[key] = attrVal[key].ctrl

                attrType = 'string'
                attrVal = json.dumps(cleanDict)
            
            elif not attrVal:
                attrType = 'string'
                attrVal = 'None'

            # add the attribute
            
            if attrType is 'string':
                cmds.addAttr(self.node, ln=attr, dt='string', keyable=False)
                cmds.setAttr(self.node + '.' + attr, str(attrVal), type='string')
            elif attrType is 'message':
                cmds.addAttr(self.node, ln=attr, at=attrType, keyable=False)
            else:
                try:
                    cmds.addAttr(self.node, ln=attr, at=attrType, dv=attrVal, keyable=False)
                except TypeError:
                    print '--'
                    print 'type: ', attrType
                    print 'value: ', attrVal
                    print 'Warning: Failed to add attribute \'{0}\'\n--'.format(attr)

    def findMirror(self, node):
        """Returns the mirrored node of the same type if it's in the scene.
        Else returns None"""

        if not node:
            print 'No mirror node found since given node was None'
            return None

        mirrorSide = Module.mirrorPairs[self.side]

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
            print '>>> Mirroring ' + self.name

            # get all the arguments needed to build self and find their mirrors 
            # before creating the instance
        
            mirroredInitArgs = {}

            for attr in inspect.getargspec(self.__init__).args:
                try:
                    value = getattr(self, attr)
                except AttributeError:
                    # could be trying to get the value of 'self'
                    continue

                print attr
        
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
            mirroredInitArgs['name'] = self.name + '_MIRROR'
            mirroredInitArgs['mirror'] = False

            mirrorSelf = self.__class__(**mirroredInitArgs)
        
            mirrorSelf.build()
        
            return mirrorSelf

        else:
            return None

    def parentModule(self):
        # check if a specific joint parent was given. If not then check the parent of the startJoint
        # This means every module except Root will need a startJoint

        # parent the whole module's group into the module group for the character
        cmds.parent(self.modGrp, self.character.modulesGrp)

        # we might give it a specific joint parent
        if self.parent:
            self.parentConstrain(self.parent, self.modGrp, maintainOffset=True)
        elif hasattr(self, 'startJoint'):
            parentJoint = cmds.listRelatives(
                self.startJoint, parent=True, type='joint') or 'layout_03_M_ctrl'

            # todo: this is where you could add a followSwitch option
            self.parentConstrain(parentJoint, self.modGrp, maintainOffset=True)
            
        elif self.modType != 'Root':
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

            cmds.connectAttr(self.node + '.components', ctrl.ctrl + '.module')

            self.lockTransforms(ctrl.offsetGrp)

    def connectBindJoints(self):
        """Connects the module's bind joints to their control"""
        
        for jnt in self.bindJoints:
            if not cmds.objExists(jnt + '.module'):
                cmds.addAttr(jnt, longName='module', attributeType='message')
            else:
                raise RuntimeError('{0} already belongs to a module'.format(jnt))

            cmds.connectAttr(self.node + '.bindJoints', jnt + '.module')

    def getContainedJoints(self):
        """Finds the joints between a start and end point on a dag"""

        sel = om.MSelectionList()

        if not self.startJoint:
            raise RuntimeError('Need a start joint.')

        sel.add(self.startJoint)
        dag = om.MDagPath()
        sel.getDagPath(0, dag)

        rootJnt = True

        itDag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kJoint)
        itDag.reset(dag, om.MItDag.kDepthFirst, om.MFn.kJoint)

        while not itDag.isDone():
            jnt = itDag.partialPathName()

            if jnt not in self.exclude:

                self.bindJoints.append(jnt)

                rootJnt = False

            else:
                itDag.prune()

            itDag.next()

    def checkContractJoint(self, contractKeys):
        """Check to see if all the given contract joints are unique to this module"""

        return True

        # todo: check contract joints correctly

        # if isinstance(contractKeys, basestring):
        #     contractKeys = [contractKeys]
        #
        # for contractKey in contractKeys:
        #
        #     if contractKey in self.contract.values():
        #         if cmds.objExists(self.contract[contractKey] + '.module'):
        #             raise RuntimeError(
        #                 'Given startJoint <{0}> already belongs to a module'.format(self.contract[contractKey]))
        #
        #         else:
        #             return True
        #     else:
        #         raise RuntimeError('<{0}> is not a part of the module contract.'.format(contractKey))

    def duplicateChain(self, joints):
        """Duplicate the given input chain"""

        return
        