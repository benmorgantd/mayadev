from bm.maya.utils import boundingBox

import maya.cmds as cmds


class Shape(object):
    types = {"cube": [(.5, -.5, .5),    (.5, -.5, -.5),    (-.5, -.5, -.5),
                      (-.5, -.5, .5), (.5, -.5, .5),     (.5, .5, .5),
                      (-.5, .5, .5),    (-.5, -.5, .5),    (-.5, .5, .5),
                      (-.5, .5, -.5), (-.5, -.5, -.5), (-.5, .5, -.5),
                      (.5, .5, -.5),    (.5, -.5, -.5),    (.5, .5, -.5),
                      (.5, .5, .5)],
             "triangle": [(0, 0, -3), (-3, 0, 2), (3, 0, 2), (0, 0, -3)],
             "square": [(.5, -.5, .5),    (.5, -.5, -.5),    (-.5, -.5, -.5),
                        (-.5, -.5, .5), (.5, -.5, .5)],
             "boundingBox": [(.5, -.5, .5),    (.5, -.5, -.5),    (-.5, -.5, -.5),
                             (-.5, -.5, .5), (.5, -.5, .5),     (.5, .5, .5),
                             (-.5, .5, .5),    (-.5, -.5, .5),    (-.5, .5, .5),
                             (-.5, .5, -.5), (-.5, -.5, -.5), (-.5, .5, -.5),
                             (.5, .5, -.5),    (.5, -.5, -.5),    (.5, .5, -.5),
                             (.5, .5, .5)],
             "cylinder": [(-0.5000001192092896, 1.0, 0.8660253882408142),
                          (0.4999999701976776, 1.0, 0.866025447845459),
                          (0.4999999701976776, -1.0, 0.866025447845459),
                          (1.0, -1.0, 0.0), (1.0, 1.0, 0.0),
                          (0.5000002384185791, 1.0, -0.8660253286361694),
                          (0.5000002384185791, -1.0, -0.8660253286361694),
                          (-0.49999985098838806, -1.0, -0.8660255074501038),
                          (-0.49999985098838806, 1.0, -0.8660255074501038),
                          (-1.0, 1.0, -1.4901161193847656e-07),
                          (-1.0, -1.0, -1.4901161193847656e-07),
                          (-0.5000001192092896, -1.0, 0.8660253882408142),
                          (-0.5000001192092896, 1.0, 0.8660253882408142),
                          (-1.0, 1.0, -1.4901161193847656e-07),
                          (-0.49999985098838806, 1.0, -0.8660255074501038),
                          (0.5000002384185791, 1.0, -0.8660253286361694),
                          (1.0, 1.0, 0.0), (0.4999999701976776, 1.0, 0.866025447845459),
                          (0.4999999701976776, -1.0, 0.866025447845459),
                          (-0.5000001192092896, -1.0, 0.8660253882408142),
                          (-1.0, -1.0, -1.4901161193847656e-07),
                          (-0.49999985098838806, -1.0, -0.8660255074501038),
                          (0.5000002384185791, -1.0, -0.8660253286361694)]
             }

    def __init__(self, name, shapeType="cube", scale=None, jnt=None):
        self.name = name
        self.shapeType = shapeType
        self.ctrl = None
        self.ctrlShape = None
        self.ctrlGrp = None
        self.scale = scale
        self.jnt = jnt

        self.build()

    def build(self):
        if self.shapeType not in Shape.types.keys():
            print "Given shape type is not valid. Defaulting to cube."
            self.shapeType = "cube"

        cmds.select(clear=True)

        self.ctrl = cmds.curve(degree=1,
                               point=Shape.types[self.shapeType],
                               name=self.name + "_ctrl", worldSpace=True)

        self.shape = cmds.listRelatives(self.ctrl, type="shape")

        if self.scale:
            cmds.xform(
                self.ctrl + ".cv[0:]", scale=(self.scale, self.scale, self.scale), relative=True)

        self.grp = cmds.group(
            self.ctrl, name=self.ctrl + "_grp", absolute=True)

        if self.jnt:
            cmds.setAttr(self.ctrl + ".rotateOrder",
                         cmds.getAttr(self.jnt + ".rotateOrder"))
            cmds.setAttr(self.grp + ".rotateOrder",
                         cmds.getAttr(self.jnt + ".rotateOrder"))

        if self.shapeType == "boundingBox":
            self.setupBoundingBox()

        if self.jnt:
            cmds.delete(cmds.parentConstraint(self.jnt, self.grp, mo=0))

    def setupBoundingBox(self):
        sceneBoundingBox = boundingBox.getSceneBoundingBox()

        cmds.xform(self.ctrl + ".cv[0:]",
                   scale=[sceneBoundingBox.width(),
                          sceneBoundingBox.height(),
                          sceneBoundingBox.depth()])

        cmds.xform(self.ctrl + ".cv[0:]",
                   translation=boundingBox.getBoundingBoxCenter(sceneBoundingBox),
                   relative=True)
