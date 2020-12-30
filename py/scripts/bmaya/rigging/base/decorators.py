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
        print(">>> Building limb type <{0}> : \'{1}\'\n".format(self.__class__.__name__, self.name))

        self.checkContract()
        self.makeNode()

        result = fn(self, *args, **kwargs)

        self.addNodeAttrs()
        self.connectComponents()
        self.connectBindJoints()
        self.parentModule()

        self.modGrp.lockTransforms()
        for ctrl in self.components:
            for attr in ['scaleX', 'scaleY', 'scaleZ']:
                ctrl.lockAttr(attr)
            ctrl.lockAttr('visibility')
            for grp in ctrl.groupHierarchy:
                grp.lockTransforms()
                grp.lockAttr('visibility')

        self.captureComponentDefaults()
        
        return result 

    return wrapper
