from bmaya.core import boundingBox, mathUtils

import maya.cmds as cmds

import bmaya.mayanode as mayanode

import shapedata

# However, to give us plenty of room to spare, we'll set the max amount of cvs to 256
CV_LIMIT = 128


class ControlCurve(mayanode.DagNode):
    def __init__(self, name='example_00_M_ctrl', shapeType='cube', scale=None, jnt=None):
        _controlMObj = mayanode.Curve.createLinearCurve(shapedata.CONTROL_TYPES_AND_VALUES[shapeType], CV_LIMIT)
        super(ControlCurve, self).__init__(_controlMObj)
        self.name = self.makeShortNameUnique(name)
        self.ctrl = self.shortName

        self.offsetGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_offsetGrp'))
        self.spaceGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_spaceGrp'))
        self.targetGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_targetGrp'))

        self.targetGrp.setParent(self.spaceGrp)
        self.spaceGrp.setParent(self.offsetGrp)
        self.setParent(self.targetGrp)

        self.groupHierarchy = [self.offsetGrp, self.spaceGrp, self.targetGrp]

        if scale:
            if isinstance(scale, list) and len(scale) == 3:
                self.scale = scale
            elif isinstance(scale, float):
                self.scale = [scale, scale, scale]
        if jnt:
            _jnt = mayanode.DagNode(jnt)
            for grp in self.groupHierarchy:
                grp.rotateOrder = _jnt.rotateOrder
            self.rotateOrder = _jnt.rotateOrder

            self.offsetGrp.matrix = _jnt.worldMatrix

        if shapeType == 'boundingBox':
            self.setupBoundingBox()

    @classmethod
    def setControlShape(cls, ctrlName, shapeType):

        _tempCurve = mayanode.DagNode(ctrlName)

        if shapeType in shapedata.CONTROL_TYPES_AND_VALUES.keys():
            _tempCurve.shape.setPoints(shapedata.CONTROL_TYPES_AND_VALUES[shapeType], space='object', cvLimit=CV_LIMIT)
        else:
            raise ValueError('Given shape type {0} not a valid shape yet.'.format(shapeType))

        del _tempCurve

    def setupBoundingBox(self):
        sceneBoundingBox = boundingBox.getSceneBoundingBox()

        if sceneBoundingBox.width() < 0.001:
            cmds.xform(self.shape + '.cv[0:]', scale=(1, 1, 1))
        else:
            cmds.xform(self.shape + '.cv[0:]', scale=(
            sceneBoundingBox.width() + .1, sceneBoundingBox.height() + .1, sceneBoundingBox.depth() + .1))

        cmds.xform(self.shape + '.cv[0:]', translation=boundingBox.getBoundingBoxCenter(sceneBoundingBox), relative=True)

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
