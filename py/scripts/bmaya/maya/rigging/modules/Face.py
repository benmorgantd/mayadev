"""Facial rig setup"""

import maya.cmds as cmds

from bmaya.maya.rigging.base import module
from bmaya.maya.rigging.base.decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.maya.util import nameUtils

from . import FkChain


class Face(module.Module):

    def __init__(self, character=None, name='face', parent=None,
                 upperHead=None, middleHead=None, lowerHead=None,
                 jaw=None, eyeballs=[], eyelidBase=None, eyebrowBase=None,
                 drivers=[]):
        module.Module.__init__(self, character=character, name=name,
                               modType='Face', parent=parent, side='M')

        self.upperHead = upperHead
        self.middleHead = middleHead
        self.lowerHead = lowerHead
        self.jaw = jaw
        self.eyeballs = eyeballs
        self.eyelidBase = eyelidBase
        self.eyebrowBase = eyebrowBase
        self.drivers = drivers

        self.contract = [self.character.facePoses,
                         self.upperHead,
                         self.middleHead,
                         self.lowerHead,
                         self.jaw,
                         self.eyeballs,
                         self.eyelidBase,
                         self.eyebrowBase,
                         self.drivers]

        # # ----- Init Regions ------- #
        # # Upper Head
        # FkChain.FkChain.__init__(self,
        #                          startJoint=self.upperHead,
        #                          name=self.name + '_upperHead',
        #                          character=self.character,
        #                          exclude=self.eyebrowBases)
        #
        # # Middle Head
        # FkChain.FkChain.__init__(self,
        #                          startJoint=self.middleHead,
        #                          name=self.name + '_middleHead',
        #                          character=self.character,
        #                          exclude=self.eyeballs + self.eyebrowBases)
        #
        # # Lower Head
        # FkChain.FkChain.__init__(self,
        #                          startJoint=self.middleHead,
        #                          name=self.name + '_lowerHead',
        #                          character=self.character,
        #                          exclude=[self.jaw])

    @wrapBuild
    def build(self):
        '''
        The "Face" module could do the work of building the different FKHierarchy
        modules sort of like how the Leg builds the Foot module as well.

        Its contract could be vague:
        - upperHead
        - middleHead
        - lowerHead
        - jaw
        - eyes
        - eyebrows
        - all drivers
        - facePoses component (json file)

        If it knows the different parts, it can make the different fkHierarchy
        modules needed to build the controls while also knowing which joint
        does what job.

        It knowing the different major parts of the head will also allow us to
        designate specific control shapes.

        It knowing which joints are drivers will allow us to translate data from
        the facePoses json file to sdk/wtAddMatrix drivers on the face rig
        - create the poses on the fk rig (will need to have drivers disconnected)
        - save that component with the manager
           - that writes the driver/driven relationships to a json file
        - read that data during buildtime
           - each frame, check if a driver has a transform. If it does,
             translate that data to an sdk where the control is the driver


        '''

        # Gather the hierarchy joints for each region, create their drive joints,
        # and build the fk controls

        self.upperHeadBindJoints, \
        self.upperHeadDriveJoints, \
        self.upperHeadControls = self.buildFaceFkHierarchy(
                startJoint=self.upperHead,
                exclude=[self.eyebrowBase])

        self.middleHeadBindJoints, \
        self.middleHeadDriveJoints, \
        self.middleHeadControls = self.buildFaceFkHierarchy(
                startJoint=self.middleHead,
                exclude=[self.eyelidBase] + self.eyeballs)

        self.lowerHeadBindJoints, \
        self.lowerHeadDriveJoints, \
        self.lowerHeadControls = self.buildFaceFkHierarchy(
                startJoint=self.lowerHead,
                exclude=self.jaw)

        self.eyebrowBindJoints, \
        self.eyebrowDriveJoints, \
        self.eyebrowControls = self.buildFaceFkHierarchy(
                startJoint=self.eyebrowBase,
                exclude=[])

        self.parentConstrain(self.upperHeadControls[0],
                             self.eyebrowControls[0],
                             maintainOffset=True)

        self.eyelidBindJoints, \
        self.eyelidDriveJoints, \
        self.eyelidControls = self.buildFaceFkHierarchy(
                startJoint=self.eyelidBase,
                exclude=[])

        self.parentConstrain(self.middleHeadControls[0],
                             self.eyelidControls[0],
                             maintainOffset=True)

        self.jawBindJoints, \
        self.jawDriveJoints, \
        self.jawControls = self.buildFaceFkHierarchy(
                startJoint=self.jaw,
                exclude=[])

        self.parentConstrain(self.lowerHeadControls[0],
                             self.jawControls[0],
                             maintainOffset=True)

    def buildFaceFkHierarchy(self, startJoint, exclude=[]):
        bindJoints = self.findHierarchyJoints(startJoint=startJoint,
                                              exclude=exclude,
                                              shortestDistance=False)

        self.bindJoints += bindJoints

        driveJoints = []

        for jnt in bindJoints:
            driveJoints.append(self.createDriveJoint(jnt))

        self.driveJoints += driveJoints

        controls = self.buildFkControls(driveJoints=driveJoints)

        self.components += controls

        return bindJoints, driveJoints, controls
