import os

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.standalone


def wrapStandalone(fn):
    def wrapper(*args, **kwargs):
        maya.standalone.initialize()
        # maya.standalone.initialize(name="python")

        result = fn(*args, **kwargs)

        maya.standalone.uninitialize()

        return result

    return wrapper


def wrapBuild(fn):
    def wrapper(self, *args, **kwargs):
        print ">>> Building ",  self.__class__.__name__

        self.checkContract()
        self.makeNode()
        self.side = self.side.upper()

        result = fn(self, *args, **kwargs)

        self.addNodeAttrs()
        self.connectComponents()
        self.connectBindJoints()
        self.parentModule()
        self.lockTransforms([comp.grp for comp in self.components] + [self.modGrp])
        self.lockTransforms([comp.ctrl for comp in self.components], attrs=["scale", "visibility"])

        print "\n"

        return result 

    return wrapper