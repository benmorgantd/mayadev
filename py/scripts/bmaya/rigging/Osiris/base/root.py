import maya.cmds as cmds

from . import module
from decorators import wrapBuild
from bmaya.rigging.shapes import shapelib
from bmaya.core import constants

reload(module)
reload(shapelib)
reload(constants)


class Root(module.Module):
    """Every rig must have a Root module"""

    def __init__(self, character=None):
        super(Root, self).__init__(modType='Root', shapeType='triangle', name='Root', 
                                   character=character)

    @wrapBuild
    def build(self):

        # import only the data from the skeleton file's root namespace
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
        self.character.masterSet = cmds.sets(empty=True, name='MASTER_set')

        self.character.skeletonSet = cmds.sets(
            cmds.ls('*_JNT', type='joint'), name='SKELETON_set')

        self.character.meshSet = cmds.sets([cmds.listRelatives(shp, parent=True)[0] for shp in cmds.ls(type='mesh')],
                                           name='MESH_set')

        cmds.sets([self.character.skeletonSet, self.character.meshSet],
                  include=self.character.masterSet)

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
        for i in range(1, 4):
            if i > 1:
                shp = shapelib.Shape('layout_{0}_M'.format(
                    str(i).zfill(2)), self.shapeType, scale=(1 - ((i - 1) * 0.15)))
                cmds.parent(shp.offsetGrp, self.components[i - 2].ctrl)
            else:
                shp = shapelib.Shape('layout_{0}_M'.format(
                    str(i).zfill(2)), self.shapeType)
                cmds.parent(shp.offsetGrp, self.modGrp)

            self.components.append(shp)

        cmds.parent(self.components[0].offsetGrp, self.componentsGrp)