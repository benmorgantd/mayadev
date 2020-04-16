"""Base class for production Assets"""

import os
import shutil
import json

import maya.cmds as cmds

from bmaya.core.components import *
from bmaya.core import constants
from bmaya.core import fileio

try:
    PROJECT_ROOT = os.environ['RIG_ROOT']
except KeyError:
    raise RuntimeError('RIG_ROOT environment variable is not set.')

class Asset(object):
    def __init__(self, name=None, project=None, assetType=None):
        # self.id, self.project, self.assetType, self.name = self.interpretId(id)
        # self.id = id
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
    def interpretId(cls, id):
        

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
        if os.path.exists(path):
            return [f for f in os.listdir(path) if f.endswith('.' + filetype)]
        else:
            return []


        return  

    @classmethod
    def splitpath(cls, filepath):
        """split a path into all of its components"""

        result = []

        while os.path.split(filepath)[1]:
            splitname = os.path.split(filepath)
            result.append(splitname[1])
            filepath = splitname[0]

        result.reverse()

        return result


    @classmethod
    def getAssetArgsFromFile(cls, filepath):
        """Given a path, derive from it the asset's name, type, and project"""

        filepath = os.path.abspath(filepath)

        assetName = None
        assetProject = None
        assetType = None

        dirname = os.path.dirname(filepath)
        basename = os.path.basename(filepath)

        # see if it's in a subdirectory of PROJECT_ROOT

        for directory, subdirectory, directoryFiles in os.walk(PROJECT_ROOT):
            if dirname in directory and basename in directoryFiles:
                # this file is within this asset's directory
                rootDirectory = os.path.dirname(os.path.join(PROJECT_ROOT, 'projects'))
                splitRootRelativePath = cls.splitpath(filepath.split(rootDirectory)[1])
                assetName = splitRootRelativePath[2]
                assetType = splitRootRelativePath[1]
                assetProject = splitRootRelativePath[0]
                
        return assetName, assetProject, assetType

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
                weightsDir = os.path.join(newVersionFolder, 'weights')
                os.mkdir(weightsDir)

                weightFiles = [os.path.join(component.fullPath, f) for f in component.files if f.endswith('.weights')]

                for weightFile in weightFiles:
                    shutil.copy(weightFile, weightsDir)
                    
            elif componentFile and os.path.exists(componentFile):
                shutil.copy(componentFile, newVersionFolder)

        print '\n>> Asset versioned successfully to: ' + newVersionFolder
    
    