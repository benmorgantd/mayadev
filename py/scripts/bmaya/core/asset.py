"""Base class for production Assets"""

import os
import shutil
import json

import maya.cmds as cmds

from components import *

try:
    PROJECT_ROOT = os.environ['OSIRIS_ROOT']
except KeyError:
    raise RuntimeError('OSIRIS_ROOT environment variable is not set.')

ASSET_TYPES = ['prop', 'environment', 'character']

class Asset(object):
    def __init__(self, name, project, assetType):
        self.name = name
        self.assetType = assetType
        self.project = project
        self.components = []

        self.templatesPath = os.path.abspath(os.path.join(os.path.dirname(__file__),'rigTemplates'))
        
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
                # todo: should ask to save the current scene first
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
    def exists(cls, project, name, assetType):
        """Checks if the given asset exists"""

        rootDir = os.path.abspath(os.path.join(PROJECT_ROOT,
                                                project, assetType, name))

        if os.path.exists(rootDir):
            return rootDir

        else:
            return False

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
    
