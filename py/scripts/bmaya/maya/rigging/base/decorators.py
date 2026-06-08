"""Purpose:
Decorators for rigging operations that allow the user to run code before and after the main logic of a function,
such as initializing and uninitializing maya.standalone, or running code before and after building a rig.
That code can include things like locking attributes, capturing component defaults, etc.
"""

import maya.standalone
import maya.cmds as cmds
from bmaya.core import log


def wrapStandalone(fn):
    def wrapper(*args, **kwargs):
        maya.standalone.initialize()

        result = fn(*args, **kwargs)

        maya.standalone.uninitialize()

        return result

    return wrapper


def wrapBuild(fn):
    def wrapper(self, *args, **kwargs):
        log.info(
            ">>> Building limb type <{0}> : '{1}'\n".format(
                self.__class__.__name__, self.name
            )
        )

        self.checkContract()
        self.makeNode()

        result = fn(self, *args, **kwargs)

        self.addNodeAttrs()
        self.connectComponents()
        self.connectBindJoints()
        self.parentModule()

        for transform in ["translate", "rotate", "scale"]:
            for axis in ["X", "Y", "Z"]:
                cmds.setAttr(
                    "{0}.{1}{2}".format(self.modGrp, transform, axis),
                    lock=True,
                    keyable=False,
                )

        for ctrl in self.components:
            for attr in ["scaleX", "scaleY", "scaleZ"]:
                cmds.setAttr(
                    "{0}.{1}".format(ctrl.ctrl, attr, lock=True, keyable=False)
                )
            cmds.setAttr(ctrl.ctrl + ".visibility", lock=True, keyable=False)

            for grp in ctrl.groupHierarchy:
                for transform in ["translate", "rotate", "scale"]:
                    for axis in ["X", "Y", "Z"]:
                        cmds.setAttr(
                            "{0}.{1}{2}".format(grp, transform, axis),
                            lock=True,
                            keyable=False,
                        )

        self.captureComponentDefaults()

        return result

    return wrapper
