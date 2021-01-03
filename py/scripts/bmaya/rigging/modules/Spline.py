# a spine is a ribbon that has attachments at both ends to other joints
# (the pelvis drives the parent of the start, the chest drives the parent of the end)
# it just takes a start and end joint

import maya.cmds as cmds

from bmaya.core import name, mathUtils, constants

from bmaya.rigging.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.rigging.base import module


class Spline(module.Module):
    def __init__(self, startJoint=None, endJoint=None, name='Spline1', character=None, side='M', mirror=False,
                 parent=None, setupTwist=True, controlAmount=3, stretchy=True, startTwistParent=None, shapeType='cube'):
        super(Spline, self).__init__(modType='Spline', name=name, character=character, mirror=mirror, side=side,
                                     shapeType=shapeType)

        self.startJoint = startJoint
        self.endJoint = endJoint
        self.setupTwist = setupTwist
        self.controlAmount = controlAmount
        self.stretchy = stretchy
        self.startTwistParent = startTwistParent

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):
        self.bindJoints = self.findHierarchyJoints(startJoint=self.startJoint, endJoint=self.endJoint,
                                                   shortestDistance=True)

        self.fkDriveJoints = self.createDriveJoints(label='FKDRIVER', constrain=False)
        self.ikDriveJoints = self.createDriveJoints(label='IKDRIVER', constrain=False)
        self.driveJoints = self.createDriveJoints(label='DRIVER', constrain=True)

        print(len(self.fkDriveJoints))

        self.fkComponents = self.buildFkControls()
        self.ikComponents = self.buildIkControls()

        if self.setupTwist:
            self.setupAdvancedTwist()

        self.setupIkEndJoint()
        self.setupIkHierarchy()

        # add an attribute for blending
        cmds.addAttr(self.node, longName='FKIK', attributeType='float', dv=1, min=0, max=1, keyable=True)

        self.blendReverse = self.blendChains(self.fkDriveJoints, self.ikDriveJoints, self.driveJoints,
                                             self.node + '.FKIK')

        # connect blend control to visibility
        cmds.connectAttr(self.blendReverse, '{0}.v'.format(self.fkComponents[0].offsetGrp))

        for ctrl in self.ikComponents:
            cmds.connectAttr(self.node + '.FKIK', '{0}.v'.format(ctrl.offsetGrp))

        self.components += self.fkComponents
        self.components += self.ikComponents

        print('finished with build!')

    def buildFkControls(self):

        _components = []

        for i in range(len(self.fkDriveJoints)):
            jnt = self.fkDriveJoints[i]
            print('got joint index')

            ctrl = shapelib.ControlCurve(name=name.findControlName(jnt, identifier='Fk'), shapeType=self.shapeType,
                                         jnt=jnt)
            print('made control')
            print(ctrl)

            # TODO there's something funky going on here with the following append statement...
            # and it's _just_ in this module.

            _components.append(ctrl)

            print('appended control')

            self.parentConstrain(ctrl.ctrl, jnt, maintainOffset=True)

            print('did constraint')

            if i == 0:
                cmds.parent(ctrl.offsetGrp, self.componentsGrp)
            else:
                parentJoint = cmds.listRelatives(jnt, parent=True, type='joint')[0]
                parentCtrl = cmds.listConnections(parentJoint + '.driveCtrl')

                if parentCtrl:
                    cmds.parent(ctrl.offsetGrp, parentCtrl[0])
                else:
                    cmds.parent(ctrl.offsetGrp, _components[0].ctrl)

            print('did parenting')

            cmds.addAttr(jnt, longName='driveCtrl', attributeType='message')
            cmds.addAttr(ctrl.ctrl, longName='driveJoint', attributeType='message')
            cmds.connectAttr(ctrl.ctrl + '.driveJoint', jnt + '.driveCtrl')
            print('made it to end of loop')

        return _components

    def buildIkControls(self):

        self.splineIkHandle, self.splineCurve = self.buildIkSpline()

        self.splineDriverJoints = self.buildSplineDriverJoints()

        cmds.hide(self.splineCurve, self.splineDriverJoints)

        # skin the driver joints to the curve
        cmds.skinCluster(self.splineDriverJoints, self.splineCurve, maximumInfluences=4)

        ikControls = []

        # build the controls
        for i in range(len(self.splineDriverJoints)):
            jnt = self.splineDriverJoints[i]

            ctrl = shapelib.ControlCurve(name=name.findControlName(jnt, identifier='Ik'), shapeType=self.shapeType,
                jnt=jnt)

            cmds.parent(ctrl.offsetGrp, self.componentsGrp)
            self.parentConstrain(ctrl.ctrl, jnt, maintainOffset=True)

            if i == 0 and self.startTwistParent:
                self.parentConstrain(self.startTwistParent, ctrl.offsetGrp, maintainOffset=True)

            ikControls.append(ctrl)

        self.setupStretch()

        return ikControls

    def buildIkSpline(self):
        """Note that there will be some movement on the ikJoints after creating this. 
        Having the blend maintain offset will help.
        """

        jntLocs = [cmds.xform(jnt, q=1, t=1, ws=1) for jnt in self.ikDriveJoints]

        splineCurve = mathUtils.fitCurveToPoints(jntLocs, name=self.name + '_spline')
        cmds.setAttr(splineCurve + '.inheritsTransform', False)

        # the end effector for the splineIKHandle is one joint too early?

        splineIkHandle = \
        cmds.ikHandle(name=self.name + '_splineIkHandle', solver='ikSplineSolver', startJoint=self.ikDriveJoints[0],
                      endEffector=self.ikDriveJoints[-1], curve=splineCurve, createCurve=False)[0]

        if constants.SPINE_UP_AXIS == 'Y':
            # special attribute values for making a y up spine
            # +y forward axis
            cmds.setAttr(splineIkHandle + '.dForwardAxis', 2)
            # +z up axis
            cmds.setAttr(splineIkHandle + '.dWorldUpAxis', 3)
            cmds.setAttr(splineIkHandle + '.dWorldUpVector', 0, 0, 1)
            cmds.setAttr(splineIkHandle + '.dWorldUpVectorEnd', 0, 0, 1)

        cmds.parent(splineCurve, splineIkHandle, self.componentsGrp)

        return [splineIkHandle, splineCurve]

    def setupStretch(self):

        # create a curveInfo node to track the current arc length of the curve
        curveShape = cmds.listRelatives(self.splineCurve, shapes=True)[0]
        curveInfo = cmds.createNode("curveInfo")
        cmds.connectAttr(curveShape + ".worldSpace[0]", curveInfo + ".inputCurve")

        # create a multiply divide node to track the stretch factor
        stretchFactor = cmds.shadingNode('multDoubleLinear', asUtility=True, name=self.name + '_stretchFactor')
        cmds.connectAttr(curveInfo + '.arcLength', stretchFactor + '.input1')
        cmds.setAttr(stretchFactor + '.input2', 1 / float(cmds.getAttr(curveInfo + '.arcLength')))

        for i in range(1, len(self.ikDriveJoints)):
            jnt = self.ikDriveJoints[i]

            # create a mdl for this joint's original length (default down axis
            # is x)
            lengthMultiplier = cmds.shadingNode('multDoubleLinear', asUtility=True, name=jnt + '_stretchMultiplier')
            cmds.setAttr(lengthMultiplier + '.input1',
                         cmds.getAttr('{0}.translate{1}'.format(jnt, constants.SPINE_UP_AXIS)))
            cmds.connectAttr(stretchFactor + '.output', lengthMultiplier + '.input2')

            cmds.connectAttr(lengthMultiplier + '.output', '{0}.translate{1}'.format(jnt, constants.SPINE_UP_AXIS))

    def buildSplineDriverJoints(self):

        # we could go on a variable here since this is essentially the number of
        # controls 

        splineDriverJoints = []

        # use the forward vector of our start joint as the y axis value
        # startJointMatrix = cmds.getAttr(self.startJoint + '.worldMatrix[0]')
        # forwardVector = om.MVector(*startJointMatrix[4:7])

        for i in range(self.controlAmount):
            cmds.select(clear=True)

            # make a control at a percentage distance along the curve
            matrix = mathUtils.getMatrixAlongCurve(self.splineCurve, i / float(self.controlAmount - 1),
                                                   downAxis=constants.SPINE_UP_AXIS)

            jnt = cmds.joint(name=name.findJointName(self.bindJoints[0], count=i, suffix='CURVEDRIVER'))

            if constants.SPINE_UP_AXIS == 'X':
                cmds.setAttr(jnt + '.rotateOrder', 2)
            else:
                cmds.setAttr(jnt + '.rotateOrder', 3)

            cmds.xform(jnt, matrix=matrix, worldSpace=True)

            cmds.makeIdentity(jnt, apply=True)

            cmds.parent(jnt, self.componentsGrp)

            splineDriverJoints.append(jnt)

        return splineDriverJoints

    def setupAdvancedTwist(self):

        cmds.setAttr(self.splineIkHandle + '.dTwistControlEnable', True)
        # set world up to Object Rotation Up (Start, End)
        cmds.setAttr(self.splineIkHandle + '.dWorldUpType', 4)

        cmds.connectAttr(self.ikComponents[0].ctrl + '.worldMatrix[0]', self.splineIkHandle + '.dWorldUpMatrix')
        cmds.connectAttr(self.ikComponents[-1].ctrl + '.worldMatrix[0]', self.splineIkHandle + '.dWorldUpMatrixEnd')

    def setupIkEndJoint(self):
        """Create a joint at the end of the ik chain that serves as more of an fk-style control"""

        cmds.select(clear=True)
        jnt = cmds.joint(
            name=name.findJointName(self.ikDriveJoints[-1], count=len(self.ikDriveJoints), suffix='IKDRIVER'))
        cmds.setAttr(jnt + '.rotateOrder', cmds.getAttr(self.ikDriveJoints[-1] + '.rotateOrder'))
        mathUtils.matchTransforms(self.ikDriveJoints[-1], jnt)

        cmds.parent(jnt, self.ikDriveJoints[-2])
        self.parentConstrain(self.ikComponents[-1], jnt, maintainOffset=True)

        # just replace the end joint with this joint so when we setup the blend
        # it just works
        self.ikDriveJoints[-1] = jnt

    def setupIkHierarchy(self):
        """Make a simple switch to make the ik hierarchy behave like an fk one"""

        cmds.addAttr(self.node, longName='hybridIk', attributeType='bool', keyable=True, defaultValue=False)

        for i in range(len(self.ikComponents) - 1):
            const = self.parentConstrain(self.ikComponents[i].ctrl, self.ikComponents[i + 1].offsetGrp)

            cmds.connectAttr(self.node + '.hybridIk',
                             '{0}.{1}'.format(const, cmds.parentConstraint(const, query=True, weightAliasList=True)[0]))

        # switch off the base ik's constraint with this if there is one 
        if self.startTwistParent:
            rev = cmds.createNode('reverse', name=self.name + '_ikHybridReverse')
            cmds.connectAttr(self.node + '.hybridIk', rev + '.inputX')
            # get the parent constraint on the first ik component's offset group
            const = cmds.ls(cmds.listRelatives(self.ikComponents[0].offsetGrp, children=True), type='parentConstraint')

            if const:
                # switch it off when we go into hybridIk mode
                cmds.connectAttr(rev + '.outputX', '{0}.{1}'.format(const[0],
                                                                    cmds.parentConstraint(const[0], query=True,
                                                                        weightAliasList=True)[0]))
