import json
import os

import maya.cmds as cmds

from . import asset

from ..tools.shapes import lib as shapeLib
from ..tools.shapes import io as shapeIO
from ..tools.weights import io as weightIO
from ..tools.build import io as buildIO


class Character(asset.Asset):
    """CharBase is the base class for all rigs created with Osiris"""

    def __init__(self, name, project, assetType):
        super(Character, self).__init__(name, project, assetType)

        self.skinClusters = []
        # an array of dictionary representations of our module classes
        self.modules = []
        self.buildData = None

        self.skeletonPath = self.getComponentRoot("skeleton")
        self.meshPath = self.getComponentRoot("mesh")
        self.cvsPath = self.getComponentRoot("cvs")
        self.weightsPath = self.getComponentRoot("weights")
        self.buildPath = self.getComponentRoot("build")

        self.componentsSet = None

    def addModule(self, moduleDict):
        # pass it the dictionary representation of the module
        # this way we can add modules from file or object data

        self.modules.append(moduleDict)

    def build(self):

        self.modules = []
        self.allControls = []
        mirrorModules = []

        # create a new scene
        cmds.file(new=True, force=True)

        self.makeNode()

        # open up the character's build file
        self.buildData = buildIO.load(self.getComponentPath("build"))

        for mod in self.buildData:
            mod["character"] = self
            self.addModule(mod)

        # create the new class instance from the string
        from .. import rigMods

        for mod in self.modules:
            # access the modType attribute from the module's dictionary
            modType = mod["modType"]

            modInstance = rigMods._MODULE_CLASSES[modType].__new__(rigMods._MODULE_CLASSES[modType])
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
                mirrorModules.append(mirrorInstance.asDict())
                self.allControls += [comp.ctrl for comp in mirrorInstance.components]

        self.modules += mirrorModules
        
        self.componentSet = cmds.sets(self.allControls, name="ctrl_SET")
        cmds.sets(self.componentSet, include="master_SET")

        self.skin()

        self.addNodeAttrs()

        for mod in self.modules:
            if cmds.objExists(mod["name"] + "_MOD"):
                cmds.connectAttr(self.node + ".modules", mod["name"] + "_MOD.character")

        shapeIO.load(self.getComponentPath("cvs"))

        weightRoot = os.path.join(self.getRootDir(), self.getComponentRoot("weights"))

        for weightPath in self.getFiles(self.getComponentPath("weights")):
            weightIO.load(os.path.join(weightRoot, os.path.basename(weightPath)))

        cmds.file(rename=self.getComponentPath("animRig"))
        cmds.file(save=True, type="mayaAscii", force=True)
        self.versionFile(self.getComponentPath("animRig"))

    def makeNode(self):
        if not cmds.objExists(self.name + "_CHAR"):
            self.node = cmds.createNode("network", name=self.name + "_CHAR")
            print ">>> Created character node >> {0} <<".format(self.node)

    def addNodeAttrs(self):
        from . import module

        if not self.node:
            raise RuntimeError("Character node doesn't exist yet for " + self.name)

        for attr in self.__dict__:
            attrVal = self.__dict__[attr]
            attrType = type(attrVal)

            if attrVal is None:
                attrType = "string"
                attrVal = "None"

            if attrType in [unicode, str]:
                attrType = "string"
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
                            elif isinstance(val[key], shapeLib.Shape):
                                cleanDict[key] = val[key].ctrl
                        cleanList.append(cleanDict)
                    elif isinstance(val, shapeLib.Shape):
                        cleanList.append(val.ctrl)

                attrType = "string"
                attrVal = json.dumps(cleanList)

            elif attrType is dict:
                cleanDict = {}
                for key in attrVal:
                    if type(attrVal[key]) in [unicode, str, int, float, bool, None]:
                        cleanDict[key] = attrVal[key]
                    elif isinstance(attrVal[key], shapeLib.Shape):
                        cleanDict[key] = attrVal[key].ctrl

                attrType = "string"
                attrVal = json.dumps(cleanDict)

            elif attrType == bool:
                attrType = "bool"
                attrVal = attrVal

            if attrType == "string":
                cmds.addAttr(self.node, ln=attr, dt="string", keyable=False)
                cmds.setAttr(self.node + "." + attr, str(attrVal), type="string")
            else:
                cmds.addAttr(self.node, ln=attr, at=attrType, dv=attrVal, keyable=False)

    def skin(self):
        # check for existing weights files. If not then skin to skeleton set
        # skin the root joint to all the meshes in the scene
        for mesh in cmds.sets(self.meshSet, query=True):
            self.skinClusters.append(cmds.skinCluster(self.skeletonSet, mesh,
                                                      maximumInfluences=1,
                                                      bindMethod=1,
                                                      weightDistribution=1,
                                                      normalizeWeights=2)[0])

# import Osiris.lib.base.character as character;helm = character.Character("Helm","dev","prop");helm.build();
