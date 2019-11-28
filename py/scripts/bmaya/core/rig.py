# subclass of asset


class Rig(object):
    def __init__(self, name, project, assetType='rig'):
        super(Rig, self).__init__(name=name, project=project, assetType=assetType)

    def initComponents(self):
        # initialize the component objects for the asset
        self.mesh = mesh.Mesh(self, 'mesh')
        self.skeleton = skeleton.Skeleton(self, 'skeleton')
        self.weights = weights.Weights(self, 'weights')
        self.cvs = cvs.Cvs(self, 'cvs')
        self.build = build.Build(self, 'build')
        self.animRig = animRig.AnimRig(self, 'animRig')

        self.components += [self.mesh, self.skeleton, self.weights, self.cvs, self.build, self.animRig]

    def initComponentFolders(self):
        """Creates the component folders for the asset"""

        for component in self.components:
            dirpath = os.path.dirname(component.fullPath)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

        print ">> Initialized component folders"

    def initComponentFiles(self):

        if not os.path.exists(self.mesh.fullPath):
            print ">> Creating mesh file."
            # mesh file is just a blank ma
            cmds.file(new=True, force=True)
            cmds.file(rename=self.mesh.fullPath)
            cmds.file(save=True, type="mayaAscii", force=True)
            self.versionFile(self.mesh.fullPath)
        else:
            print '>> A working mesh file already exists for ' + self.name

        if not os.path.exists(self.skeleton.fullPath):
            print ">> Creating skeleton file."
            # create a single joint for the default skeleton file
            cmds.file(new=True, force=True)
            cmds.joint(name="root_00_M_JNT")
            cmds.file(rename=self.skeleton.fullPath)
            cmds.file(save=True, type="mayaAscii", force=True)
            self.versionFile(self.skeleton.fullPath)
        else:
            print '>> A working skeleton file already exists for ' + self.name

        if not os.path.exists(self.cvs.fullPath):
            print ">> Creating cvs file."
            with open(self.cvs.fullPath, "w") as f:
                json.dump({}, f)
            self.versionFile(self.cvs.fullPath)
        else:
            print '>> A working cvs file already exists for ' + self.name

        if not os.path.exists(self.build.fullPath):
            print ">> Creating build file."
            # give it a LayoutRig template
            layoutRigPath = os.path.join(self.templatesPath, "LayoutRig.json")

            with open(layoutRigPath, "r") as f:
                layoutRigData = f.read()
            
            # write the contents to this asset's build file
            with open(self.build.fullPath, "w") as f:
                f.write(layoutRigData)

            self.versionFile(self.build.fullPath)