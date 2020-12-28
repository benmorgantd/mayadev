from bmaya.core import boundingBox, mathUtils

import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya import mayanode

import shapedata


class ControlCurve(mayanode.DagNode):
    def __init__(self, name='example_00_M_ctrl', shapeType='cube', scale=None, jnt=None):
        _controlMObj = mayanode.Curve.createLinearCurve(shapedata.CONTROL_TYPES_AND_VALUES[shapeType])
        super(ControlCurve, self).__init__(_controlMObj)
        self.name = mayanode.DagNode.makeShortNameUnique(name)

        self.offsetGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_offsetGrp'))
        self.spaceGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_spaceGrp'))
        self.targetGrp = mayanode.DagNode(cmds.group(empty=True, name=self.shortName + '_targetGrp'))

        self.targetGrp.parent = self.spaceGrp
        self.spaceGrp.parent = self.offsetGrp
        self.parent = self.targetGrp

        self.groupHierarchy = [self.offsetGrp, self.spaceGrp, self.targetGrp]

        if scale:
            self.scale = scale
        if jnt:
            _jnt = mayanode.DagNode(jnt)
            for grp in self.groupHierarchy:
                grp.rotateOrder = _jnt.rotateOrder
            self.rotateOrder = _jnt.rotateOrder

            self.offsetGrp.matrix = _jnt.worldMatrix

        if shapeType == 'boundingBox':
            self.setupBoundingBox()

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
