import json
import os
import time

import maya.cmds as cmds

from bmaya.asset import Asset
from bmaya.components import *

from bmaya.tools.shapes import shapelib, shapeio
from bmaya.tools.weights import weightio
from bmaya.Osiris.tools.build import buildio

reload(shapeio)
reload(weightio)
reload(buildio)


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
        m = cmds.sets(self.meshSet, query=True)

        if m:
            return m
        else:
            return []
        
    def addModule(self, moduleDict):
        # pass it the dictionary representation of the module
        # this way we can add modules from file or object data

        self.modules.append(moduleDict)

    def buildRig(self):

        self.modules = []
        self.allControls = []
        mirrorModules = []

        # create a new scene
        cmds.file(new=True, force=True)

        self.makeNode()

        # open up the character's build file
        self.buildData = buildio.load(self.build.fullPath)

        for mod in self.buildData:
            mod['character'] = self
            self.addModule(mod)

        # create the new class instance from the string
        from .. import rigMods

        for mod in self.modules:
            # access the modType attribute from the module's dictionary
            modType = mod['modType']

            modInstance = rigMods.MODULE_CLASSES[modType].__new__(rigMods.MODULE_CLASSES[modType])
            modInstance.__init__(character=self)

            for key, value in mod.items():
                setattr(modInstance, key, value)

            # build it!
            modInstance.build()

            self.allControls += [comp.ctrl for comp in modInstance.components]

            # it'll mirror if its mirror attribute is True
            mirrorInstance = modInstance.doMirror()

            cmds.refresh(currentView=True)

            if mirrorInstance:
                mirrorModules.append(mirrorInstance.dict())
                self.allControls += [comp.ctrl for comp in mirrorInstance.components]

        self.modules += mirrorModules
        
        self.componentSet = cmds.sets(self.allControls, name='CTRL_set')
        cmds.sets(self.componentSet, include='MASTER_set')

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
        # set all meshes to reference
        self.setupMeshReferencing()
        # cmds.setAttr('SKELETON.visibility', 0)
        # self.setupSkeletonVisibility()

        cmds.file(rename=self.animRig.fullPath)
        cmds.file(save=True, type='mayaAscii', force=True)
        self.versionFile(self.animRig.fullPath)

    def makeNode(self):
        if not cmds.objExists(self.name + '_CHAR'):
            self.node = cmds.createNode('network', name=self.name + '_CHAR')
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
            self.skinClusters.append(cmds.skinCluster(self.skeletonSet, mesh,
                                                      maximumInfluences=1,
                                                      bindMethod=1,
                                                      weightDistribution=1,
                                                      normalizeWeights=2)[0])

    def setupMeshReferencing(self):

        md = cmds.createNode('multDoubleLinear', name='meshRef_md')
        cmds.setAttr(md + '.input2', 2)
        
        cmds.addAttr(self.node, longName='referenceMesh', attributeType='bool', defaultValue=True, keyable=True)
        cmds.connectAttr(self.node + '.referenceMesh', md + '.input1')

        for mesh in self.meshes:
            cmds.setAttr(mesh + '.overrideEnabled', 1)
            cmds.connectAttr(md + '.output', mesh + '.overrideDisplayType')

# import Osiris.lib.base.character as character;helm = character.Character('Helm','dev','prop');helm.build();
