import json

import maya.cmds as cmds
import maya.OpenMaya as om

import character
import Osiris.lib.tools.shapes.lib as shapeLib

from decorators import wrapBuild


class Module(object):
    mirrorPairs = {"L": "R", "R": "L"}

    def __init__(self, character, name="module1", components=[], modType=None,
                 parent=None, side="L", mirror=False, contract={}, shapeType="cube"):

        self.character = character
        self.components = components
        self.bindJoints = []
        self.side = side
        self.modType = modType
        self.mirror = mirror
        self.parent = parent
        self.name = name
        self.node = None
        self.shapeType = shapeType

    def makeNode(self):
        # create the module node before anything gets built. 
        if not cmds.objExists(self.name + "_MOD"):
            # this creates a locator shape of the given name
            self.node = cmds.createNode("network", name=self.name + "_MOD")
            self.modGrp = cmds.createNode("transform", name=self.name + "_GRP")
            print ">>> Created {0} node >> {1} <<".format(self.modType, self.node)

    def addNodeAttrs(self):
        if not self.node:
            raise RuntimeError("Module node doesn't exist yet for " + self.name)

        for attr in self.__dict__:
            attrVal = self.__dict__[attr]
            attrType = type(attrVal)

            if isinstance(attrVal, character.Character):
                attrType = "message"

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
                    elif isinstance(val, character.Character):
                        cleanList.append(val.name)
                    elif isinstance(val, shapeLib.Shape):
                        cleanList.append(val.ctrl)

                attrType = "string"
                attrVal = json.dumps(cleanList)

            elif attrType is dict:
                cleanDict = {}

                for key in attrVal:
                    if type(attrVal[key]) in [unicode, str, int, float, bool, None]:
                        cleanDict[key] = attrVal[key]
                    elif isinstance(attrVal[key], character.Character):
                        cleanDict[key] = attrVal[key].name
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
            elif attrType == "message":
                cmds.addAttr(self.node, ln=attr, at=attrType, keyable=False)
            else:
                cmds.addAttr(self.node, ln=attr, at=attrType, dv=attrVal, keyable=False)


    def build(self):
        return

    def doMirror(self):
        if self.mirror:
            print ">>> Mirroring " + self.name

            mirrorSide = Module.mirrorPairs[self.side]

            # create a new instance of this class with mirrored attributes

            mirrorContract = {}
            
            for key in self.contract:
                value = self.contract[key]

                if isinstance(value, basestring):
                    mirrorContract[key] = self.findMirror(value)

                elif type(value) is list:
                    mirrorList = []
                    for j in value:
                        mirrorList.append(self.findMirror(j))

                    mirrorContract[key] = mirrorList

            # the mirror contract isn't getting set correctly


            mirrorSelf = self.__class__(character=self.character,
                                        contract=mirrorContract,
                                        side=mirrorSide,
                                        modType=self.modType,
                                        mirror=False,
                                        name=self.name.replace(self.side + "_", mirrorSide + "_"))

            mirrorSelf.build()

            return mirrorSelf

    def findMirror(self, node):
        """Returns the mirrored node of the same type if it's in the scene.
        Else returns None"""

        if not node:
            print "No mirror node found since given node was None"
            return

        mirrorSide = Module.mirrorPairs[self.side]

        mirrorNode = node.replace((self.side + "_"), (mirrorSide + "_"))

        nodeType = cmds.objectType(node)

        if mirrorNode in cmds.ls(type=nodeType):
            return mirrorNode
        else:
            raise RuntimeError("Mirror could not be found for >> " + node)

    def parentModule(self):
        # check if a specific joint parent was given. If not then check the parent of the startJoint
        # This means every module except Root will need a startJoint

        cmds.parent(self.modGrp, self.character.modulesGrp)

        if "startJoint" in self.contract.keys():
            startJoint = self.contract["startJoint"]
            parentJoint = cmds.listRelatives(startJoint, parent=True, type="joint")

            if parentJoint:
                moduleParent = parentJoint[0]
                # todo: this is where you could add a followSwitch option
            
            else:
                # parent to layout group
                moduleParent = "layout03_ctrl"

            self.parentConstrain(moduleParent, self.modGrp)

    def asDict(self):
        modDict = {key: value for key, value in self.__dict__.items() if "__" not in key}
        return modDict

    def parentConstrain(self, parent=None, childList=None, maintainOffset=True):

        if type(childList) in [str, unicode]:
            childList = [childList]

        for child in childList:
            cmds.parentConstraint(parent, child, mo=maintainOffset)

    def lockTransforms(self, ctrls, attrs=["translate", "rotate", "scale"]):
        if type(ctrls) in [str, unicode]:
            ctrls = [ctrls]

        for ctrl in ctrls:
            for attr in attrs:
                if attr in ["translate", "rotate", "scale"]:
                    for axis in ["X", "Y", "Z"]:
                        cmds.setAttr("{0}.{1}{2}".format(ctrl, attr, axis),
                                     lock=True, keyable=False, channelBox=False)
                else:
                    cmds.setAttr("{0}.{1}".format(ctrl, attr),
                                  lock=True, keyable=False, channelBox=False)

    def checkContract(self):
        for key in self.contract:
            if self.contract[key] == None:
                raise RuntimeError("Contract is not yet fulfilled")

        print ">>> Contract for {0} fulfilled".format(self.modType)
        return True

    def connectComponents(self):
        for ctrl in self.components:
            if not cmds.objExists(ctrl.ctrl + ".module"):
                cmds.addAttr(ctrl.ctrl, longName="module", attributeType="message")

            cmds.connectAttr(self.node + ".components", ctrl.ctrl + ".module")

            self.lockTransforms(ctrl.grp)

    def connectBindJoints(self):
        for jnt in self.bindJoints:
            if not cmds.objExists(jnt + ".module"):
                cmds.addAttr(jnt, longName="module", attributeType="message")
            else:
                raise RuntimeError("{0} already belongs to a module".format(jnt))

            cmds.connectAttr(self.node + ".bindJoints", jnt + ".module")

    def getContainedJoints(self):


        sel = om.MSelectionList()
        print self.contract['startJoint']
        sel.add(self.contract['startJoint'])
        dag = om.MDagPath()
        sel.getDagPath(0, dag)

        rootJnt = True

        itDag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kJoint)
        itDag.reset(dag, om.MItDag.kDepthFirst, om.MFn.kJoint)

        while not itDag.isDone():
            jnt = itDag.partialPathName()

            if jnt not in self.contract['exclude']:

                self.bindJoints.append(jnt)

                rootJnt = False

            else:
                itDag.prune()

            itDag.next()


    def checkContractJoint(self, contractKeys):
        """Check to see if all the given contract joints are unique to this module"""

        if isinstance(contractKeys, basestring):
            contractKeys = list(contractKeys)

        for contractKeys in contractKey

        if contractKey in self.contract.keys():
            if cmds.objExists(self.contract[contractKey] + '.module'):
                raise RuntimeError(
                    'Given startJoint <{0}> already belongs to a module'.format(self.contract[contractKey]))

            else:
                return True
        else:
            raise RuntimeError('<{0}> is not a part of the module contract.'.format(contractKey))


    def duplicateChain(self, joints):
        """Duplicate the given input chain"""
        
        
        