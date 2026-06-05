"""Purpose:
The Layout module is the first module in the rig hierarchy. It is responsible for importing the skeleton and mesh, 
and creating the main rig groups and sets. It also creates a stack of offset controls that can be used to position 
the rig in the scene before building the rest of the rig.
"""
import maya.cmds as cmds

from . import module
from .decorators import wrapBuild
from bmaya.maya.rigging.shapes import shapelib
from bmaya.core import constants


class Layout(module.Module):
    """Every rig must have a Layout module"""

    def __init__(self, character=None):
        super(Layout, self).__init__(modType='Layout', shapeType='pointedCircle', name='Layout', 
                                   character=character)

    @wrapBuild
    def build(self):

        # import only the data from the skeleton file's Layout namespace
        # to do this we'll first open the file and

        cmds.file(self.character.skeleton.fullPath, i=True,
                  applyTo=':', loadReferenceDepth='none')
        print('>>> Imported skeleton component <<<<')

        # import the mesh
        cmds.file(self.character.mesh.fullPath, i=True,
                  applyTo=':', loadReferenceDepth='none')
        print('>>> Imported mesh component <<<<')

        self.makeRigSets()
        self.makeRigGroups()
        self.makeCtrls()

    def makeRigSets(self):
        self.character.meshSet = cmds.sets([cmds.listRelatives(shp, parent=True)[0] for shp in cmds.ls(type='mesh')],
                                           name='MESH_set')

    def makeRigGroups(self):
        self.character.rigGrp = cmds.group(empty=True, name='RIG')

        self.character.connectToCharacter(self.character.rigGrp)

        try:
            self.character.meshGrp = cmds.group(self.character.meshSet, name='MESH')
        except RuntimeError:
            self.character.meshGrp = cmds.group(empty=True, name='MESH')

        self.character.skeletonGrp = cmds.group(constants.ROOT_JOINT, name='SKELETON')
        cmds.setAttr(self.character.skeletonGrp + '.visibility', 0)

        self.character.modulesGrp = cmds.group(empty=True, name='MODULES')

        cmds.parent(self.character.modulesGrp, self.character.skeletonGrp,
                    self.character.meshGrp, self.character.rigGrp)

        for grp in [self.character.modulesGrp, self.character.skeletonGrp, self.character.meshGrp, self.character.rigGrp]:
            for transform in ['translate', 'rotate', 'scale']:
                for axis in ['X', 'Y', 'Z']:
                    cmds.setAttr('{0}.{1}{2}'.format(grp, transform, axis), lock=True)

    def makeCtrls(self):
        # make a stack of offset controls
        for i in range(constants.COUNT_START, constants.COUNT_START + constants.LAYOUT_CONTROL_COUNT):
            if i > constants.COUNT_START:
                shp = shapelib.ControlCurve(name='layout_{0:02d}_{1}_{2}'.format(i, constants.SIDE_NAMES['middle'], constants.CTRL_SUFFIX), shapeType=self.shapeType, scale=(1 - ((i - 1) * 0.15)))
                cmds.parent(shp.offsetGrp, previous_ctrl.ctrl)
                previous_ctrl = shp
            else:
                shp = shapelib.ControlCurve(name='layout_{0:02d}_{1}_{2}'.format(i, constants.SIDE_NAMES['middle'], constants.CTRL_SUFFIX), shapeType=self.shapeType, scale=(1 - ((i - 1) * 0.15)))
                cmds.parent(shp.offsetGrp, self.modGrp)
                previous_ctrl = shp
           
            # TODO: add back in moveable pivot?
            #pivot = self.addMoveablePivot(shp)
            self.components.append(shp)
            #self.components.append(pivot)

        cmds.parent(self.components[0].offsetGrp, self.componentsGrp)
