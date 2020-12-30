import json
import os
import time

import maya.cmds as cmds

from bmaya.core.asset import Asset
from bmaya.core.components import *
from bmaya.core import constants, fileio, qtbase

from bmaya.rigging.shapes import shapelib, shapeio
from bmaya.rigging.weights import weightio, weightutils
from bmaya.rigging import buildio
from bmaya import mayanode

import layout


class Rig(Asset):
    '''Rig is the base class for all rigs'''

    def __init__(self, assetId, hasFace=False):
        super(Rig, self).__init__(assetId)

        self.hasFace = hasFace
        self.skinClusters = []
        # an array of dictionary representations of our module classes
        self.modules = []
        self.buildData = None
        self.componentsSet = None
        self.timeBuilt = time.strftime('%c', time.localtime())

        self.initComponents()
        self.initComponentFolders()
        self.initComponentFiles()

    @property
    def meshShapes(self):
        _setMeshes = cmds.sets(self.meshSet, query=True) or []
        _meshShapes = []
        for mesh in _setMeshes:
            _meshShapes.append(mayanode.DagNode(mesh).shape)

        return _meshShapes

    @property
    def controls(self):
        _controls = []
        _setControls = cmds.sets(self.ctrlSet, query=True) or []
        for control in _setControls:
            _controls.append(mayanode.DagNode(control))

        return _controls

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

        progressWindow = qtbase.ProgressWindow(title='Building Rig')
        progressWindow.show()

        self.modules = []
        self.allControls = []
        mirrorModules = []

        progressWindow.setStatus('Creating blank scene')
        progressWindow.increment(5)

        # create a new scene
        cmds.file(new=True, force=True)

        progressWindow.setStatus('Loading plugins')
        progressWindow.increment(5)
        # load required plugins
        self.loadPlugins()

        progressWindow.setStatus('Making character node')
        progressWindow.increment(5)

        self.makeNode()

        progressWindow.setStatus('Reading build file')
        progressWindow.increment(5)

        # open up the character's build file (json)
        self.buildData = buildio.load(self.build.fullPath)

        buildList = []

        progressWindow.setStatus('Building layout rig')
        progressWindow.increment(5)

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

        progressWindow.setStatus('Flattening build tree')
        progressWindow.increment(5)

        for mod in self.buildData:
            if mod['children']:
                addChildren(mod)
            else:
                mod['character'] = self
                self.addModule(mod)
                buildList.append(mod)

        print(buildList)

        # create the new class instance from the data
        from bmaya.rigging import modules

        progressWindow.setStatus('Building limbs')
        progressWindow.increment(5)

        for mod in buildList:
            # access the modType attribute from the module's dictionary
            modType = mod['modType']

            # create a new instance of that class
            modInstance = modules.MODULE_CLASSES[modType].__new__(
                modules.MODULE_CLASSES[modType])
            modInstance.__init__(character=self)

            for key, value in mod.items():
                # transfer the values from the read file to the instance
                setattr(modInstance, key, value)

            # build it!
            modInstance.build()

            self.allControls += [comp.ctrl for comp in modInstance.components]

            # it'll mirror if its mirror attribute is True
            mirrorInstance = modInstance.doMirror()

            # optional, adds time.
            cmds.refresh(currentView=True)

            if mirrorInstance:
                mirrorModules.append(mirrorInstance.dict)
                self.allControls += [comp.ctrl for comp in
                                     mirrorInstance.components]

        self.modules += mirrorModules

        progressWindow.setStatus('Making sets')
        progressWindow.increment(5)

        self.ctrlSet = cmds.sets(self.allControls, name='CTRL_set')
        if self.hasFace:
            self.faceCtrlSet = cmds.sets(name='FACE_CTRL_set')
            cmds.sets(self.faceCtrlSet, edit=True, forceElement=self.ctrlSet)

        progressWindow.setStatus('Adding default skinning')
        progressWindow.increment(5)
        # skinning after the components have been built allows us to create bind joints
        self.skin()

        progressWindow.setStatus('Writing character node attributes')
        progressWindow.increment(5)
        self.addNodeAttrs()

        for mod in self.modules:
            if cmds.objExists(mod['name'] + '_' + constants.MODULE_SUFFIX):
                cmds.connectAttr(self.node + '.modules',
                                 '{0}_{1}.character'.format(mod['name'],
                                                            constants.MODULE_SUFFIX))

        progressWindow.setStatus('Loading control shapes')
        progressWindow.increment(5)
        shapeio.load(self.componentPathFromType('cvs'))

        progressWindow.setStatus('Loading weights')
        progressWindow.increment(5)
        weightsDir = self.componentPathFromType('weights')
        weightFiles = self.findFilesOfType(weightsDir, 'weights')

        for f in weightFiles:
            weightio.load(os.path.join(weightsDir, f))

        # create influences set
        self.bindSet = self.makeBindSet()

        progressWindow.setStatus('Coloring controls')
        progressWindow.increment(5)
        self.colorControls()

        progressWindow.setStatus('Cleaning up')
        # scene cleanup:
        self.setupMeshReferencing()
        self.lockDownConstraints()

        cmds.hide(cmds.ls(type='ikHandle'))

        progressWindow.setStatus('Running post operations')
        progressWindow.increment(5)
        self.runPostOps()

        progressWindow.setStatus('Finished building rig')

        cmds.file(rename=self.animRig.fullPath)
        cmds.file(save=True, type='mayaAscii', force=True)
        fileio.versionFile(self.animRig.fullPath)

        cmds.viewFit(allObjects=True, fitFactor=1)

        endTime = time.time()

        print "Rig built in {0:.2f} seconds.".format(endTime - startTime)

        progressWindow.hide()
        del progressWindow

    def makeNode(self):
        if not cmds.objExists(self.name + '_CHAR'):
            self.node = cmds.createNode('network', name=self.name + '_CHAR')

            # create an attribute to glue other parts to the rig to
            cmds.addAttr(self.node, longName='connector',
                         attributeType='message')

            print '>>> Created character node >> {0} <<'.format(self.node)

    def addNodeAttrs(self):

        if not self.node:
            raise RuntimeError(
                'Character node does not exist yet for ' + self.name)

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
                            if type(val[key]) in [unicode, str, int, float,
                                                  bool, None]:
                                cleanDict[key] = val[key]
                            elif isinstance(val[key], shapelib.ControlCurve):
                                cleanDict[key] = val[key].ctrl
                        cleanList.append(cleanDict)
                    elif isinstance(val, shapelib.ControlCurve):
                        cleanList.append(val.ctrl)

                attrType = 'string'
                attrVal = json.dumps(cleanList)

            elif attrType is dict:
                cleanDict = {}
                for key in attrVal:
                    if type(attrVal[key]) in [unicode, str, int, float, bool,
                                              None]:
                        cleanDict[key] = attrVal[key]
                    elif isinstance(attrVal[key], shapelib.ControlCurve):
                        cleanDict[key] = attrVal[key].ctrl

                attrType = 'string'
                attrVal = json.dumps(cleanDict)

            elif attrType is bool:
                attrType = 'bool'
                attrVal = attrVal

            elif attrType in [animRig.AnimRig, build.Build, cvs.Cvs, mesh.Mesh,
                              skeleton.Skeleton, weights.Weights]:
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
                cmds.setAttr(self.node + '.' + attr, str(attrVal),
                             type='string')
            else:
                cmds.addAttr(self.node, ln=attr, at=attrType, dv=attrVal,
                             keyable=False)

            cmds.setAttr(self.node + '.' + attr, lock=True)

    def skin(self):
        # check for existing weights files. If not then skin to skeleton set
        # skin the root joint to all the meshes in the scene

        for mesh in self.meshShapes:
            weightsPath = os.path.join(self.weights.fullPath,
                                       mesh.transform + '.' + self.weights.extension)
            if os.path.exists(weightsPath):
                weightio.load(weightsPath)
            elif 'noSkin' not in cmds.listAttr(mesh):
                # skin meshes not marked noSkin to the root joint
                self.skinClusters.append(
                    cmds.skinCluster(constants.ROOT_JOINT, mesh,
                                     maximumInfluences=1,
                                     bindMethod=1,
                                     weightDistribution=1,
                                     normalizeWeights=1)[0])
            else:
                print('Skipped applying weights on ' + mesh)

    def setupMeshReferencing(self):

        md = cmds.createNode('multDoubleLinear', name='meshRef_md')
        cmds.setAttr(md + '.input2', 2)
        # don't have it show up in the mesh's channel box
        cmds.setAttr(md + '.isHistoricallyInteresting', False)

        cmds.addAttr(self.node, longName='referenceMesh', attributeType='bool',
                     defaultValue=True, keyable=True)
        cmds.connectAttr(self.node + '.referenceMesh', md + '.input1',
                         force=True)

        for mesh in self.meshShapes:
            try:
                cmds.setAttr(mesh + '.overrideEnabled', 1)
                cmds.connectAttr(md + '.output', mesh + '.overrideDisplayType',
                                 force=True)
            except RuntimeError:
                pass

    def lockMeshes(self):

        for mesh in self.meshShapes:
            numVerts = mesh.fnMesh.numVertices()

            for i in xrange(numVerts):
                cmds.setAttr(mesh + '.pt[{0}]'.format(i), lock=True)

    def connectToCharacter(self, node):

        if cmds.objExists(node):
            cmds.addAttr(node, longName='character', attributeType='message')
            cmds.connectAttr(self.node + '.connector', node + '.character')

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
                    weights = cmds.parentConstraint(constraint, query=True,
                                                    weightAliasList=True)
                else:
                    weights = cmds.orientConstraint(constraint, query=True,
                                                    weightAliasList=True)

                if weights:
                    for w in range(len(weights)):
                        attrHideList += ['w{0}'.format(w)]
            else:
                weights = cmds.parentConstraint(constraint, query=True,
                                                weightAliasList=True)
                if weights:
                    for w in range(len(weights)):
                        attrHideList += ['w{0}'.format(w)]

            for attr in attrHideList:
                self.hideKeyableAttr('{0}.{1}'.format(constraint, attr))

    def makeBindSet(self):
        skelJoints = set(cmds.listRelatives('SKELETON', type='joint', ad=1))
        skinClusterInfluences = set()

        for mesh in self.meshShapes:
            existingSkin = mesh.getSkinCluster
            if existingSkin:
                members = existingSkin.influenceObjects

                for i in xrange(members.length()):
                    if members[i].partialPathName() in skelJoints:
                        skinClusterInfluences.add(members[i].partialPathName())

        bindSet = cmds.sets(list(skinClusterInfluences), name='BIND_set')

    def colorControls(self):
        for ctrl in self.controls:
            if '_M_' in ctrl.name:
                side = 22
            elif '_L_' in ctrl.name:
                side = 6
            elif '_R_' in ctrl.name:
                side = 13
            else:
                side = 22
            try:
                cmds.setAttr(ctrl + '.overrideEnabled', True)
                cmds.setAttr(ctrl + '.overrideColor', side)
            except:
                # for sets nested within the ctrl set
                pass

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
        self.postops = postops.PostOps(self, 'postops')

        if self.hasFace:
            self.facePoses = facePoses.FacePoses(self, 'facePoses')

        self.components += [self.mesh, self.skeleton, self.weights, self.cvs,
                            self.build, self.animRig, self.postops]
        if self.hasFace:
            self.components.append(self.facePoses)

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
            layoutRigPath = os.path.join(constants.TEMPLATES_PATH,
                                         "LayoutRig.json")

            with open(layoutRigPath, "r") as f:
                layoutRigData = f.read()

            # write the contents to this asset's build file
            with open(self.build.fullPath, "w") as f:
                f.write(layoutRigData)

            fileio.versionFile(self.build.fullPath)

        if not os.path.exists(self.postops.fullPath):
            print ">> Creating postops file"

            # Write the template python file
            with open(self.postops.fullPath, 'w') as f:
                f.write(constants.POSTOPS_TEMPLATE)

            fileio.versionFile(self.postops.fullPath)


        if self.hasFace:

            if not os.path.exists(self.facePoses.fullPath):
                print(">> Creating facePoses file")

                # write a blank json file
                with open(self.facePoses.fullPath, "w") as f:
                    json.dump({}, f)
                fileio.versionFile(self.facePoses.fullPath)


    def runPostOps(self):
        # run postops file
        with open(self.postops.fullPath, 'r') as f:
            code = f.read()
            exec (code)
