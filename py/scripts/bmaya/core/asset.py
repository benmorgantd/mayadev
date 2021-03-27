"""Base class for production Assets"""

import os
import shutil

import maya.cmds as cmds

from bmaya.core.components import *


try:
    PROJECT_DIR = os.environ['RIGGING_PROJECT_DIR']
except KeyError:
    raise RuntimeError('RIGGING_PROJECT_DIR environment variable is not set.')


class Asset(object):
    def __init__(self, assetId):
        self.assetId = Asset.validateId(assetId)

        self.components = []

    @property
    def rootDir(self):
        root = self.cleanPath(os.path.join(PROJECT_DIR, self.project, self.assetType, self.name))
        
        if os.path.exists(root):
            return root
        else:
            os.makedirs(root)
            return root

    @property
    def project(self):
        return self.assetId.split('|')[0]

    @property
    def assetType(self):
        return self.assetId.split('|')[1]
    
    @property
    def name(self):
        return self.assetId.split('|')[2]

    @classmethod
    def validateId(cls, assetId):
        """Determine if the given id is acceptable. 
        Ids should be a string in the format: project|type|name"""

        assert isinstance(assetId, str)

        if '|' not in assetId:
            raise ValueError('Id should have tokens split by the pike character.')
            
        splitId = assetId.split('|')

        if len(splitId) != 3:
            raise ValueError('Id must be three tokens separated by pikes')
        
        # check for illegal characters that may cause path errors
        if any(not token.isalnum() for token in splitId):
            raise ValueError('Id is not alphanumeric and contains illegal characters.')

        return assetId

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

        rootDir = os.path.abspath(os.path.join(PROJECT_DIR,
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
    def getAssetIdFromFile(cls, filepath):
        """Given a path, derive from it the asset's name, type, and project"""

        filepath = cls.cleanPath(filepath)

        assetName = None
        assetProject = None
        assetType = None

        dirname = cls.cleanPath(os.path.dirname(filepath))
        basename = cls.cleanPath(os.path.basename(filepath))

        # see if it's in a subdirectory of PROJECT_ROOT

        for directory, subdirectory, directoryFiles in os.walk(PROJECT_DIR):
            if dirname in cls.cleanPath(directory) and any(basename in cls.cleanPath(f) for f in directoryFiles):
                # this file is within this asset's directory
                rootDirectory = cls.cleanPath(os.path.dirname(os.path.join(PROJECT_DIR, 'projects')))
                # returns [project, type, name, ..., basename]
                splitRootRelativePath = cls.splitpath(filepath.split(rootDirectory)[1])
                assetName = splitRootRelativePath[2]
                assetType = splitRootRelativePath[1]
                assetProject = splitRootRelativePath[0]
        if assetProject and assetType and assetName:
            return '|'.join([assetProject, assetType, assetName])
        else:
            cmds.warning('NO ASSET FOUND')
            return None

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

        print('\n>> Creating asset version ' + versionNum)

        os.mkdir(newVersionFolder)

        for component in self.components:
            componentFile = component.fullPath

            print('>>> Versioning asset component ' + component.type)

            if component.type == 'weights':
                weightsDir = os.path.join(newVersionFolder, 'weights')
                os.mkdir(weightsDir)

                weightFiles = [os.path.join(component.fullPath, f) for f in component.files if f.endswith('.weights')]

                for weightFile in weightFiles:
                    shutil.copy(weightFile, weightsDir)
                    
            elif componentFile and os.path.exists(componentFile):
                shutil.copy(componentFile, newVersionFolder)

        print('\n>> Asset versioned successfully to: ' + newVersionFolder)

    @classmethod
    def cleanPath(cls, filepath):
        return os.path.abspath(filepath.lower())

    # TODO: add component-loading logic at the asset level?

