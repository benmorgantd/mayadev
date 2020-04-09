import maya.cmds as cmds 

from bmaya.rigging.modules import FkTwist
from bmaya.rigging.rigBuilder.base.decorators import wrapBuild
from bmaya.core import name, constants, mayanode


class NeckHead(FkTwist.FkTwist):

    def __init__(self, startJoint=None, endJoint=None, exclude=[], name='NeckHead1',
                 character=None, parent=None, shapeType='cube', mirror=False, side='L',
                 alignWorld=False, twistAxis='X', exponent=1):

        FkTwist.FkTwist.__init__(self, name=name, character=character, shapeType=shapeType, 
                                 mirror=mirror, side=side, alignWorld=alignWorld,
                                 startJoint=startJoint, endJoint=endJoint, exclude=exclude,
                                 exponent=exponent, twistAxis=twistAxis)

        self.modType = 'NeckHead'

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        self.buildNeckHead()

    def buildNeckHead(self):
        self.buildFkTwist()

        # add constraints for twist controls
        for i in range(1, len(self.components) - 1):
            twistCtrl = self.components[i]

            # wtAddMatrix = cmds.shadingNode('wtAddMatrix', asUtility=True, name=twistCtrl.ctrl + '_wtAddMatrix')
            
            # cmds.connectAttr(self.components[0].ctrl + '.worldMatrix[0]', wtAddMatrix + '.wtMatrix[0].matrixIn')
            # cmds.connectAttr(self.components[-1].ctrl + '.worldMatrix[0]', wtAddMatrix + '.wtMatrix[1].matrixIn')

            # startPoint = mayanode.Transform(self.components[0].ctrl)
            # endPoint = mayanode.Transform(self.components[-1].ctrl)
            # twistPoint = mayanode.Transform(twistCtrl.ctrl)

            # print twistCtrl.ctrl
            # print twistPoint.worldPosition.x, twistPoint.worldPosition.y, twistPoint.worldPosition.z

            # # get the distance between the start and end component
            # startEndDistance = (endPoint.worldPosition - startPoint.worldPosition).length()
            # startTwistDistance = (twistPoint.worldPosition - startPoint.worldPosition).length()
            
            # # get the percentage it is along that distance
            # distancePercent = startTwistDistance / float(startEndDistance)

            # cmds.setAttr(wtAddMatrix + '.wtMatrix[0].weightIn', distancePercent)
            # cmds.setAttr(wtAddMatrix + '.wtMatrix[1].weightIn', 1 - distancePercent)
            
            # # decompose and connect
            # decomp = cmds.createNode('decomposeMatrix', name=twistCtrl.ctrl + '_matrixDecomp')
            # cmds.connectAttr(wtAddMatrix + '.matrixSum', decomp + '.inputMatrix')
            # cmds.connectAttr(decomp + '.outputTranslate', twistCtrl.spaceGrp + '.translate')

            cmds.aimConstraint(self.components[-1].ctrl, twistCtrl.spaceGrp, 
                              aimVector=constants.UNIT_VECTORS[constants.DOWN_AXIS],
                              upVector=constants.UNIT_VECTORS[constants.UP_AXIS],
                              worldUpType='objectrotation', 
                              worldUpObject=self.components[0].ctrl,
                              worldUpVector=constants.UNIT_VECTORS[constants.UP_AXIS],
                              maintainOffset=True)