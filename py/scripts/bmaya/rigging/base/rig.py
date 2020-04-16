import json
import os
import time

import maya.cmds as cmds

from bmaya.core.asset import Asset
from bmaya.core.components import *
from bmaya.core import constants, fileio

from bmaya.rigging.shapes import shapelib, shapeio
from bmaya.rigging.weights import weightio
from bmaya.rigging import buildio

from decorators import wrapStandalone
import layout


class Rig(Asset):
    '''Rig is the base class for all rigs'''

    def __init__(self, assetId):
        super(Rig, self).__init__(assetId)

        self.initComponents()
        self.initComponentFolders()
        self.initComponentFiles()

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
        return cmds.sets(self.ctrlSet, query=True) or []

    @property
    def influences(self):
        return cmds.sets(self.bindSet, query=True) or []

    def addModule(self, moduleDict):
        # pass it the dictionary representation of the module
        # this way we can add modules from file or object data

        assert isinstance(moduleDict, dict)

        self.modules.append(moduleDict)

    def buildLayout(self):
        layoutMod = layout.Layout(character=self)
        layoutMod.build()
        return layoutMod.dict, layoutMod.components

    def buildRig(self):

        startTime = time.time()

        self.modules = []
        self.allControls = []
        mirrorModules = []

        # create a new scene
        cmds.file(new=True, force=True)

        # load required plugins
        self.loadPlugins()

        self.makeNode()
        
        # open up the character's build file (json)
        self.buildData = buildio.load(self.build.fullPath)
        
        buildList = []

        layoutDict, layoutComponents = self.buildLayout()
        self.modules.append(layoutDict)
        self.allControls += [comp.ctrl for comp in layoutComponents]

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
        from bmaya.rigging import modules

        for mod in buildList:
            # access the modType attribute from the module's dictionary
            modType = mod['modType']

            # create a new instance of that class
            modInstance = modules.MODULE_CLASSES[modType].__new__(modules.MODULE_CLASSES[modType])
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
        
        self.ctrlSet = cmds.sets(self.allControls, name='CTRL_set')

        # skinning after the components have been built allows us to create bind joints
        self.skin()

        self.addNodeAttrs()

        for mod in self.modules:
            if cmds.objExists(mod['name'] + '_MOD'):
                cmds.connectAttr(self.node + '.modules', mod['name'] + '_MOD.character')

        shapeio.load(self.componentPathFromType('cvs'))

        weightsDir = self.componentPathFromType('weights')
        weightFiles = self.findFilesOfType(weightsDir, 'weights')

        for f in weightFiles:
            weightio.load(os.path.join(weightsDir, f))

        # create influences set
        self.bindSet = self.makeBindSet()

        self.colorControls()

        # scene cleanup:
        self.setupMeshReferencing()
        self.lockDownConstraints()

        cmds.hide(cmds.ls(type='ikHandle'))
    
        cmds.file(rename=self.animRig.fullPath)
        cmds.file(save=True, type='mayaAscii', force=True)
        fileio.versionFile(self.animRig.fullPath)

        cmds.viewFit(allObjects=True, fitFactor=1)

        endTime = time.time()

        print "Rig built in {0:.2f} seconds.".format(endTime - startTime)

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
        cmds.connectAttr(self.node + '.referenceMesh', md + '.input1', force=True)

        for mesh in self.meshes:
            cmds.setAttr(mesh + '.overrideEnabled', 1)
            cmds.connectAttr(md + '.output', mesh + '.overrideDisplayType', force=True)

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
            

    def makeBindSet(self):
        skelJoints = set(cmds.listRelatives('SKELETON', type='joint', ad=1))
        skinClusterInfluences = set()

        for mesh in self.meshes:
            existingSkin = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
            if existingSkin:
                members = cmds.skinCluster(existingSkin[0], query=True, influence=True)
                for jnt in members:
                    if jnt in skelJoints:
                        skinClusterInfluences.add(jnt)
        
        bindSet = cmds.sets(list(skinClusterInfluences), name='BIND_set')

    def colorControls(self):
        for ctrl in self.controls:
            if '_M_' in ctrl:
                side = 22
            elif '_L_' in ctrl:
                side = 6
            elif '_R_' in ctrl:
                side = 13
                
            cmds.setAttr(ctrl + '.overrideEnabled', True)
            cmds.setAttr(ctrl + '.overrideColor', side)

    def loadPlugins(self):
        for plugin in constants.REQUIRED_PLUGINS:
            cmds.loadPlugin(plugin, quiet=True)

    def initComponents(self):
        # initialize the component objects for the asset
        self.mesh = mesh.Mesh(self, 'mesh')
        self.skeleton = skeleton.Skeleton(self, 'skeleton')
        self.weights = weights.Weights(self, 'weights')
        self.cvs = cvs.Cvs(self, 'cvs')
        self.build = build.Build(self, 'build')
        self.animRig = animRig.AnimRig(self, 'animRig')

        self.components += [self.mesh, self.skeleton, self.weights, self.cvs, self.build, self.animRig]
        
    def initComponentFolders(self):
        """Creates the component folders for the asset"""

        for component in self.components:
            dirpath = os.path.dirname(component.fullPath)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

        print ">> Component folders initialized"

    
    def initComponentFiles(self):

        if not os.path.exists(self.mesh.fullPath):
            print ">> Creating mesh file."
            # mesh file is just a blank ma
            cmds.file(new=True, force=True)
            cmds.file(rename=self.mesh.fullPath)
            cmds.file(save=True, type="mayaAscii", force=True)
            fileio.versionFile(self.mesh.fullPath)
        else:
            print '>> A working mesh file already exists for ' + self.name

        if not os.path.exists(self.skeleton.fullPath):
            print ">> Creating skeleton file."
            # create a single joint for the default skeleton file
            cmds.file(new=True, force=True)
            cmds.joint(name=constants.ROOT_JOINT)
            cmds.file(rename=self.skeleton.fullPath)
            cmds.file(save=True, type="mayaAscii", force=True)
            fileio.versionFile(self.skeleton.fullPath)
        else:
            print '>> A working skeleton file already exists for ' + self.name

        if not os.path.exists(self.cvs.fullPath):
            print ">> Creating cvs file."
            with open(self.cvs.fullPath, "w") as f:
                json.dump({}, f)
            fileio.versionFile(self.cvs.fullPath)
        else:
            print '>> A working cvs file already exists for ' + self.name

        if not os.path.exists(self.build.fullPath):
            print ">> Creating build file."
            # give it a LayoutRig template
            layoutRigPath = os.path.join(constants.TEMPLATES_PATH, "LayoutRig.json")

            with open(layoutRigPath, "r") as f:
                layoutRigData = f.read()
            
            # write the contents to this asset's build file
            with open(self.build.fullPath, "w") as f:
                f.write(layoutRigData)

            fileio.versionFile(self.build.fullPath)