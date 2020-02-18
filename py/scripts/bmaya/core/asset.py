"""Base class for production Assets"""

import os
import shutil
import json

import maya.cmds as cmds

from bmaya.rigging.components import *
from bmaya.core import constants

try:
    PROJECT_ROOT = os.environ['RIG_ROOT']
except KeyError:
    raise RuntimeError('RIG_ROOT environment variable is not set.')

class Asset(object):
    def __init__(self, name, project, assetType):
        self.name = name
        self.assetType = assetType
        self.project = project
        self.components = []

        self.initComponents()
        self.initComponentFolders()
        self.initComponentFiles()

    @property
    def rootDir(self):
        root = os.path.abspath(os.path.join(PROJECT_ROOT, self.project, self.assetType, self.name))
        
        if os.path.exists(root):
            return root
        else:
            os.makedirs(root)
            return root

    @classmethod
    def openInExplorer(cls, path):
        if os.path.exists(path):
            os.startfile(os.path.dirname(path))

    @classmethod
    def openFile(cls, path):
        if os.path.exists(path):
            if path.endswith('.ma'):
                cmds.file(path, open=True, force=True)
            else:
                os.startfile(path)

    @classmethod
    def versionFile(cls, path):
        """Versions the given file to a subfolder in its directory called
        <basename>.versions.

         """

        if not os.path.exists(path):
            return

        dirname = os.path.dirname(path)

        filename, extension = os.path.splitext(os.path.basename(path))

        versionFolder = os.path.join(dirname, (filename + ".Versions"))

        # create the version folder if it doesn't exist
        if not os.path.exists(versionFolder):
            os.mkdir(versionFolder)

        numVersions = len(os.listdir(versionFolder))

        versionFilename = os.path.join(versionFolder, "{0}_{1:04d}{2}".format(
            filename, (numVersions + 1), extension))

        shutil.copy(path, versionFilename)

        print ">> Versioned file to {0}".format(versionFilename)

    @classmethod
    def referenceFile(cls, path):
        if os.path.exists(path):
            if path.endswith('.ma'):
                cmds.file(path, reference=True, 
                          namespace=os.path.splitext(os.path.basename(path))[0])
        

    @classmethod
    def exists(cls, project, name, assetType):
        """Checks if the given asset exists"""

        rootDir = os.path.abspath(os.path.join(PROJECT_ROOT,
                                                project, assetType, name))

        if os.path.exists(rootDir):
            return rootDir

        else:
            return False

    @classmethod
    def findFilesOfType(cls, path, filetype):
        return  [f for f in os.listdir(path) if f.endswith('.' + filetype)]

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

        print ">> Initialized component folders"

    def initComponentFiles(self):

        if not os.path.exists(self.mesh.fullPath):
            print ">> Creating mesh file."
            # mesh file is just a blank ma
            cmds.file(new=True, force=True)
            cmds.file(rename=self.mesh.fullPath)
            cmds.file(save=True, type="mayaAscii", force=True)
            self.versionFile(self.mesh.fullPath)
        else:
            print '>> A working mesh file already exists for ' + self.name

        if not os.path.exists(self.skeleton.fullPath):
            print ">> Creating skeleton file."
            # create a single joint for the default skeleton file
            cmds.file(new=True, force=True)
            cmds.joint(name=constants.ROOT_JOINT)
            cmds.file(rename=self.skeleton.fullPath)
            cmds.file(save=True, type="mayaAscii", force=True)
            self.versionFile(self.skeleton.fullPath)
        else:
            print '>> A working skeleton file already exists for ' + self.name

        if not os.path.exists(self.cvs.fullPath):
            print ">> Creating cvs file."
            with open(self.cvs.fullPath, "w") as f:
                json.dump({}, f)
            self.versionFile(self.cvs.fullPath)
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

            self.versionFile(self.build.fullPath)

    def componentPathFromType(self, componentType):
        
        for component in self.components:
            if component.type == componentType:
                return component.fullPath

    def versionAsset(self):
        """Versions the entire asset to a folder"""

        versionFolder = os.path.join(self.rootDir, (self.name + ".Versions"))

        if not os.path.exists(versionFolder):
            os.makedirs(versionFolder)

        numVersions = len(os.listdir(versionFolder))

        # make a new version folder

        versionNum = str(numVersions + 1)
        versionNum = versionNum.zfill(3)

        newVersionFolder = os.path.join(versionFolder, self.name + versionNum)

        print '\n>> Creating asset version ' + versionNum

        os.mkdir(newVersionFolder)

        for component in self.components:
            componentFile = component.fullPath

            print '>>> Versioning asset component ' + component.type

            if component.type == 'weights':
                weightVersionFolder = os.mkdir(os.path.join(newVersionFolder, 'weights'))
                for weightFile in component.files:
                    shutil.copy(weightFile, weightVersionFolder)
            elif componentFile and os.path.exists(componentFile):
                shutil.copy(componentFile, newVersionFolder)

        print '\n>> Asset versioned successfully to: ' + newVersionFolder
    
    