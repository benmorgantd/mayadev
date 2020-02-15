import maya.cmds as cmds

from bmaya.rigging.Osiris.base import module
from bmaya.rigging.Osiris.base.decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import mathUtils


class Ribbon(module.Module):

    def __init__(self, startJoint=None, endJoint=None, controlAmount=3, jointAmount=4, 
                 name='Ribbon1', character=None, parent=None, side='L', mirror=False,
                 addDeformers=True):
        super(Ribbon, self).__init__(modType='Ribbon', name=name, character=character, 
                                     mirror=mirror, side=side)

        self.parent = parent
        self.startJoint = startJoint
        self.endJoint = endJoint

        self.controlAmount = controlAmount
        self.jointAmount = jointAmount
        self.addDeformers = addDeformers

        if self.controlAmount < 2:
            raise ValueError('Ribbons must have at least 2 controls')
        if self.jointAmount < 2:
            raise ValueError('Ribbons must have at least 2 bind joints')

        self.contract = [self.startJoint, self.endJoint]

    @wrapBuild
    def build(self):

        self.skinnedPlane = self.buildSkinnedPlane(self.startJoint, self.endJoint)
        if self.addDeformers:
            self.deformerPlane = self.buildDeformerPlane(self.startJoint, self.endJoint, self.skinnedPlane)
        self.followJoints = self.makeFollowJoints(self.skinnedPlane, self.startJoint)
        self.driveJoints = self.makeDriveJoints(self.skinnedPlane, self.startJoint)
        self.bindJoints = self.makeBindJoints(self.startJoint, self.followJoints)
        self.followControls = self.makeFollowJointControls(self.bindJoints, self.followJoints)
        self.skinDriverJointsToPlane(self.driveJoints, self.skinnedPlane)
        self.driveControls = self.makeDriverControls(self.startJoint, self.driveJoints)
        self.addVisibilitySwitches()

    def buildRibbon(self, startJoint, endJoint, name, twist=True, sine=False, identifier=''):
        self.name = name
        skinnedPlane = self.buildSkinnedPlane(startJoint, endJoint)
        if self.addDeformers:
            deformerPlane = self.buildDeformerPlane(startJoint, endJoint, skinnedPlane, twist=twist,
                                                    sine=sine, identifier=identifier)
        followJoints = self.makeFollowJoints(skinnedPlane, startJoint, identifier)
        driveJoints = self.makeDriveJoints(skinnedPlane, startJoint, identifier)
        bindJoints = self.makeBindJoints(startJoint, followJoints, identifier)
        followControls = self.makeFollowJointControls(bindJoints, followJoints)
        self.skinDriverJointsToPlane(driveJoints, skinnedPlane)
        driveControls = self.makeDriverControls(startJoint, driveJoints)
        self.addVisibilitySwitches()

        attrDict = {'skinnedPlane':skinnedPlane, 'followJoints':followJoints, 'followControls':followControls,
                    'bindJoints':bindJoints, 'driveControls':driveControls}
        return attrDict

    def buildSkinnedPlane(self, startJoint, endJoint):
        # we want the number of U patches to be the same as the joint amount. 
        # This makes each joint sit in the center of a patch, which gives good tangents
        skinnedPlane = cmds.nurbsPlane(name='{0}_{1}_skinnedPlane'.format(self.name, self.side),
                                pivot=(0,0,0), axis=(0,1,0), width=1, lengthRatio=1,
                                patchesU=self.jointAmount, patchesV=1, degree=1,
                                constructionHistory=False)[0]

        cmds.parent(skinnedPlane, self.driverGrp)

        # align plane
        cmds.delete(cmds.pointConstraint(startJoint, endJoint, skinnedPlane, mo=0))
        cmds.delete(cmds.aimConstraint(endJoint, skinnedPlane, 
                    aimVector=[1,0,0], upVector=[0,1,0], worldUpType='None'))
        
        cmds.xform(skinnedPlane, scale=[mathUtils.getDistance(startJoint,endJoint), 1, 1])

        cmds.makeIdentity(skinnedPlane, apply=True, t=1, r=1, s=1, pn=1)

        return skinnedPlane

    def buildDeformerPlane(self, startJoint, endJoint, skinnedPlane, twist=True, sine=True, identifier=''):
        deformerPlane = cmds.duplicate(skinnedPlane,
                                       name='{0}{1}_{2}_deformerPlane'.format(self.name, identifier, self.side))[0]

        cmds.makeIdentity(deformerPlane, apply=True, t=1, r=1, s=1, pn=1)

        if twist:

            # TWIST deformer
            cmds.select(deformerPlane)
            twistDeformer, twistHandle = cmds.nonLinear(type='twist', name=deformerPlane + '_twistDef')

            cmds.parent(twistHandle, self.driverGrp)

            cmds.delete(cmds.aimConstraint(startJoint, twistHandle, mo=0,
                        aimVector=[0,-1,0], upVector=[1,0,0], worldUpType='None'))

            # module attribute names won't be unique if we're making multiple ribbons on a parent module
            attrNames = {'twistStart': identifier + 'TwistStart',
                        'twistEnd': identifier + 'TwistEnd',
                        'twistStartOffset': identifier + 'TwistStartOffset',
                        'twistEndOffset': identifier + 'TwistEndOffset'}

            cmds.addAttr(self.node, longName=attrNames['twistStart'], attributeType='float', keyable=True)
            cmds.addAttr(self.node, longName=attrNames['twistEnd'], attributeType='float', keyable=True)

            # full chain twist with offsets (for arms, forearms)

            cmds.addAttr(self.node, longName=attrNames['twistStartOffset'], attributeType='float', keyable=False)
            cmds.addAttr(self.node, longName=attrNames['twistEndOffset'], attributeType='float', keyable=False)

            startPma = cmds.shadingNode('addDoubleLinear', asUtility=True, name=self.node + '_twistStartADL')
            cmds.connectAttr(self.node + '.' + attrNames['twistStart'], startPma + '.input1')
            cmds.connectAttr(self.node + '.' + attrNames['twistStartOffset'], startPma + '.input2')

            endPma = cmds.shadingNode('addDoubleLinear', asUtility=True, name=self.node + '_twistEndADL')
            cmds.connectAttr(self.node + '.' + attrNames['twistEnd'], endPma + '.input1')
            cmds.connectAttr(self.node + '.' + attrNames['twistEndOffset'], endPma + '.input2')

            cmds.connectAttr(startPma + '.output', twistDeformer + '.startAngle')
            cmds.connectAttr(endPma + '.output', twistDeformer + '.endAngle')

            self.messageConnect(self.node, twistDeformer, (identifier + 'TwistDeformer'), 'module')

        if sine:
            # SINE deformer
            cmds.select(deformerPlane)

            sineDeformer, sineHandle = cmds.nonLinear(type='sine', name=deformerPlane + '_sineDef')

            sineHandleGrp = cmds.group(empty=True, name=sineHandle + '_grp')
            cmds.delete(cmds.parentConstraint(sineHandle, sineHandleGrp, mo=0))
            cmds.parent(sineHandleGrp, self.driverGrp)
            cmds.parent(sineHandle, sineHandleGrp)
            cmds.xform(sineHandle, scale=(1,1,1), absolute=True)
            dist = mathUtils.getDistance(startJoint, endJoint)
            cmds.xform(sineHandleGrp, scale=[(dist/2.0), (dist/2.0), (dist/2.0)])
            # this rotation assumes an X down, Y up joint orientation
            cmds.xform(sineHandleGrp, rotation=(-90,0,90), r=1, os=1)

            cmds.addAttr(self.node, longName='sineAmplitude', attributeType='float', keyable=True)
            cmds.addAttr(self.node, longName='sineWavelength', attributeType='float', dv=1.0, keyable=True)
            cmds.addAttr(self.node, longName='sineOffset', attributeType='float', keyable=True)
            cmds.addAttr(self.node, longName='sineSlide', attributeType='float', keyable=True)
            cmds.addAttr(self.node, longName='sineDropoff', attributeType='float', keyable=True, min=0, max=1)

            cmds.connectAttr(self.node + '.sineAmplitude', sineDeformer + '.amplitude')
            cmds.connectAttr(self.node + '.sineWavelength', sineDeformer + '.wavelength')
            cmds.connectAttr(self.node + '.sineOffset', sineDeformer + '.offset')
            cmds.connectAttr(self.node + '.sineDropoff', sineDeformer + '.dropoff')
            cmds.connectAttr(self.node + '.sineSlide', sineHandle + '.translateY')

        cmds.blendShape(deformerPlane, skinnedPlane, weight=[(0,1)])

        return deformerPlane

    def makeFollowJoints(self, skinnedPlane, startJoint, identifier=''):

        followJoints = []
        self.followJointGrp = cmds.group(empty=True, name=self.name + identifier + '_followJoints')
        cmds.parent(self.followJointGrp, self.componentsGrp)
        cmds.hide(self.followJointGrp)

        # the bind joints follow the ribbon, which is driven the drivers

        for i in range(self.jointAmount):
            cmds.select(cl=1)

            joint = cmds.joint(name = self.findJointName(startJoint, identifier=identifier, count=i, suffix='FOLLOW'))
            # we actually want the follow joints to be xyz rotate order
            cmds.setAttr(joint + '.rotateOrder', 0)

            infoNode = cmds.createNode("pointOnSurfaceInfo", name=joint + "_POINTONSURFACE")
            cmds.connectAttr("{0}.worldSpace[0]".format(skinnedPlane), infoNode + ".inputSurface")
            cmds.setAttr(infoNode + ".turnOnPercentage", 1)

            cmds.setAttr(infoNode + ".parameterV", 0.5)

            if i != 0:
                cmds.setAttr(infoNode + ".parameterU", (1 / (float(self.jointAmount - 1)) * i))
            else:
                cmds.setAttr(infoNode + ".parameterU", 0)

            # make a matrix rivot
            matrix4x4 = cmds.shadingNode("fourByFourMatrix", name=joint + "_MAT4X4", asUtility=True)
            infoAttrs = ["normalizedNormal", "normalizedTangentU", "normalizedTangentV", "position"]
            axis = ["X", "Y", "Z"]

            for j in range(4):
                for k in range(3):
                    cmds.connectAttr("{0}.{1}{2}".format(infoNode, infoAttrs[j], axis[k]), "{0}.in{1}{2}".format(matrix4x4, j, k))

            # multiply the result of that matrix by the joint's parent inverse matrix.
            # this makes the joint follow the ribbon in world space
            multMatrix = cmds.shadingNode('multMatrix', asUtility=True, name=joint + '_MULTMATRIX')
            cmds.connectAttr(matrix4x4 + '.output', multMatrix + '.matrixIn[0]')
            cmds.connectAttr(joint + '.parentInverseMatrix[0]', multMatrix + '.matrixIn[1]')

            decompMatrix = cmds.createNode("decomposeMatrix", name=joint + "_MATDECOMP")
            cmds.connectAttr(multMatrix + ".matrixSum", decompMatrix + ".inputMatrix")
            cmds.connectAttr(decompMatrix + ".outputTranslate", joint + ".translate")
            cmds.connectAttr(decompMatrix + ".outputRotate", joint + ".rotate")

            cmds.parent(joint, self.followJointGrp)

            followJoints.append(joint)

        return followJoints

    def makeDriveJoints(self, skinnedPlane, startJoint, identifier=''):

        driveJoints = []
        driverJointsGrp = cmds.group(empty=True, name=self.name + "_driverJoints")

        for i in range(self.controlAmount):
            cmds.select(cl=1)

            joint = cmds.joint(name=self.findJointName(startJoint, identifier=identifier, count=i, suffix='DRIVER'))
            cmds.setAttr(joint + '.rotateOrder', 4)

            infoNode = cmds.createNode("pointOnSurfaceInfo", name=joint + "_POINTONSURFACE")
            cmds.connectAttr("{0}.worldSpace[0]".format(skinnedPlane), infoNode + ".inputSurface")
            cmds.setAttr(infoNode + ".turnOnPercentage", 1)

            cmds.setAttr(infoNode + ".parameterV", 0.5)

            if i != 0:
                cmds.setAttr(infoNode + ".parameterU", (1 / (float(self.controlAmount - 1)) * i))
            else:
                cmds.setAttr(infoNode + ".parameterU", 0)

            # make a matrix rivot
            matrix4x4 = cmds.shadingNode("fourByFourMatrix", name=joint + "_MAT4X4", asUtility=True)
            infoAttrs = ["normalizedNormal", "normalizedTangentU", "normalizedTangentV", "position"]
            axis = ["X", "Y", "Z"]

            for j in range(4):
                for k in range(3):
                    cmds.connectAttr("{0}.{1}{2}".format(infoNode, infoAttrs[j], axis[k]), "{0}.in{1}{2}".format(matrix4x4, j, k))

            decompMatrix = cmds.createNode("decomposeMatrix", name=joint + "_MATDECOMP")
            cmds.connectAttr(matrix4x4 + ".output", decompMatrix + ".inputMatrix")
            
            # make orient and sdk groups
            jointPosition = cmds.xform(joint, query=True, translation=True, worldSpace=True)

            orientGrp = cmds.group(empty=True, name=joint + "_grp")
            sdkGrp = cmds.group(empty=True, name=joint + "_sdk")

            cmds.delete(cmds.parentConstraint(joint, orientGrp, mo=0))
            cmds.delete(cmds.parentConstraint(joint, orientGrp, mo=0))

            cmds.parent(joint, sdkGrp)
            cmds.parent(sdkGrp, orientGrp)
            cmds.parent(orientGrp, driverJointsGrp)

            axis = ['X', 'Y', 'Z']

            for z in range(3):
                cmds.connectAttr(decompMatrix + ".outputTranslate" + axis[z], orientGrp + ".translate" + axis[z])
                cmds.connectAttr(decompMatrix + ".outputRotate" + axis[z], orientGrp + ".rotate" + axis[z])

                cmds.disconnectAttr(decompMatrix + ".outputTranslate" + axis[z], orientGrp + ".translate" + axis[z])
                cmds.disconnectAttr(decompMatrix + ".outputRotate" + axis[z], orientGrp + ".rotate" + axis[z])


            driveJoints.append(joint)

            cmds.delete(decompMatrix, matrix4x4, infoNode)

        cmds.parent(driverJointsGrp, self.driverGrp)

        # turn off inherit transform on driver group to get rid of double xforms
        cmds.setAttr(self.driverGrp + '.inheritsTransform', 0)

        return driveJoints

    def makeBindJoints(self, parentJoint, followJoints, identifier=''):
        bindJoints = []
        
        for i in range(len(followJoints)):
            followJnt = followJoints[i]

            if identifier:
                bindJnt = cmds.joint(name=self.findJointName(parentJoint, identifier=identifier, count=i, suffix='JNT'))
            else:
                bindJnt = cmds.joint(name='{0}_{1}_{2}_JNT'.format(self.name, str(i).zfill(2), self.side))
            cmds.setAttr(bindJnt + '.rotateOrder', 0)

            cmds.delete(cmds.parentConstraint(followJnt, bindJnt, mo=0))
            cmds.makeIdentity(bindJnt, apply=True, t=1,r=1,s=1,pn=1)

            self.messageConnect(followJnt, bindJnt, 'bindJoint', 'driveJoint')

            cmds.parent(bindJnt, parentJoint)

            bindJoints.append(bindJnt)

        return bindJoints

    def makeFollowJointControls(self, bindJoints, followJoints):

        followJointControls = []

        self.followControlGrp = cmds.group(empty=True, name=self.name + '_followControls')
        cmds.parent(self.followControlGrp, self.componentsGrp)

        for i in range(len(followJoints)):
            ctrl = shapelib.Shape(name=self.findControlName(followJoints[i], identifier='Follow'), 
                                  shapeType='square', jnt=followJoints[i], scale=1.15)

            cmds.parent(ctrl.offsetGrp, self.followControlGrp)

            self.parentConstrain(followJoints[i], ctrl.offsetGrp, maintainOffset=True)

            self.parentConstrain(ctrl.ctrl, bindJoints[i], maintainOffset=True)

            self.components.append(ctrl)

            followJointControls.append(ctrl)

        return followJointControls
        
    def skinDriverJointsToPlane(self, driveJoints, skinnedPlane):

        cmds.select(driveJoints)
        cmds.select(skinnedPlane, add=True)

        cstr = cmds.skinCluster(toSelectedBones=True, skinMethod=0, dropoffRate=3.0)[0]

        cmds.select(skinnedPlane)

        cmds.skinPercent(cstr, pruneWeights=0.05)

    def makeDriverControls(self, startJoint, driveJoints):

        driverControls = []

        driverControlGrp = cmds.group(empty=True, name=self.name + '_driverControls')
        cmds.parent(driverControlGrp, self.componentsGrp)

        for driveJnt in driveJoints:
            ctrl = shapelib.Shape(name=self.findControlName(driveJnt, identifier='Driver'), shapeType='cube', jnt=driveJnt)

            cmds.parent(ctrl.offsetGrp, self.componentsGrp)

            self.parentConstrain(ctrl.ctrl, driveJnt + '_grp', maintainOffset=True)

            cmds.parent(ctrl.offsetGrp, driverControlGrp)

            self.components.append(ctrl)

            driverControls.append(ctrl)

        cmds.parentConstraint(startJoint, driverControlGrp, mo=1)

        return driverControls

    def addVisibilitySwitches(self):
        if 'showFollowControls' not in cmds.listAttr(self.node):
            cmds.addAttr(self.node, longName='showFollowControls', attributeType='bool', keyable=True)

        cmds.connectAttr(self.node + '.showFollowControls', self.followControlGrp + '.v')
