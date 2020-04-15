import maya.cmds as cmds

from . import module
from decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import constants, name


class Layout(module.Module):
    """Every rig must have a Layout module"""

    def __init__(self, character=None):
        super(Layout, self).__init__(modType='Layout', shapeType='triangle', name='Layout', 
                                   character=character)

    @wrapBuild
    def build(self):

        # import only the data from the skeleton file's Layout namespace
        # to do this we'll first open the file and

        cmds.file(self.character.skeleton.fullPath, i=True,
                  applyTo=':', loadReferenceDepth='none')
        print '>>> Imported skeleton component <<<<'

        # import the mesh
        cmds.file(self.character.mesh.fullPath, i=True,
                  applyTo=':', loadReferenceDepth='none')
        print '>>> Imported mesh component <<<<'

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
            self.character.meshGrp = cmds.group(
                self.character.meshSet, name='MESH')
        except RuntimeError:
            self.character.meshGrp = cmds.group(empty=True, name='MESH')

        self.character.skeletonGrp = cmds.group(constants.ROOT_JOINT, name='SKELETON')
        cmds.setAttr(self.character.skeletonGrp + '.visibility', 0)

        self.character.modulesGrp = cmds.group(empty=True, name='MODULES')

        cmds.parent(self.character.modulesGrp, self.character.skeletonGrp,
                    self.character.meshGrp, self.character.rigGrp)

        self.lockTransforms([self.character.modulesGrp, self.character.skeletonGrp,
                             self.character.meshGrp, self.character.rigGrp], 
                             attrs=['translate', 'rotate', 'scale'])

    def makeCtrls(self):
        # make a stack of offset controls
        for i in range(constants.COUNT_START, 3):
            if i > constants.COUNT_START:
                shp = shapelib.Shape(name='layout_{0:02d}_{1}_{2}'.format(i, constants.SIDE_NAMES['middle'], constants.CTRL_SUFFIX),shapeType=self.shapeType, scale=(1 - ((i - 1) * 0.15)))
                cmds.parent(shp.offsetGrp, self.components[i - 1].ctrl)
            else:
                shp = shapelib.Shape(name='layout_{0:02d}_{1}_{2}'.format(i, constants.SIDE_NAMES['middle'], constants.CTRL_SUFFIX),shapeType=self.shapeType, scale=(1 - ((i - 1) * 0.15)))
                cmds.parent(shp.offsetGrp, self.modGrp)

            self.components.append(shp)

        cmds.parent(self.components[0].offsetGrp, self.componentsGrp)