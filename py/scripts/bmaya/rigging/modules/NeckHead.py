import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.rigging.modules import FkTwist
from bmaya.rigging.base.decorators import wrapBuild
from bmaya.core import name, constants, mayanode


class NeckHead(FkTwist.FkTwist):

    def __init__(self, startJoint=None, endJoint=None, exclude=[],
                 name='NeckHead1',
                 character=None, parent=None, shapeType='cube', mirror=False,
                 side='L',
                 alignWorld=False, twistAxis='X', exponent=1):
        FkTwist.FkTwist.__init__(self, name=name, character=character,
                                 shapeType=shapeType,
                                 mirror=mirror, side=side,
                                 alignWorld=alignWorld,
                                 startJoint=startJoint, endJoint=endJoint,
                                 exclude=exclude,
                                 exponent=exponent, twistAxis=twistAxis)

        self.modType = 'NeckHead'

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        self.buildNeckHead()

    def buildNeckHead(self):
        self.buildFkTwist()

        startPoint = mayanode.Transform(self.components[0].ctrl).worldPosition
        endPoint = mayanode.Transform(self.components[-1].ctrl).worldPosition
        startEndDistance = (endPoint - startPoint).length()

        # add constraints for twist controls
        for i in range(1, len(self.components) - 1):
            twistCtrl = self.components[i]

            twistPoint = om.MVector(
                *cmds.xform(twistCtrl.ctrl, query=True, translation=True,
                            worldSpace=True))

            # get the distance between the start and end component
            startTwistDistance = (twistPoint - startPoint).length()

            # get the percentage it is along that distance
            distancePercent = startTwistDistance / float(startEndDistance)

            pConstraint = cmds.pointConstraint(self.components[0].ctrl,
                                               self.components[-1].ctrl,
                                               twistCtrl.spaceGrp,
                                               maintainOffset=False)[0]

            weightList = cmds.pointConstraint(pConstraint, query=True,
                                              weightAliasList=True)
            cmds.setAttr('{0}.{1}'.format(pConstraint, weightList[0]),
                         1 - distancePercent)
            cmds.setAttr('{0}.{1}'.format(pConstraint, weightList[1]),
                         distancePercent)

            cmds.aimConstraint(self.components[-1].ctrl, twistCtrl.spaceGrp,
                               aimVector=constants.UNIT_VECTORS[
                                   constants.DOWN_AXIS],
                               upVector=constants.UNIT_VECTORS[
                                   constants.UP_AXIS],
                               worldUpType='objectrotation',
                               worldUpObject=self.components[0].ctrl,
                               worldUpVector=constants.UNIT_VECTORS[
                                   constants.UP_AXIS],
                               maintainOffset=True)
