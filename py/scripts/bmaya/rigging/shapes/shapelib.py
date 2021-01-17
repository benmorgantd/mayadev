import maya.cmds as cmds

from bmaya.core import boundingBox, mathUtils
# import bmaya.mayanode as mayanode

import shapedata

# However, to give us plenty of room to spare, we'll set the max amount of cvs to 256
CV_LIMIT = 128


class ControlCurve(object):
    types = {
        'cylinder': [(-0.5, 0.99, 0.88), (0.5, 0.99, 0.88), (0.5, -0.99, 0.88), (0.99, -0.99, 0.0), (0.99, 0.99, 0.0),
                     (0.5, 0.99, -0.88), (0.5, -0.99, -0.88), (-0.5, -0.99, -0.88), (-0.5, 0.99, -0.88),
                     (-0.99, 0.99, -0.0), (-0.99, -0.99, -0.0), (-0.5, -0.99, 0.88), (-0.5, 0.99, 0.88),
                     (-0.99, 0.99, -0.0), (-0.5, 0.99, -0.88), (0.5, 0.99, -0.88), (0.99, 0.99, 0.0), (0.5, 0.99, 0.88),
                     (0.5, -0.99, 0.88), (-0.5, -0.99, 0.88), (-0.99, -0.99, -0.0), (-0.5, -0.99, -0.88),
                     (0.5, -0.99, -0.88), (0.5, -0.99, 0.88)],
        'square': [(1.0, 0.0, 1.0), (1.0, 0.0, -1.0), (-1.0, 0.0, -1.0), (-1.0, 0.0, 1.0), (1.0, 0.0, 1.0)],
        'triangle': [(0.0, 0.0, -0.97), (-0.97, 0.0, 0.65), (0.97, 0.0, 0.65), (0.0, 0.0, -0.97)],
        'halfCircleArrow': [(0.14, -0.0, 0.95), (0.52, 0.0, 0.86), (0.84, 0.0, 0.6), (1.02, 0.0, 0.23),
                            (1.02, -0.0, -0.18), (0.84, -0.0, -0.56), (1.07, -0.0, -0.74), (0.14, -0.0, -0.97),
                            (0.14, 0.0, -0.02), (0.39, 0.0, -0.2), (0.46, 0.0, -0.06), (0.46, -0.0, 0.1),
                            (0.39, -0.0, 0.24), (0.27, -0.0, 0.34), (0.14, -0.0, 0.38), (0.14, -0.0, 0.67),
                            (0.14, -0.0, 0.95)],
        'archedDoubleArrow': [(-0.22, 0.98, 0.0), (-0.22, 0.95, 0.22), (-0.22, 0.88, 0.42), (-0.22, 0.76, 0.61),
                              (-0.22, 0.61, 0.76), (-0.22, 0.42, 0.88), (-0.44, 0.42, 0.88), (-0.22, 0.22, 0.95),
                              (0.0, 0.0, 0.97), (0.22, 0.22, 0.95), (0.44, 0.42, 0.88), (0.22, 0.42, 0.88),
                              (0.22, 0.61, 0.76), (0.22, 0.76, 0.61), (0.22, 0.88, 0.42), (0.22, 0.95, 0.22),
                              (0.22, 0.98, 0.0), (0.22, 0.95, -0.22), (0.22, 0.88, -0.42), (0.22, 0.76, -0.61),
                              (0.22, 0.61, -0.76), (0.22, 0.42, -0.88), (0.44, 0.42, -0.88), (0.22, 0.22, -0.95),
                              (0.0, 0.0, -0.97), (-0.22, 0.22, -0.95), (-0.44, 0.42, -0.88), (-0.22, 0.42, -0.88),
                              (-0.22, 0.61, -0.76), (-0.22, 0.76, -0.61), (-0.22, 0.88, -0.42), (-0.22, 0.95, -0.22),
                              (-0.22, 0.98, 0.0)],
        'circleArrow': [(0.0, -0.0, 0.98), (0.4, 0.0, 0.88), (0.75, 0.0, 0.62), (0.94, 0.0, 0.24), (0.94, -0.0, -0.19),
                        (0.75, -0.0, -0.57), (0.99, -0.0, -0.76), (0.0, -0.0, -1.0), (0.0, 0.0, -0.02),
                        (0.27, 0.0, -0.2), (0.34, 0.0, -0.06), (0.34, -0.0, 0.1), (0.27, -0.0, 0.25),
                        (0.14, -0.0, 0.35), (0.0, -0.0, 0.39), (0.0, -0.0, 0.68), (0.0, -0.0, -0.01),
                        (0.0, -0.0, -0.69), (0.0, -0.0, -0.4), (-0.13, -0.0, -0.36), (-0.26, -0.0, -0.26),
                        (-0.34, -0.0, -0.11), (-0.34, 0.0, 0.05), (-0.26, 0.0, 0.19), (0.0, 0.0, 0.01),
                        (0.0, -0.0, 0.99), (-0.98, -0.0, 0.75), (-0.74, -0.0, 0.56), (-0.94, -0.0, 0.18),
                        (-0.94, 0.0, -0.25), (-0.74, 0.0, -0.63), (-0.4, 0.0, -0.9), (0.0, -0.0, -0.99)],
        'dome': [(0.0, 0.0, -0.98), (-0.49, 0.0, -0.85), (-0.85, 0.0, -0.49), (-0.98, -0.0, 0.0), (-0.85, -0.0, 0.49),
                 (-0.49, -0.0, 0.85), (-0.0, -0.0, 0.98), (0.49, -0.0, 0.85), (0.85, -0.0, 0.49), (0.98, 0.0, -0.0),
                 (0.85, 0.0, -0.49), (0.49, 0.0, -0.85), (0.0, 0.0, -0.98), (-0.0, 0.49, -0.85), (0.0, 0.85, -0.49),
                 (0.0, 0.98, 0.0), (0.0, 0.85, 0.49), (0.0, 0.49, 0.85), (0.0, -0.0, 0.98), (0.0, 0.0, -0.98),
                 (-0.49, 0.0, -0.85), (-0.85, 0.0, -0.49), (-0.98, -0.0, 0.0), (-0.85, 0.49, 0.0), (-0.49, 0.85, 0.0),
                 (0.0, 0.98, 0.0), (0.49, 0.85, -0.0), (0.85, 0.49, -0.0), (0.98, -0.0, -0.0), (-0.98, 0.0, -0.0)],
        'sphere': [(0.0, 1.0, 0.0), (0.0, 0.92, 0.38), (0.0, 0.71, 0.71), (0.0, 0.38, 0.92), (0.0, 0.0, 1.0),
                   (0.0, -0.38, 0.92), (0.0, -0.71, 0.71), (0.0, -0.92, 0.38), (0.0, -1.0, 0.0), (0.0, -0.92, -0.38),
                   (0.0, -0.71, -0.71), (0.0, -0.38, -0.92), (0.0, 0.0, -1.0), (0.0, 0.38, -0.92), (0.0, 0.71, -0.71),
                   (0.0, 0.92, -0.38), (0.0, 1.0, 0.0), (-0.38, 0.92, 0.0), (-0.71, 0.71, 0.0), (-0.92, 0.38, 0.0),
                   (-1.0, 0.0, 0.0), (-0.92, -0.38, 0.0), (-0.71, -0.71, 0.0), (-0.38, -0.92, 0.0), (0.0, -1.0, 0.0),
                   (0.38, -0.92, 0.0), (0.71, -0.71, 0.0), (0.92, -0.38, 0.0), (1.0, 0.0, 0.0), (0.92, 0.38, 0.0),
                   (0.71, 0.71, 0.0), (0.38, 0.92, 0.0), (0.0, 1.0, 0.0), (0.0, 0.92, 0.38), (0.0, 0.71, 0.71),
                   (0.0, 0.38, 0.92), (0.0, 0.0, 1.0), (-0.5, 0.0, 0.87), (-0.87, 0.0, 0.5), (-1.0, 0.0, 0.0),
                   (-0.87, 0.0, -0.5), (-0.5, 0.0, -0.87), (0.0, 0.0, -1.0), (0.5, 0.0, -0.87), (0.87, 0.0, -0.5),
                   (1.0, 0.0, 0.0), (0.87, 0.0, 0.5), (0.5, 0.0, 0.87), (0.0, 0.0, 1.0)],
        'cube': [(0.99, -0.99, 0.99), (0.99, -0.99, -0.99), (-0.99, -0.99, -0.99), (-0.99, -0.99, 0.99),
                 (0.99, -0.99, 0.99), (0.99, 0.99, 0.99), (-0.99, 0.99, 0.99), (-0.99, -0.99, 0.99),
                 (-0.99, 0.99, 0.99), (-0.99, 0.99, -0.99), (-0.99, -0.99, -0.99), (-0.99, 0.99, -0.99),
                 (0.99, 0.99, -0.99), (0.99, -0.99, -0.99), (0.99, 0.99, -0.99), (0.99, 0.99, 0.99)],
        'singleArrow': [(0.0, 0.0, 0.0), (-0.14, 0.0, -0.0), (-0.14, 0.0, 0.14), (-0.14, 0.0, 0.71), (-0.28, 0.0, 0.71),
                        (0.0, 0.0, 0.99), (0.28, 0.0, 0.71), (0.14, 0.0, 0.71), (0.14, 0.0, 0.0), (0.0, 0.0, 0.0)],
        'fourArrow': [(-0.2, 0.0, -0.4), (-0.2, 0.0, -0.59), (-0.4, 0.0, -0.59), (-0.0, 0.0, -0.99), (0.4, 0.0, -0.59),
                      (0.2, 0.0, -0.59), (0.2, 0.0, -0.4), (0.2, 0.0, -0.2), (0.59, 0.0, -0.2), (0.59, 0.0, -0.4),
                      (0.99, 0.0, 0.0), (0.59, 0.0, 0.4), (0.59, 0.0, 0.2), (0.2, 0.0, 0.2), (0.2, 0.0, 0.59),
                      (0.4, 0.0, 0.59), (-0.0, 0.0, 0.99), (-0.4, 0.0, 0.59), (-0.2, 0.0, 0.59), (-0.2, 0.0, 0.2),
                      (-0.59, 0.0, 0.2), (-0.59, 0.0, 0.4), (-0.99, 0.0, 0.0), (-0.59, 0.0, -0.4), (-0.59, 0.0, -0.2),
                      (-0.2, 0.0, -0.2), (-0.2, 0.0, -0.4)],
        'circleStick': [(0.0, 0.0, 0.0), (0.0, 0.0, 0.61), (0.12, 0.0, 0.65), (0.19, 0.0, 0.75), (0.19, -0.0, 0.87),
                        (0.12, -0.0, 0.97), (-0.0, -0.0, 1.01), (-0.12, -0.0, 0.97), (-0.19, -0.0, 0.87),
                        (-0.19, 0.0, 0.75), (-0.12, 0.0, 0.65), (0.0, 0.0, 0.61), (-0.0, -0.0, 1.01),
                        (0.12, -0.0, 0.97), (0.19, -0.0, 0.87), (0.19, 0.0, 0.81), (-0.19, 0.0, 0.81)],
        'boundingBox': [(1.0, -1.0, 1.0), (1.0, -1.0, -1.0), (-1.0, -1.0, -1.0), (-1.0, -1.0, 1.0), (1.0, -1.0, 1.0),
                        (1.0, 1.0, 1.0), (-1.0, 1.0, 1.0), (-1.0, -1.0, 1.0), (-1.0, 1.0, 1.0), (-1.0, 1.0, -1.0),
                        (-1.0, -1.0, -1.0), (-1.0, 1.0, -1.0), (1.0, 1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0),
                        (1.0, 1.0, 1.0)],
        'circle': [(0.0, 0.0, -1.0), (-0.38, 0.0, -0.92), (-0.71, 0.0, -0.71), (-0.92, 0.0, -0.38), (-1.0, -0.0, 0.0),
                   (-0.92, -0.0, 0.38), (-0.71, -0.0, 0.71), (-0.38, -0.0, 0.92), (0.0, -0.0, 1.0), (0.38, -0.0, 0.92),
                   (0.71, -0.0, 0.71), (0.92, -0.0, 0.38), (1.0, 0.0, -0.0), (0.92, 0.0, -0.38), (0.71, 0.0, -0.71),
                   (0.38, 0.0, -0.92), (-0.0, 0.0, -1.0)],
        'pointedCircle': [(0.0, 0.0, -3.0), (-0.927051, 0.0, -2.853171), (-1.763355, 0.0, -2.427051),
                          (-2.427051, 0.0, -1.763355), (-2.853171, 0.0, -0.927051), (-3.0, 0.0, 0.0),
                          (-2.853171, 0.0, 0.927051), (-2.427051, 0.0, 1.763355), (-1.763355, 0.0, 2.427051),
                          (-0.927051, 0.0, 2.853171), (0.0, 0.0, 3.9999990000000003), (0.927051, 0.0, 2.853171),
                          (1.763355, 0.0, 2.427051), (2.427051, 0.0, 1.763355), (2.853171, 0.0, 0.927051),
                          (3.0, 0.0, 0.0), (2.853171, 0.0, -0.927051), (2.427051, 0.0, -1.763355),
                          (1.763355, 0.0, -2.427051), (0.927051, 0.0, -2.853171), (0.0, 0.0, -3.0)],
        'pivot': [(-0.154, 1.5, 0.154), (0.154, 1.5, 0.154), (0.024, 0.022, 0.021), (1.5, 0.154, 0.159),
                  (1.5, -0.154, 0.159), (0.024, -0.022, 0.021), (0.154, -1.5, 0.154), (-0.154, -1.5, 0.154),
                  (-0.024, -0.022, 0.021), (-1.5, -0.154, 0.159), (-1.5, 0.154, 0.159), (-0.024, 0.022, 0.021),
                  (-0.154, 1.5, 0.154), (-0.154, 1.5, -0.154), (-0.024, 0.022, -0.021), (-0.177, 0.164, -1.5),
                  (-0.177, -0.164, -1.5), (-0.024, -0.022, -0.021), (-0.154, -1.5, -0.154), (-0.154, -1.5, 0.154),
                  (-0.024, -0.022, 0.021), (-0.177, -0.164, 1.5), (-0.177, 0.164, 1.5), (-0.024, 0.022, 0.021),
                  (-0.154, 1.5, 0.154), (0.154, 1.5, 0.154), (0.024, 0.022, 0.021), (0.177, 0.164, 1.5),
                  (0.177, -0.164, 1.5), (0.024, -0.022, 0.021), (0.154, -1.5, 0.154), (0.154, -1.5, -0.154),
                  (0.024, -0.022, -0.021), (0.177, -0.164, -1.5), (0.177, 0.164, -1.5), (0.024, 0.022, -0.021),
                  (0.154, 1.5, -0.154), (0.154, 1.5, 0.154), (0.154, 1.5, -0.154), (0.024, 0.022, -0.021),
                  (1.5, 0.154, -0.159), (1.5, -0.154, -0.159), (0.024, -0.022, -0.021), (0.154, -1.5, -0.154),
                  (-0.154, -1.5, -0.154), (-0.024, -0.022, -0.021), (-1.5, -0.154, -0.159), (-1.5, 0.154, -0.159),
                  (-0.024, 0.022, -0.021), (-0.154, 1.5, -0.154), (0.154, 1.5, -0.154), (0.024, 0.022, -0.021),
                  (0.024, 0.022, 0.021), (1.5, 0.154, 0.159), (1.5, 0.154, -0.159), (1.5, -0.154, -0.159),
                  (1.5, -0.154, 0.159), (0.024, -0.022, 0.021), (0.024, -0.022, -0.021), (0.024, 0.022, -0.021),
                  (0.024, -0.022, -0.021), (-0.024, -0.022, -0.021), (-0.177, -0.164, -1.5), (0.177, -0.164, -1.5),
                  (0.177, 0.164, -1.5), (-0.177, 0.164, -1.5), (-0.024, 0.022, -0.021), (0.024, 0.022, -0.021),
                  (-0.024, 0.022, -0.021), (-0.024, 0.022, 0.021), (-1.5, 0.154, 0.159), (-1.5, 0.154, -0.159),
                  (-1.5, -0.154, -0.159), (-1.5, -0.154, 0.159), (-0.024, -0.022, 0.021), (-0.024, -0.022, -0.021),
                  (-0.024, -0.022, 0.021), (0.024, -0.022, 0.021), (0.024, 0.022, 0.021), (-0.024, 0.022, 0.021),
                  (-0.024, -0.022, 0.021), (-0.024, 0.022, 0.021), (-0.024, 0.022, -0.021), (-0.024, -0.022, -0.021),
                  (-0.024, 0.022, -0.021), (-0.024, 0.022, 0.021), (-0.177, 0.164, 1.5), (0.177, 0.164, 1.5),
                  (0.177, -0.164, 1.5), (-0.177, -0.164, 1.5)],
        'diamond': [(0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (-1.0, 0.0, 0.0), (0.0, 0.0, -1.0),
                    (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0),
                    (0.0, -1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0),
                    (0.0, 0.0, -1.0)]}

    def __init__(self, name='example_00_M_ctrl', shapeType='cube', scale=None, jnt=None):
        self.name = name
        self.shapeType = shapeType
        self.ctrl = None
        self.ctrlShape = None
        self.ctrlGrp = None
        self.scale = scale
        self.jnt = jnt

        self.build()

    def __str__(self):
        return self.ctrl

    def __repr__(self):
        return self.ctrl

    def build(self):
        if self.shapeType not in self.types.keys():
            print 'Given shape type is not valid. Defaulting to cube.'
            self.shapeType = 'cube'

        cmds.select(clear=True)

        self.ctrl = cmds.curve(degree=1, point=self.types[self.shapeType], name=self.name, worldSpace=True)

        self.shape = cmds.listRelatives(self.ctrl, type='shape')

        if self.scale:
            cmds.xform(self.ctrl + '.cv[0:]', scale=(self.scale, self.scale, self.scale), relative=True)

        # make offsetGrp>>spaceGrp>>targetGrp>>ctrl

        self.offsetGrp = cmds.group(empty=True, name=self.name + '_offsetGrp')
        self.spaceGrp = cmds.group(empty=True, name=self.name + '_spaceGrp', parent=self.offsetGrp)
        self.targetGrp = cmds.group(empty=True, name=self.name + '_targetGrp', parent=self.spaceGrp)

        cmds.parent(self.ctrl, self.targetGrp)

        self.groupHierarchy = [self.offsetGrp, self.spaceGrp, self.targetGrp]

        if self.jnt:
            rotateOrder = cmds.getAttr(self.jnt + '.rotateOrder')

            # have the hierarchy share the same rotate order
            for grp in self.groupHierarchy + [self.ctrl]:
                cmds.setAttr(grp + '.rotateOrder', rotateOrder)

        if self.shapeType == 'boundingBox':
            self.setupBoundingBox()

        if self.jnt:
            mathUtils.matchTransforms(self.jnt, self.offsetGrp)

    def setupBoundingBox(self):
        sceneBoundingBox = boundingBox.getSceneBoundingBox()

        if sceneBoundingBox.width() < 0.001:
            cmds.xform(self.ctrl + '.cv[0:]', scale=(1, 1, 1))

        else:
            cmds.xform(self.ctrl + '.cv[0:]', scale=(
            sceneBoundingBox.width() + .1, sceneBoundingBox.height() + .1, sceneBoundingBox.depth() + .1))

        cmds.xform(self.ctrl + '.cv[0:]', translation=boundingBox.getBoundingBoxCenter(sceneBoundingBox), relative=True)

    @classmethod
    def drawLine(cls, name, pointA, pointB, parentNode):
        crv = cmds.curve(degree=1, p=[(0, 0, 0), (1, 0, 0)], name=name)
        crvShape = cmds.listRelatives(crv, shapes=True)[0]

        decompA = cmds.shadingNode('decomposeMatrix', asUtility=True, name=name + '_decompMatrixA')
        decompB = cmds.shadingNode('decomposeMatrix', asUtility=True, name=name + '_decompMatrixB')
        cmds.connectAttr(pointA + '.worldMatrix[0]', decompA + '.inputMatrix')
        cmds.connectAttr(pointB + '.worldMatrix[0]', decompB + '.inputMatrix')

        cmds.connectAttr(decompA + '.outputTranslate', crvShape + '.controlPoints[0]')
        cmds.connectAttr(decompB + '.outputTranslate', crvShape + '.controlPoints[1]')

        cmds.parent(crv, parentNode, a=1)
        cmds.setAttr(crv + '.inheritsTransform', 0)
        cmds.setAttr(crvShape + '.template', 1)

        cmds.xform(crv, translation=(0, 0, 0), a=1, ws=1)
        cmds.xform(crv, rotation=(0, 0, 0), a=1, ws=1)

        cmds.select(cl=1)

        return [crv, crvShape]


# class ControlCurveMayanode(mayanode.DagNode):
#     def __init__(self, name='example_00_M_ctrl', shapeType='cube', scale=None, jnt=None):
#         _controlMObj = mayanode.Curve.createLinearCurve(shapedata.CONTROL_TYPES_AND_VALUES[shapeType], CV_LIMIT)
#         super(ControlCurve, self).__init__(_controlMObj)
#         self.name = self.makeShortNameUnique(name)
#         self.ctrl = self.shortName
#
#         self.offsetGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_offsetGrp'))
#         self.spaceGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_spaceGrp'))
#         self.targetGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_targetGrp'))
#
#         self.targetGrp.setParent(self.spaceGrp)
#         self.spaceGrp.setParent(self.offsetGrp)
#         self.setParent(self.targetGrp)
#
#         self.groupHierarchy = [self.offsetGrp, self.spaceGrp, self.targetGrp]
#
#         if scale:
#             if isinstance(scale, list) and len(scale) == 3:
#                 self.scale = scale
#             elif isinstance(scale, float):
#                 self.scale = [scale, scale, scale]
#         if jnt:
#             _jnt = mayanode.DagNode(jnt)
#             for grp in self.groupHierarchy:
#                 grp.rotateOrder = _jnt.rotateOrder
#             self.rotateOrder = _jnt.rotateOrder
#
#             self.offsetGrp.matrix = _jnt.worldMatrix
#
#         if shapeType == 'boundingBox':
#             self.setupBoundingBox()
#
#     @classmethod
#     def setControlShape(cls, ctrlName, shapeType):
#
#         _tempCurve = mayanode.DagNode(ctrlName)
#
#         if shapeType in shapedata.CONTROL_TYPES_AND_VALUES.keys():
#             _tempCurve.shape.setPoints(shapedata.CONTROL_TYPES_AND_VALUES[shapeType], space='object', cvLimit=CV_LIMIT)
#         else:
#             raise ValueError('Given shape type {0} not a valid shape yet.'.format(shapeType))
#
#         del _tempCurve
#
#     def setupBoundingBox(self):
#         sceneBoundingBox = boundingBox.getSceneBoundingBox()
#
#         if sceneBoundingBox.width() < 0.001:
#             cmds.xform(self.shape + '.cv[0:]', scale=(1, 1, 1))
#         else:
#             cmds.xform(self.shape + '.cv[0:]', scale=(
#                 sceneBoundingBox.width() + .1, sceneBoundingBox.height() + .1, sceneBoundingBox.depth() + .1))
#
#         cmds.xform(self.shape + '.cv[0:]', translation=boundingBox.getBoundingBoxCenter(sceneBoundingBox),
#                    relative=True)
#
    # @classmethod
    # def drawLine(cls, name, pointA, pointB, parentNode):
    #     crv = cmds.curve(degree=1, p=[(0, 0, 0), (1, 0, 0)], name=name)
    #     crvShape = cmds.listRelatives(crv, shapes=True)[0]
    #
    #     decompA = cmds.shadingNode('decomposeMatrix', asUtility=True, name=name + '_decompMatrixA')
    #     decompB = cmds.shadingNode('decomposeMatrix', asUtility=True, name=name + '_decompMatrixB')
    #     cmds.connectAttr(pointA + '.worldMatrix[0]', decompA + '.inputMatrix')
    #     cmds.connectAttr(pointB + '.worldMatrix[0]', decompB + '.inputMatrix')
    #
    #     cmds.connectAttr(decompA + '.outputTranslate', crvShape + '.controlPoints[0]')
    #     cmds.connectAttr(decompB + '.outputTranslate', crvShape + '.controlPoints[1]')
    #
    #     cmds.parent(crv, parentNode, a=1)
    #     cmds.setAttr(crv + '.inheritsTransform', 0)
    #     cmds.setAttr(crvShape + '.template', 1)
    #
    #     cmds.xform(crv, translation=(0, 0, 0), a=1, ws=1)
    #     cmds.xform(crv, rotation=(0, 0, 0), a=1, ws=1)
    #
    #     cmds.select(cl=1)
    #
    #     return [crv, crvShape]
