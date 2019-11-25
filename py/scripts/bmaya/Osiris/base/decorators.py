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

        self.lockTransforms([comp.grp for comp in self.components] + [self.modGrp])
        self.lockTransforms([comp.ctrl for comp in self.components], attrs=["scale", "visibility"])
        
        print "\n"

        return result 

    return wrapper


# # #
# attribute wrappers for tagging module attributes
# # #


def stringAttr(fn):
    def stringAttrWrapper(self, *args, **kwargs):
        return True
    return stringAttrWrapper

def intAttr(fn):
    def intAttrWrapper(self, *args, **kwargs):
        return True
    return intAttrWrapper

def boolAttr(fn):
    def boolAttrWrapper(self, *args, **kwargs):
        return True
    return boolAttrWrapper

def listAttr(fn):
    def listAttrWrapper(self, *args, **kwargs):
        return True
    return listAttrWrapper

def dictAttr(fn):
    def dictAttrWrapper(self, *args, **kwargs):
        return True
    return dictAttrWrapper

def enumAttr(fn):
    def enumAttrWrapper(self, *args, **kwargs):
        return True
    return enumAttrWrapper