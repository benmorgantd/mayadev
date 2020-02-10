import json
import os
import time

import maya.cmds as cmds

from bmaya.core.asset import Asset
from bmaya.rigging.components import *
from bmaya.core import constants

from bmaya.rigging.shapes import shapelib, shapeio
from bmaya.rigging.weights import weightio
from bmaya.rigging.Osiris.tools.build import buildio

import layout

#reload(shapeio)
#reload(weightio)
#reload(buildio)
#reload(layout)

class Character(Asset):
    '''Character is the base class for all rigs created with Osiris'''

    def __init__(self, name, project, assetType):
        super(Character, self).__init__(name, project, assetType)

        self.skinClusters = []
        # an array of dictionary representations of our module classes
        self.modules = []
        self.buildData = None
        self.componentsSet = None
        self.timeBuilt = time.strftime('%c', time.localtime())

    @property
    def meshes(self):
        return cmds.sets(self.meshSet, query=True) or []
    
    @property
    def controls(self):
        return cmds.sets(self.allControls, query=True) or []

    def addModule(self, moduleDict):
        # pass it the dictionary representation of the module
        # this way we can add modules from file or object data

        assert isinstance(moduleDict, dict)

        self.modules.append(moduleDict)

    def buildLayout(self):
        layoutMod = layout.Layout(character=self)
        layoutMod.build()
        return layoutMod.dict

    def buildRig(self):

        self.modules = []
        self.allControls = []
        mirrorModules = []

        # create a new scene
        cmds.file(new=True, force=True)

        self.makeNode()
        
        # open up the character's build file (json)
        self.buildData = buildio.load(self.build.fullPath)
        
        buildList = []

        self.modules.append(self.buildLayout())

        # unflatten tree
        def addChildren(mod):
            mod['character'] = self
            self.addModule(mod)
            buildList.append(mod)

            for child in mod['children']:
                addChildren(child)

        for mod in self.buildData:
            if mod['children']:
                addChildren(mod)
            else:
                mod['character'] = self
                self.addModule(mod)
                buildList.append(mod)

        # create the new class instance from the data
        from bmaya.rigging import rigModules

        for mod in buildList:
            # access the modType attribute from the module's dictionary
            modType = mod['modType']

            # create a new instance of that class
            modInstance = rigModules.MODULE_CLASSES[modType].__new__(rigModules.MODULE_CLASSES[modType])
            modInstance.__init__(character=self)

            for key, value in mod.items():
                # transfer the values from the read file to the instance
                setattr(modInstance, key, value)

            # build it!
            modInstance.build()

            self.allControls += [comp.ctrl for comp in modInstance.components]

            # it'll mirror if its mirror attribute is True
            mirrorInstance = modInstance.doMirror()

            # optional
            # cmds.refresh(currentView=True)

            if mirrorInstance:
                mirrorModules.append(mirrorInstance.dict)
                self.allControls += [comp.ctrl for comp in mirrorInstance.components]

        self.modules += mirrorModules
        
        self.componentSet = cmds.sets(self.allControls, name='CTRL_set')
        cmds.sets(self.componentSet, include='MASTER_set')

        # skinning after the components have been built allows us to create bind joints
        self.skin()

        self.addNodeAttrs()

        for mod in self.modules:
            if cmds.objExists(mod['name'] + '_MOD'):
                cmds.connectAttr(self.node + '.modules', mod['name'] + '_MOD.character')

        shapeio.load(self.cvs.fullPath)

        weightRoot = os.path.join(self.rootDir, self.weights.fullPath)

        for weightPath in self.weights.files:
            weightio.load(os.path.join(weightRoot, os.path.basename(weightPath)))

        # scene cleanup:
        self.setupMeshReferencing()
        self.lockDownConstraints()

        cmds.hide(cmds.ls(type='ikHandle'))
    
        cmds.file(rename=self.animRig.fullPath)
        cmds.file(save=True, type='mayaAscii', force=True)
        self.versionFile(self.animRig.fullPath)

    def makeNode(self):
        if not cmds.objExists(self.name + '_CHAR'):
            self.node = cmds.createNode('network', name=self.name + '_CHAR')

            # create an attribute to glue other parts to the rig to
            cmds.addAttr(self.node, longName='sock', attributeType='message')

            print '>>> Created character node >> {0} <<'.format(self.node)

    def addNodeAttrs(self):

        if not self.node:
            raise RuntimeError('Character node does not exist yet for ' + self.name)

        for attr in self.__dict__:
            attrVal = self.__dict__[attr]
            attrType = type(attrVal)

            if attrVal is None:
                attrType = 'string'
                attrVal = 'None'

            if attrType in [unicode, str]:
                attrType = 'string'
                attrVal = str(attrVal)

            elif attrType is list:
                cleanList = []

                for val in attrVal:
                    if type(val) in [unicode, str, int, float, bool, None]:
                        cleanList.append(val)

                    elif type(val) is dict:
                        cleanDict = {}
                        for key in val:
                            if type(val[key]) in [unicode, str, int, float, bool, None]:
                                cleanDict[key] = val[key]
                            elif isinstance(val[key], shapelib.Shape):
                                cleanDict[key] = val[key].ctrl
                        cleanList.append(cleanDict)
                    elif isinstance(val, shapelib.Shape):
                        cleanList.append(val.ctrl)

                attrType = 'string'
                attrVal = json.dumps(cleanList)

            elif attrType is dict:
                cleanDict = {}
                for key in attrVal:
                    if type(attrVal[key]) in [unicode, str, int, float, bool, None]:
                        cleanDict[key] = attrVal[key]
                    elif isinstance(attrVal[key], shapelib.Shape):
                        cleanDict[key] = attrVal[key].ctrl

                attrType = 'string'
                attrVal = json.dumps(cleanDict)

            elif attrType is bool:
                attrType = 'bool'
                attrVal = attrVal

            elif attrType in [animRig.AnimRig, build.Build, cvs.Cvs, mesh.Mesh, skeleton.Skeleton, weights.Weights]:
                attrType = 'string'
                attrVal = self.componentPathFromType(attr)
                attr += 'Path'
            else:
                attrType = 'string'
                try:
                    attrVal = attr.fullPath
                except AttributeError:
                    continue

            if attrType == 'string':
                cmds.addAttr(self.node, ln=attr, dt='string', keyable=False)
                cmds.setAttr(self.node + '.' + attr, str(attrVal), type='string')
            else:
                cmds.addAttr(self.node, ln=attr, at=attrType, dv=attrVal, keyable=False)

            cmds.setAttr(self.node + '.' + attr, lock=True)

    def skin(self):
        # check for existing weights files. If not then skin to skeleton set
        # skin the root joint to all the meshes in the scene

        for mesh in self.meshes:
            weightsPath = os.path.join(self.weights.fullPath, mesh + '.' + self.weights.extension)
            if os.path.exists(weightsPath):
                weightio.load(weightsPath)
            else:
                # skin the mesh to the root joint
                self.skinClusters.append(cmds.skinCluster(constants.ROOT_JOINT, mesh,
                                                        maximumInfluences=1,
                                                        bindMethod=1,
                                                        weightDistribution=1,
                                                        normalizeWeights=1)[0])

    def setupMeshReferencing(self):

        md = cmds.createNode('multDoubleLinear', name='meshRef_md')
        cmds.setAttr(md + '.input2', 2)
        # don't have it show up in the mesh's channel box
        cmds.setAttr(md + '.isHistoricallyInteresting', False)
        
        cmds.addAttr(self.node, longName='referenceMesh', attributeType='bool', defaultValue=True, keyable=True)
        cmds.connectAttr(self.node + '.referenceMesh', md + '.input1')

        for mesh in self.meshes:
            cmds.setAttr(mesh + '.overrideEnabled', 1)
            cmds.connectAttr(md + '.output', mesh + '.overrideDisplayType')

    def lockMeshes(self):

        for mesh in self.meshes:
            verts = cmds.polyEvaluate(mesh, vertex=True)

            for i in range(verts):
                cmds.setAttr('{0}.pt[{1}]'.format(mesh, i), lock=True)
    
    def connectToCharacter(self, node):
        
        if cmds.objExists(node):
            cmds.addAttr(node, longName='character', attributeType='message')
            cmds.connectAttr(self.node + '.sock', node + '.character')

    def hideKeyableAttr(self, obj):
        if cmds.objExists(obj):
            cmds.setAttr(obj, keyable=False, channelBox=False)

    def lockDownConstraints(self):
         # manage constraints
        for constraint in cmds.ls(type='constraint'):
            attrHideList = ['nodeState', 'interpType']

            constraintType = cmds.objectType(constraint)

            if constraintType in ['parentConstraint', 'orientConstraint']:
                cmds.setAttr(constraint + '.interpType', 2)
                attrHideList += ['rdtx', 'rdty', 'rdtz']
                if constraintType == 'parentConstraint':
                    weights = cmds.parentConstraint(constraint, query=True, weightAliasList=True)
                else:
                    weights = cmds.orientConstraint(constraint, query=True, weightAliasList=True)
                
                if weights:
                    for w in range(len(weights)):
                        attrHideList += ['w{0}'.format(w)]
            else:
                weights = cmds.parentConstraint(constraint, query=True, weightAliasList=True)
                if weights:
                    for w in range(len(weights)):
                        attrHideList += ['w{0}'.format(w)]
            
            for attr in attrHideList:
                self.hideKeyableAttr('{0}.{1}'.format(constraint, attr))
            

