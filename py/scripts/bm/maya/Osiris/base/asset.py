import os
import shutil
import json

import maya.cmds as cmds

try:
    PROJECT_ROOT = os.environ['OSIRIS_ROOT']
except KeyError:
    raise RuntimeError('OSIRIS_ROOT environment variable is not set.')
    

class Asset(object):
    def __init__(self, name, project, assetType):
        self.name = name
        self.assetType = assetType
        self.project = project
        self.rootDir = None
        self.components = ["mesh", "skeleton",
                           "weights", "cvs", "animRig", "build"]

        self.templatesPath = os.path.abspath(os.path.join(__file__, "..", "..", "templates"))

        self.initComponentFolders()
        self.initComponentFiles()

    def initComponentFolders(self):
        """Creates the component folders for the asset"""

        meshdir = os.path.dirname(self.getComponentPath("mesh"))
        weightsdir = self.getComponentPath("weights")

        if not os.path.exists(meshdir):
            os.makedirs(meshdir)

        if not os.path.exists(weightsdir):
            os.makedirs(weightsdir)

        print ">> Initialized component folders"

    def initComponentFiles(self):

        meshfile = self.getComponentPath("mesh")
        skeletonfile = self.getComponentPath("skeleton")
        cvsfile = self.getComponentPath("cvs")
        buildfile = self.getComponentPath("build")

        if not os.path.exists(meshfile) or not os.path.exists(skeletonfile):
            if not os.path.exists(meshfile):
                print ">> Creating mesh file."
                # mesh file is just a blank ma
                cmds.file(new=True, force=True)
                cmds.file(rename=meshfile)
                cmds.file(save=True, type="mayaAscii", force=True)
                self.versionFile(meshfile)

            if not os.path.exists(skeletonfile):
                print ">> Creating skeleton file."
                # create a single joint for the default skeleton file
                cmds.file(new=True, force=True)
                cmds.joint(name="root")
                cmds.file(rename=skeletonfile)
                cmds.file(save=True, type="mayaAscii", force=True)
                self.versionFile(skeletonfile)

            print ">> Component files initialized."

        else:
            print ">> Maya component files already exist for " + self.name

        if not os.path.exists(cvsfile):
            print ">> Creating cvs file."
            with open(cvsfile, "w") as f:
                json.dump({}, f)

            self.versionFile(cvsfile)

        if not os.path.exists(buildfile):
            print ">> Creating build file."
            # give it a LayoutRig template
            layoutRigPath = os.path.join(self.templatesPath, "LayoutRig.json")

            with open(layoutRigPath, "r") as f:
                layoutRigData = f.read()

            # copy the contents to this asset's build file
            with open(buildfile, "w") as f:
                f.write(layoutRigData)

            self.versionFile(buildfile)

    def getRootDir(self):
        self.rootDir = os.path.abspath(os.path.join(PROJECT_ROOT,
                                                    self.project, self.assetType, self.name))

        if os.path.exists(self.rootDir):
            return self.rootDir
        else:
            os.makedirs(self.rootDir)
            return self.rootDir

    def getComponentRoot(self, componentType):
        """Returns the relative path to the component file"""

        extensions = {"mesh": ".ma", "skeleton": ".ma",
                      "cvs": ".json", "animRig": ".ma", 
                      "weights": ".xml", "build":".json", "components":""}

        if componentType not in extensions.keys():
            print ">> '{0}' is not a valid component type.".format(componentType)
            return None

        if componentType == "mesh":
            return os.path.join(componentType, (componentType + extensions[componentType]))
        elif componentType in ["animRig", "build"]:
            return os.path.join("rig", (componentType + extensions[componentType]))
        elif componentType == "components":
            return os.path.join("rig", "components")
        elif componentType in ["skeleton", "cvs"]:
            return os.path.join("rig", "components", (componentType + extensions[componentType]))
        elif componentType == "weights":
            return os.path.join("rig", "components", componentType)

    def getComponentPath(self, componentType):
        """Returns the full path to the desired component file"""

        return os.path.join(self.getRootDir(), self.getComponentRoot(componentType))

    def getFiles(self, filepath):

        return os.listdir(filepath)

    def versionAsset(self):
        """Versions the entire asset to a folder"""

        versionFolder = os.path.join(
            self.getRootDir(), (self.name + ".Versions"))

        if not os.path.exists(versionFolder):
            os.makedirs(versionFolder)

        numVersions = len(os.listdir(versionFolder))

        # make a new version folder
        newVersionFolder = os.path.join(versionFolder, "{0}_{1:04d}".format(
            self.name, (numVersions + 1)))

        os.mkdir(newVersionFolder)

        for component in self.components:
            componentFile = self.getComponentPath(component)

            if componentFile and os.path.exists(componentFile):
                shutil.copy(componentFile, newVersionFolder)

            elif component == "weights":
                weightVersionFolder = os.mkdir(
                    os.path.join(newVersionFolder, "weights"))
                for weightFile in componentFile:
                    shutil.copy(weightFile, weightVersionFolder)

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
