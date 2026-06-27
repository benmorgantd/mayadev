"""Purpose:
The Rig class is the main class for building a rig. It contains the main logic for building the rig,
as well as the main attributes that are used by the modules to build the rig, such as the list of modules,
the build data, etc. It also contains methods for building the layout rig, skinning the rig,
coloring controls, etc.
The Rig class is responsible for orchestrating the entire rigging process,
and is the main class that is instantiated when building a rig.
"""

import json
import os
import time

import maya.cmds as cmds

from bmaya.maya.asset.asset import Asset
from bmaya.maya.asset.components import (
    animRig,
    build,
    cvs,
    weights,
    build,
    mesh,
    skeleton,
    postops,
    facePoses,
)
from bmaya.core import log, decorators, progressmanager
import bmaya.core.constants
from bmaya.core.util import fileUtils

from bmaya.maya.rigging.shapes import shapelib, shapeio
from bmaya.maya.rigging.weights import weightio
from bmaya.maya.rigging import buildio
from bmaya.maya.rigging import modules
import bmaya.maya.constants
from bmaya.maya.util import dgUtils

from . import layout

RIG_ROOT_IDENTIFIER = "is_rig_root"


# TODO: the rig shouldn't be the topmost node, that should be more like an "asset" node
class Rig(Asset):
    """Rig is the base class for all rigs

    How to build a rig:

    from bmaya.maya.asset.asset import Asset
    from bmaya.maya.rigging.base.rig import Rig

    myAsset = Asset('dev|prop|cube')
    myRig = Rig(myAsset.asset_id)
    myRig.buildRig()
    myAsset.openFile(myAsset.componentPathFromType('animRig'))
    """

    def __init__(self, asset_id, has_face=True):
        super(Rig, self).__init__(asset_id)

        # TODO: is there anything identifying this as a Rig node?

        self.has_face = has_face
        self.skin_clusters = []
        # an array of dictionary representations of our module classes
        self.modules = []
        self.build_data = None
        self.components_set = None
        self.time_built = time.strftime("%c", time.localtime())

        self.init_components()
        self.init_component_folders()
        self.init_component_files()

    @property
    def meshShapes(self):
        _set_meshes = cmds.sets(self.mesh_set, query=True) or []
        _mesh_shapes = []
        for mesh in _set_meshes:
            _mesh_shapes.append(cmds.listRelatives(mesh, type="shape")[0])

        return _mesh_shapes

    @property
    def controls(self):
        _controls = []
        _set_controls = cmds.sets(self.ctrl_set, query=True) or []
        for control in _set_controls:
            _controls.append(control)

        return _controls

    @property
    def influences(self):
        return cmds.sets(self.bind_set, query=True) or []

    def add_module(self, module_dict):
        # pass it the dictionary representation of the module
        # this way we can add modules from file or object data

        assert isinstance(module_dict, dict)

        self.modules.append(module_dict)

    def build_layout(self):
        layout_mod = layout.Layout(character=self)
        layout_mod.build()
        return layout_mod.dict, layout_mod.components

    @decorators.log_fn_duration
    def build_rig(self):
        pmanager = progressmanager.ProgressManager()
        pmanager.start("Building Rig")

        self.modules = []
        self.all_controls = []
        mirror_modules = []

        pmanager.update(5, "Creating blank scene")

        # create a new scene
        cmds.file(new=True, force=True)

        pmanager.update(10, "Loading plugins")
        # load required plugins
        self.load_plugins()

        pmanager.update(15, "Making character node")

        self.make_node()

        pmanager.update(20, "Reading build file")

        # open up the character's build file (json)
        self.build_data = buildio.load(self.build.full_path)

        build_list = []

        pmanager.update(25, "Building layout rig")

        layout_dict, layout_components = self.build_layout()
        self.modules.append(layout_dict)
        self.all_controls += [comp.ctrl for comp in layout_components]

        # unflatten tree

        def add_children(mod):
            mod["character"] = self
            self.add_module(mod)
            build_list.append(mod)

            for child in mod["children"]:
                add_children(child)

        pmanager.update(30, "Flattening build tree")

        for mod in self.build_data:
            if mod["children"]:
                add_children(mod)
            else:
                mod["character"] = self
                self.add_module(mod)
                build_list.append(mod)

        pmanager.update(35, "Building limbs")

        if not build_list:
            raise RuntimeError

        for mod in build_list:
            # access the modType attribute from the module's dictionary
            mod_type = mod["modType"]

            # create a new instance of that class
            mod_instance = modules.MODULE_CLASSES[mod_type].__new__(
                modules.MODULE_CLASSES[mod_type]
            )
            mod_instance.__init__(character=self)

            for key, value in mod.items():
                # transfer the values from the read file to the instance
                setattr(mod_instance, key, value)

            # build it!
            mod_instance.build()

            self.all_controls += [comp.ctrl for comp in mod_instance.components]

            # it'll mirror if its mirror attribute is True
            mirror_instance = mod_instance.do_mirror()

            # optional, adds time.
            # cmds.refresh(currentView=True)

            if mirror_instance:
                mirror_modules.append(mirror_instance.dict)
                self.all_controls += [comp.ctrl for comp in mirror_instance.components]

        self.modules += mirror_modules

        pmanager.update(40, "Making sets")

        self.ctrl_set = cmds.sets(self.all_controls, name="CTRL_set")
        if self.has_face:
            self.faceCtrlSet = cmds.sets(name="FACE_CTRL_set")
            cmds.sets(self.faceCtrlSet, edit=True, forceElement=self.ctrl_set)

        pmanager.update(45, "Adding skinning")
        # skinning after the components have been built allows us to create
        # bind joints
        self.skin()

        pmanager.update(50, "Writing character node attributes")
        self.add_node_attrs()

        # connect modules to rig
        for mod in self.modules:
            mod_node_name = f'{mod["name"]}_{bmaya.core.constants.MODULE_SUFFIX}'
            if cmds.objExists(mod_node_name):
                dgUtils.set_attr_locked(
                    mod_node_name,
                    "character",
                    False,
                )
                cmds.connectAttr(
                    self.node + ".modules",
                    f"{mod_node_name}.character",
                )
                dgUtils.set_attr_locked(
                    mod_node_name,
                    "character",
                    True,
                )

        pmanager.update(55, "Loading control shapes")
        shapeio.load(self.component_path_from_type("cvs"))

        # progressWindow.setStatus('Loading weights')
        # progressWindow.increment(5)
        weights_dir = self.component_path_from_type("weights")
        weight_files = self.find_files_of_type(weights_dir, "weights")

        for f in weight_files:
            weightio.load(os.path.join(weights_dir, f))

        # create influences set
        self.bind_set = self.make_bind_set()

        pmanager.update(60, "Coloring controls")
        self.color_controls()

        cmds.refresh(currentView=True)

        pmanager.update(85, "Cleaning up")
        # scene cleanup:
        self.setup_mesh_referencing()
        self.lock_down_constraints()

        cmds.hide(cmds.ls(type="ikHandle"))

        pmanager.update(95, "Running post operations")
        self.run_post_ops()

        pmanager.update(100, "Finished building rig")
        pmanager.end()

        cmds.file(rename=self.animRig.full_path)
        cmds.file(save=True, type="mayaAscii", force=True)
        fileUtils.version_file(self.animRig.full_path)

        if not bmaya.maya.constants.IS_BATCH:
            cmds.viewFit(allObjects=True, fitFactor=1)

    def make_node(self):
        if not cmds.objExists(self.name + "_RIG"):
            self.node = cmds.createNode("network", name=self.name + "_RIG")

            # create an attribute to glue other parts to the rig to
            cmds.addAttr(self.node, longName="connector", attributeType="message")

            log.info("Created character node {0} <<".format(self.node))

    def add_node_attrs(self):

        if not self.node:
            raise RuntimeError("Character node does not exist yet for " + self.name)

        # Add identifying attributes for the rig node
        dgUtils.safe_add_and_lock_attr(
            self.node,
            longName=RIG_ROOT_IDENTIFIER,
            attributeType="bool",
            defaultValue=True,
        )

        added_attributes = []

        for attr in self.__dict__:
            # TODO: we may want to avoid so much json stamping and do more wiring
            # TODO: it appears like we might be double-stamping attributes
            log.info(f"Adding module attribute {attr} to node {self.node}")

            attrVal = self.__dict__[attr]
            attrType = type(attrVal)

            if attrVal is None:
                attrType = "string"
                attrVal = "None"

            if attrType in [str]:
                attrType = "string"
                attrVal = str(attrVal)

            elif attrType is list:
                cleanList = []

                for val in attrVal:
                    if type(val) in [str, int, float, bool, None]:
                        cleanList.append(val)

                    elif type(val) is dict:
                        cleanDict = {}
                        for key in val:
                            if type(val[key]) in [str, int, float, bool, None]:
                                cleanDict[key] = val[key]
                            elif isinstance(val[key], shapelib.ControlCurve):
                                cleanDict[key] = val[key].ctrl
                        cleanList.append(cleanDict)
                    elif isinstance(val, shapelib.ControlCurve):
                        cleanList.append(val.ctrl)

                attrType = "string"
                attrVal = json.dumps(cleanList)

            elif attrType is dict:
                cleanDict = {}
                for key in attrVal:
                    if type(attrVal[key]) in [str, int, float, bool, None]:
                        cleanDict[key] = attrVal[key]
                    elif isinstance(attrVal[key], shapelib.ControlCurve):
                        cleanDict[key] = attrVal[key].ctrl

                attrType = "string"
                attrVal = json.dumps(cleanDict)

            elif attrType is bool:
                attrType = "bool"
                attrVal = attrVal

            elif attrType in [
                animRig.AnimRig,
                build.Build,
                cvs.Cvs,
                mesh.Mesh,
                skeleton.Skeleton,
                weights.Weights,
            ]:
                attrType = "string"
                attrVal = self.component_path_from_type(attr)
                attr += "Path"
            else:
                attrType = "string"
                try:
                    attrVal = attr.full_path
                except AttributeError:
                    continue

            if not dgUtils.has_attribute(self.node, attr):
                if attrType == "string":
                    dgUtils.safe_add_attr(self.node, attr, dt="string", keyable=False)
                    cmds.setAttr(self.node + "." + attr, str(attrVal), type="string")
                    cmds.setAttr(f"{self.node}.{attr}", lock=True)

                else:
                    dgUtils.safe_add_and_lock_attr(
                        self.node,
                        longName=attr,
                        at=attrType,
                        dv=attrVal,
                        keyable=False,
                    )

                added_attributes.append(attr)

    def skin(self):
        # check for existing weights files. If not then skin to skeleton set
        # skin the root joint to all the meshes in the scene

        for mesh in self.meshShapes:
            weightsPath = os.path.join(
                self.weights.full_path, mesh + "." + self.weights.extension
            )
            if os.path.exists(weightsPath):
                weightio.load(weightsPath)
            elif "noSkin" not in cmds.listAttr(mesh):
                # skin meshes not marked noSkin to the root joint
                self.skin_clusters.append(
                    cmds.skinCluster(
                        bmaya.core.constants.ROOT_JOINT,
                        mesh,
                        maximumInfluences=1,
                        bindMethod=1,
                        weightDistribution=1,
                        normalizeWeights=1,
                    )[0]
                )
            else:
                log.info("Skipped applying weights on " + mesh)

    def setup_mesh_referencing(self):

        md = cmds.createNode("multDL", name="meshRef_md")
        cmds.setAttr(md + ".input2", 2)
        # don't have it show up in the mesh's channel box
        cmds.setAttr(md + ".isHistoricallyInteresting", False)

        cmds.addAttr(
            self.node,
            longName="referenceMesh",
            attributeType="bool",
            defaultValue=True,
            keyable=True,
        )
        cmds.connectAttr(self.node + ".referenceMesh", md + ".input1", force=True)

        for mesh in self.meshShapes:
            try:
                cmds.setAttr(mesh + ".overrideEnabled", 1)
                cmds.connectAttr(
                    md + ".output", mesh + ".overrideDisplayType", force=True
                )
            except RuntimeError:
                pass

    def lockMeshes(self):

        for mesh in self.meshShapes:
            numVerts = mesh.fnMesh.numVertices()

            for i in range(numVerts):
                cmds.setAttr(mesh + ".pt[{0}]".format(i), lock=True)

    def connect_to_character(self, node):

        if cmds.objExists(node):
            cmds.addAttr(node, longName="character", attributeType="message")
            cmds.connectAttr(self.node + ".connector", node + ".character")

    def hideKeyableAttr(self, obj):
        if cmds.objExists(obj):
            cmds.setAttr(obj, keyable=False, channelBox=False)

    def lock_down_constraints(self):
        # manage constraints
        for constraint in cmds.ls(type="constraint"):
            attrHideList = ["nodeState", "interpType"]

            constraintType = cmds.objectType(constraint)

            if constraintType in ["parentConstraint", "orientConstraint"]:
                cmds.setAttr(constraint + ".interpType", 2)
                attrHideList += ["rdtx", "rdty", "rdtz"]
                if constraintType == "parentConstraint":
                    weights = cmds.parentConstraint(
                        constraint, query=True, weightAliasList=True
                    )
                else:
                    weights = cmds.orientConstraint(
                        constraint, query=True, weightAliasList=True
                    )

                if weights:
                    for w in range(len(weights)):
                        attrHideList += ["w{0}".format(w)]
            else:
                weights = cmds.parentConstraint(
                    constraint, query=True, weightAliasList=True
                )
                if weights:
                    for w in range(len(weights)):
                        attrHideList += ["w{0}".format(w)]

            for attr in attrHideList:
                self.hideKeyableAttr("{0}.{1}".format(constraint, attr))

    def make_bind_set(self):
        skelJoints = set(cmds.listRelatives("SKELETON", type="joint", ad=1))
        skinClusterInfluences = set()

        for mesh in self.meshShapes:
            existingSkin = cmds.ls(cmds.listHistory(mesh), type="skinCluster")
            if existingSkin:
                members = cmds.skinCluster(existingSkin[0], query=True, influence=True)
                for jnt in members:
                    if jnt in skelJoints:
                        skinClusterInfluences.add(jnt)

        bindSet = cmds.sets(list(skinClusterInfluences), name="BIND_set")

        return bindSet

    def color_controls(self):
        for ctrl in self.controls:
            if "_M_" in ctrl:
                side = 22
            elif "_L_" in ctrl:
                side = 6
            elif "_R_" in ctrl:
                side = 13
            else:
                side = 22
            try:
                cmds.setAttr(ctrl + ".overrideEnabled", True)
                cmds.setAttr(ctrl + ".overrideColor", side)
            except BaseException:
                # for sets nested within the ctrl set
                pass

    def load_plugins(self):
        for plugin in bmaya.maya.constants.REQUIRED_PLUGINS:
            cmds.loadPlugin(plugin, quiet=True)

    def init_components(self):
        # initialize the component objects for the asset
        self.mesh = mesh.Mesh(self, "mesh")
        self.skeleton = skeleton.Skeleton(self, "skeleton")
        self.weights = weights.Weights(self, "weights")
        self.cvs = cvs.Cvs(self, "cvs")
        self.build = build.Build(self, "build")
        self.animRig = animRig.AnimRig(self, "animRig")
        self.postops = postops.PostOps(self, "postops")

        if self.has_face:
            self.facePoses = facePoses.FacePoses(self, "facePoses")

        self.components += [
            self.mesh,
            self.skeleton,
            self.weights,
            self.cvs,
            self.build,
            self.animRig,
            self.postops,
        ]
        if self.has_face:
            self.components.append(self.facePoses)

    def init_component_folders(self):
        """Creates the component folders for the asset"""

        for component in self.components:
            dirpath = os.path.dirname(component.full_path)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

        log.info("Component folders initialized")

    def init_component_files(self):

        if not os.path.exists(self.mesh.full_path):
            log.info("Creating mesh file.")
            # mesh file is just a blank ma
            cmds.file(new=True, force=True)
            cmds.file(rename=self.mesh.full_path)
            cmds.file(save=True, type="mayaAscii", force=True)
            fileUtils.version_file(self.mesh.full_path)
        else:
            log.info("A working mesh file already exists for " + self.name)

        if not os.path.exists(self.skeleton.full_path):
            log.info("Creating skeleton file.")
            # create a single joint for the default skeleton file
            cmds.file(new=True, force=True)
            cmds.joint(name=bmaya.core.constants.ROOT_JOINT)
            cmds.file(rename=self.skeleton.full_path)
            cmds.file(save=True, type="mayaAscii", force=True)
            fileUtils.version_file(self.skeleton.full_path)
        else:
            log.info("A working skeleton file already exists for " + self.name)

        if not os.path.exists(self.cvs.full_path):
            log.info("Creating cvs file.")
            with open(self.cvs.full_path, "w") as f:
                json.dump({}, f)
            fileUtils.version_file(self.cvs.full_path)
        else:
            log.info("A working cvs file already exists for " + self.name)

        if not os.path.exists(self.build.full_path):
            log.info("Creating build file using default LayoutRig template.")
            # give it a LayoutRig template
            layoutRigPath = os.path.join(
                bmaya.maya.constants.RIG_TEMPLATES_DIR, "LayoutRig.json"
            )

            with open(layoutRigPath, "r") as f:
                layoutRigData = f.read()

            # write the contents to this asset's build file
            with open(self.build.full_path, "w") as f:
                f.write(layoutRigData)

            fileUtils.version_file(self.build.full_path)

        if not os.path.exists(self.postops.full_path):
            log.info("Creating postops file")

            # Write the template python file
            with open(self.postops.full_path, "w") as f:
                f.write(bmaya.maya.constants.POSTOPS_TEMPLATE)

            fileUtils.version_file(self.postops.full_path)

        if self.has_face:
            if not os.path.exists(self.facePoses.full_path):
                log.info("Creating facePoses file")

                # write a blank json file
                with open(self.facePoses.full_path, "w") as f:
                    json.dump({}, f)
                fileUtils.version_file(self.facePoses.full_path)

    def run_post_ops(self):
        # run postops file
        with open(self.postops.full_path, "r") as f:
            code = f.read()
            exec(code)


def is_rig_root(node):
    return dgUtils.has_attribute(node, RIG_ROOT_IDENTIFIER)
