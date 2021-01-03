import maya.standalone
import maya.cmds as cmds

def wrapStandalone(fn):
    def wrapper(*args, **kwargs):
        maya.standalone.initialize()

        result = fn(*args, **kwargs)

        maya.standalone.uninitialize()

        return result

    return wrapper


def wrapBuild(fn):
    def wrapper(self, *args, **kwargs):
        print(">>> Building limb type <{0}> : \'{1}\'\n".format(self.__class__.__name__, self.name))

        self.checkContract()
        self.makeNode()

        result = fn(self, *args, **kwargs)

        self.addNodeAttrs()
        self.connectComponents()
        self.connectBindJoints()
        self.parentModule()

        for transform in ['translate', 'rotate', 'scale']:
            for axis in ['X', 'Y', 'Z']:
                cmds.setAttr('{0}.{1}{2}'.format(self.modGrp, transform, axis), lock=True)

        for ctrl in self.components:
            for attr in ['scaleX', 'scaleY', 'scaleZ']:
                cmds.setAttr('{0}.{1}'.format(ctrl.ctrl, attr, lock=True))
            cmds.setAttr(ctrl.ctrl + '.visibility', lock=True)
            for grp in ctrl.groupHierarchy:
                for transform in ['translate', 'rotate', 'scale']:
                    for axis in ['X', 'Y', 'Z']:
                        cmds.setAttr('{0}.{1}{2}'.format(grp, transform, axis))

        self.captureComponentDefaults()
        
        return result 

    return wrapper
