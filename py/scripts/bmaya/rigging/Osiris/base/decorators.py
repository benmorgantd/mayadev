import maya.standalone

def wrapStandalone(fn):
    def wrapper(*args, **kwargs):
        maya.standalone.initialize()

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

        self.lockTransforms(self.modGrp)
        self.lockTransforms([comp.ctrl for comp in self.components], attrs=["scale", "visibility"])

        for comp in self.components:
            for grp in comp.groupHierarchy:
                self.lockTransforms(grp, lock=False, attrs=['translate', 'rotate', 'scale', 'visibility'])
        
        print "\n"

        return result 

    return wrapper
