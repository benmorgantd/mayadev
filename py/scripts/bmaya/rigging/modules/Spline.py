# a spine is a ribbon that has attachments at both ends to other joints
# (the pelvis drives the parent of the start, the chest drives the parent of the end)
# it just takes a start and end joint

import maya.cmds as cmds
import maya.OpenMaya as om

from bmaya.core import name

from bmaya.rigging.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.rigging.base import module


class Spline(module.Module):
    def __init__(self, startJoint=None, endJoint=None, name='Spline1', 
                 character=None, side='M', mirror=False, parent=None, setupTwist=True, controlAmount=3, 
                 stretchy=True, startTwistParent=None, shapeType='cube'):
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
        self.bindJoints = self.findHierarchyJoints(startJoint=self.startJoint,
                                                   endJoint=self.endJoint, 
                                                   shortestDistance=True)

        self.fkDriveJoints = self.createDriveJoints(label='FKDRIVER', constrain=False)
        self.ikDriveJoints = self.createDriveJoints(label='IKDRIVER', constrain=False)
        self.driveJoints = self.createDriveJoints(label='DRIVER', constrain=True)
        
        
        
        self.fkComponents = self.buildFkControls()
        self.ikComponents = self.buildIkControls()

        if self.setupTwist:
            self.setupAdvancedTwist()

        self.setupIkEndJoint()
        self.setupIkHierarchy()

        # add an attribute for blending
        cmds.addAttr(self.node, longName='FKIK', attributeType='float', dv=1, 
                     min=0, max=1, keyable=True)

        self.blendReverse = self.blendChains(self.fkDriveJoints, self.ikDriveJoints, self.driveJoints, self.node + '.FKIK')

        # connect blend control to visibility
        cmds.connectAttr(self.blendReverse, '{0}.v'.format(self.fkComponents[0].offsetGrp))
        
        for ctrl in self.ikComponents:
            cmds.connectAttr(self.node + '.FKIK', '{0}.v'.format(ctrl.offsetGrp))
        
        self.components += self.fkComponents
        self.components += self.ikComponents

    def buildFkControls(self):

        components = []

        for i in range(len(self.fkDriveJoints)):
            jnt = self.fkDriveJoints[i]

            ctrl = shapelib.Shape(name=name.findControlName(jnt, identifier='Fk'),
                                  shapeType=self.shapeType, jnt=jnt)

            components.append(ctrl)

            self.parentConstrain(ctrl.ctrl, jnt, maintainOffset=True)

            if i == 0:
                cmds.parent(ctrl.offsetGrp, self.componentsGrp)
            else:
                parentJoint = cmds.listRelatives(
                    jnt, parent=True, type='joint')[0]
                parentCtrl = cmds.listConnections(parentJoint + '.driveCtrl')

                if parentCtrl:
                    cmds.parent(ctrl.offsetGrp, parentCtrl[0])
                else:
                    cmds.parent(ctrl.offsetGrp, components[0].ctrl)

            cmds.addAttr(jnt, longName='driveCtrl', attributeType='message')
            cmds.addAttr(ctrl.ctrl, longName='driveJoint', attributeType='message')
            cmds.connectAttr(ctrl.ctrl + '.driveJoint', jnt + '.driveCtrl')

        return components

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

            ctrl = shapelib.Shape(name=name.findControlName(jnt, identifier='Ik'), shapeType=self.shapeType, jnt=jnt)
            
            cmds.parent(ctrl.offsetGrp, self.componentsGrp)
            cmds.parentConstraint(ctrl.ctrl, jnt, maintainOffset=True)
            
            if i == 0 and self.startTwistParent:
                cmds.parentConstraint(self.startTwistParent, ctrl.offsetGrp, maintainOffset=True)

            ikControls.append(ctrl)

        self.setupStretch()

        return ikControls

    def buildIkSpline(self):
        """Note that there will be some movement on the ikJoints after creating this. 
        Having the blend maintain offset will help.
        """

        jntLocs = [cmds.xform(jnt, q=1, t=1, ws=1) for jnt in self.ikDriveJoints]

        linearCurve = cmds.curve(degree=1, point=jntLocs)

        splineCurve = cmds.fitBspline(linearCurve, constructionHistory=False, tolerance=0.001,
                                      name='{0}_00_{1}_SPLINE'.format(self.name, self.side))[0]
                                      
        cmds.setAttr(splineCurve + '.inheritsTransform', False)
        
        cmds.delete(linearCurve)

        cmds.parent(splineCurve, self.componentsGrp)

        # the end effector for the splineIKHandle is one joint too early?

        splineIkHandle = cmds.ikHandle(name=self.name + '_splineIkHandle', 
                                       solver='ikSplineSolver', startJoint=self.ikDriveJoints[0], 
                                       endEffector=self.ikDriveJoints[-1], curve=splineCurve,
                                       createCurve=False)[0]
                                       
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
            cmds.setAttr(lengthMultiplier + '.input1', cmds.getAttr(jnt + '.translateX'))
            cmds.connectAttr(stretchFactor + '.output', lengthMultiplier + '.input2')
            
            cmds.connectAttr(lengthMultiplier + '.output', jnt + '.translateX')

    def buildSplineDriverJoints(self):
        
        # we could go on a variable here since this is essentially the number of
        # controls 

        splineDriverJoints = []

        # create a temporary curveInfo node to give us positional information
        # along our spline curve
        curveShape = cmds.listRelatives(self.splineCurve, shapes=True)[0]
        curveInfo = cmds.createNode("pointOnCurveInfo")
        cmds.connectAttr(curveShape + ".worldSpace[0]", curveInfo + ".inputCurve")
        cmds.setAttr(curveInfo + ".turnOnPercentage", True)

        # build a matrix from the curve into node
        temp4x4 = cmds.createNode('fourByFourMatrix')
        cmds.connectAttr(curveInfo + '.position.positionX', temp4x4 + '.in30')
        cmds.connectAttr(curveInfo + '.position.positionY', temp4x4 + '.in31')
        cmds.connectAttr(curveInfo + '.position.positionZ', temp4x4 + '.in32')

        # align the down axis (x) to the tangent of the curve
        cmds.connectAttr(curveInfo + '.normalizedTangent.normalizedTangentX', temp4x4 + '.in00')
        cmds.connectAttr(curveInfo + '.normalizedTangent.normalizedTangentY', temp4x4 + '.in01')
        cmds.connectAttr(curveInfo + '.normalizedTangent.normalizedTangentZ', temp4x4 + '.in02')

        for i in range(self.controlAmount):
            cmds.select(clear=True)
            # make a control at a percentage distance along the curve
            cmds.setAttr(curveInfo + ".parameter", i / float(self.controlAmount - 1))

            jnt = cmds.joint(name=name.findJointName(self.bindJoints[0], count=i, suffix='CURVEDRIVER'))
            cmds.setAttr(jnt + '.rotateOrder', 2)
            
            # use the forward vector of our start joint as the y axis value
            # default forward axis is y (make this a variable)
            startJointMatrix = cmds.getAttr(self.startJoint + '.worldMatrix[0]')
            forwardVector = om.MVector(*startJointMatrix[4:7])
            # we could make this a variable to (to be the average vector, a
            # specified vector, etc)

            U = om.MVector(*cmds.getAttr(curveInfo + '.normalizedTangent')[0])
            W = (U ^ forwardVector).normal()

            # like an up vector in an aim, the forward vector may not always be 
            # orthogonal to U (if the spline has any sort of curve to it)
            forwardVector = (W ^ U).normal()

            cmds.setAttr(temp4x4 + '.in10', forwardVector.x)
            cmds.setAttr(temp4x4 + '.in11', forwardVector.y)
            cmds.setAttr(temp4x4 + '.in12', forwardVector.z)

            cmds.setAttr(temp4x4 + '.in20', W.x)
            cmds.setAttr(temp4x4 + '.in21', W.y)
            cmds.setAttr(temp4x4 + '.in22', W.z)

            cmds.xform(jnt, matrix=cmds.getAttr(temp4x4 + '.output'))

            cmds.makeIdentity(jnt, apply=True)

            cmds.parent(jnt, self.componentsGrp)

            splineDriverJoints.append(jnt)

        cmds.delete(curveInfo, temp4x4)

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
        jnt = cmds.joint(name=name.findJointName(self.ikDriveJoints[-1], count=len(self.ikDriveJoints), suffix='IKDRIVER'))
        cmds.setAttr(jnt + '.rotateOrder', cmds.getAttr(self.ikDriveJoints[-1] + '.rotateOrder'))
        cmds.delete(cmds.parentConstraint(self.ikDriveJoints[-1], jnt, maintainOffset=False))
        
        cmds.parent(jnt, self.ikDriveJoints[-2])
        cmds.parentConstraint(self.ikComponents[-1], jnt, maintainOffset=True)

        # just replace the end joint with this joint so when we setup the blend
        # it just works
        self.ikDriveJoints[-1] = jnt

    def setupIkHierarchy(self):
        """Make a simple switch to make the ik hierarchy behave like an fk one"""

        cmds.addAttr(self.node, longName='hybridIk', attributeType='bool', keyable=True, defaultValue=False)
        
        for i in range(len(self.ikComponents) - 1):
            const = cmds.parentConstraint(self.ikComponents[i].ctrl, 
                                          self.ikComponents[i + 1].offsetGrp, 
                                          maintainOffset=True)[0]

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
                cmds.connectAttr(rev + '.outputX', 
                             '{0}.{1}'.format(const[0], cmds.parentConstraint(const[0], query=True, weightAliasList=True)[0]))