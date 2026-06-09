"""Purpose:
The Module class is the base class for all rig modules. It contains the basic attributes and methods that
all modules will need, such as building the module, creating the module node, adding attributes to the node,
finding mirror nodes, etc. Each specific module (such as Arm, Leg, Spine, etc.) will inherit from this class
and implement its own build method to create the specific rig for that module.
The module also contains some class methods that are used by various modules, such as adding a moveable pivot to a control, etc.
"""

import json
import inspect

import maya.cmds as cmds
import maya.api.OpenMaya as om

from bmaya.core import constants, log
from bmaya.maya.util import nameUtils, mathUtils
from bmaya.maya.rigging.shapes import shapelib


class Module(object):
    mirrorPairs = {"L": "R", "R": "L", "M": None}

    def __init__(
        self,
        character=None,
        name="module1",
        mod_type="Module",
        parent=None,
        side="L",
        mirror=False,
        shape_type="cube",
        align_world=None,
    ):

        self.character = character

        self.name = name
        self.mod_type = mod_type
        self.parent = self.determine_parent(parent)
        self.side = side
        self.mirror = mirror
        self.shape_type = shape_type
        self.align_world = align_world

        self.components = []
        self.bind_joints = []
        self.drive_joints = []

        self.node = None
        self.driver_grp = None
        self.mod_grp = None
        self.components_grp = None
        self.start_joint = None
        self.end_joint = None

    @property
    def dict(self):
        return {key: value for key, value in self.__dict__.items() if "__" not in key}

    def build(self):
        # should get defined by child class
        raise NotImplementedError("Each module must implement its own build method.")

    def make_node(self):
        # create the module node before anything gets built.
        if not cmds.objExists("{0}_{1}".format(self.name, constants.MODULE_SUFFIX)):
            # this creates a locator shape of the given name
            self.node = cmds.createNode(
                "network", name="{0}_{1}".format(self.name, constants.MODULE_SUFFIX)
            )
            # holds all the parts of the module. Not for transforming
            self.mod_grp = cmds.createNode("transform", name=self.name + "_GRP")
            # holds the components of the node. Transform this should not
            # result in double xforms
            self.components_grp = cmds.createNode(
                "transform", name=self.name + "_COMPONENTS"
            )
            # holds the driver joints for the node
            self.driver_grp = cmds.createNode("transform", name=self.name + "_DRIVERS")
            cmds.hide(self.driver_grp)
            cmds.parent(self.driver_grp, self.components_grp)

            # print 'Created {0} node {1} <<'.format(self.mod_type,
            # self.node)
        else:
            raise RuntimeError(
                "Module of name {0} already exists.".format(
                    "{0}_{1}".format(self.name, constants.MODULE_SUFFIX)
                )
            )

    def parse_for_maya_attr(self, attr):

        if isinstance(attr, bool):
            mayaAttrType = "bool"
            mayaAttrVal = attr

        elif isinstance(attr, str):
            mayaAttrType = "string"
            mayaAttrVal = str(attr)

        elif isinstance(attr, list):
            cleanList = []

            for val in attr:
                if isinstance(val, (str, int, float, bool)):
                    cleanList.append(val)
                elif isinstance(val, shapelib.ControlCurve):
                    cleanList.append(val.ctrl)

            mayaAttrType = "string"
            mayaAttrVal = json.dumps(cleanList)

        elif isinstance(attr, dict):
            cleanDict = {}

            for key, value in attr.items():
                if isinstance(value, (str, int, float, bool)):
                    cleanDict[key] = value
                elif isinstance(value, shapelib.ControlCurve):
                    cleanDict[key] = value.ctrl

            mayaAttrType = "string"
            mayaAttrVal = json.dumps(cleanDict)

        elif not attr:
            mayaAttrType = "string"
            mayaAttrVal = "None"

        elif isinstance(attr, shapelib.ControlCurve):
            mayaAttrType = "string"
            mayaAttrVal = attr.ctrl

        else:
            mayaAttrType = "string"
            mayaAttrVal = str(attr)

        return mayaAttrType, mayaAttrVal

    def add_node_attrs(self):
        if not self.node:
            raise RuntimeError("Module node does not exist yet for " + self.name)

        for attrName, attrVal in self.__dict__.items():
            attrType = type(attrVal)

            mayaAttrType, mayaAttrVal = self.parse_for_maya_attr(attrVal)

            # add the attribute

            if mayaAttrType == "string":
                cmds.addAttr(self.node, ln=attrName, dt="string", keyable=False)
                cmds.setAttr(self.node + "." + attrName, mayaAttrVal, type="string")
            elif mayaAttrType == "bool":
                cmds.addAttr(
                    self.node, ln=attrName, at="bool", dv=mayaAttrVal, keyable=False
                )
            elif mayaAttrType == "message":
                cmds.addAttr(self.node, ln=attrName, at=mayaAttrType, keyable=False)
            else:
                try:
                    cmds.addAttr(
                        self.node,
                        ln=attrName,
                        at=mayaAttrType,
                        dv=mayaAttrVal,
                        keyable=False,
                    )
                except TypeError:
                    log.info("--")
                    log.info("type: ", mayaAttrType)
                    log.info("value: ", mayaAttrVal)
                    log.info(
                        "Warning: Failed to add attribute '{0}'\n--".format(attrName)
                    )

    def find_mirror(self, node):
        """Returns the mirrored node of the same type if it's in the scene.
        Else returns None"""

        if isinstance(node, (int, float)):
            # TODO: we could be mirroring vectors here maybe
            return node
        elif not node:
            return None

        mirror_side = Module.mirrorPairs[self.side]

        if node in ["R", "L"]:
            return mirror_side

        mirror_node = node.replace(("_" + self.side + "_"), ("_" + mirror_side + "_"))

        try:
            nodeType = cmds.objectType(node)
        except RuntimeError:
            return mirror_node

        if mirror_node in cmds.ls(type=nodeType):
            return mirror_node
        else:
            return None

    def do_mirror(self):

        if self.mirror:
            # get all the arguments needed to build self and find their mirrors
            # before creating the instance

            mirrored_init_args = {}

            raise NotImplementedError("Mirroring is not implemented yet for py3")

            # TODO: py3
            for attr in inspect.getfullargspec(self.__init__).args:
                try:
                    value = getattr(self, attr)
                except AttributeError:
                    # could be trying to get the value of 'self'
                    continue

                if isinstance(value, str):
                    mirrored_init_args[attr] = self.find_mirror(value)

                elif isinstance(value, list):
                    mirrorList = []
                    for j in value:
                        mirrorList.append(self.find_mirror(j))
                    mirrored_init_args[attr] = mirrorList

                else:
                    mirrored_init_args[attr] = value

            # we don't want to worry about a name convention for mirrored
            # modules
            mirrored_init_args["name"] = self.name + "_mirror"
            mirrored_init_args["mirror"] = False

            mirrorSelf = self.__class__()

            for arg in mirrored_init_args.keys():
                if arg != "parent":
                    setattr(mirrorSelf, arg, mirrored_init_args[arg])

            # set attribute manually for parent so that we know it has the
            # start_joint variable set
            setattr(
                mirrorSelf, "parent", mirrorSelf.determine_parent(mirrorSelf.parent)
            )

            mirrorSelf.build()

            return mirrorSelf
        else:
            return None

    def determine_parent(self, parent):
        if parent and cmds.objExists(parent):
            return parent
        elif hasattr(self, "start_joint"):
            parent_transform = cmds.listRelatives(
                self.start_joint, parent=True, type="joint"
            )
            if parent_transform:
                parent_transform = parent_transform[0]
            else:
                parent_transform = constants.TOP_LAYOUT_CONTROL

            return parent_transform
        else:
            return constants.TOP_LAYOUT_CONTROL

    def parent_module(self):
        # check if a specific joint parent was given. If not then check the parent of the start_joint
        # This means every module except Root will need a start_joint

        if self.mod_type == "Layout":
            cmds.parent(self.components_grp, self.mod_grp)
            cmds.parent(self.mod_grp, self.character.modules_grp)
            return

        # parent the whole module's group into the module group for the
        # character
        cmds.parent(self.mod_grp, self.character.modules_grp)
        cmds.parent(self.components_grp, self.mod_grp)

        # we might give it a specific joint parent
        if self.parent:
            # For Matrix Constraints we can't parentConstrain to the whole module group. We need to do to just the module's components
            # TODO: we'd have to do this for all groups under self.componentsGrp
            # TODO: we'd want to move the drivers group out
            self.parent_constrain(
                self.parent, self.components[0].offset_grp, maintain_offset=True
            )
        elif hasattr(self, "start_joint"):
            parent_transform = cmds.listRelatives(
                self.start_joint, parent=True, type="joint"
            )
            if parent_transform:
                parent_transform = parent_transform[0]
            else:
                parent_transform = constants.BOTTOM_LAYOUT_CONTROL

            # Todo: this is where you could add a followSwitch option
            # ONLY constrain the components of the module, not the driver
            # joints, or else we'll get double transforms
            self.parent_constrain(
                parent_transform, self.components[0].offset_grp, maintain_offset=True
            )

        elif self.mod_type != "Layout":
            raise RuntimeError("Module must have a start joint.")

    def parent_constrain(self, parent=None, child=None, maintain_offset=True):
        if isinstance(parent, shapelib.ControlCurve):
            parent = parent.ctrl
        if isinstance(child, shapelib.ControlCurve):
            child = child.ctrl

        # create a matrix-style constraint
        mult_matrix = cmds.createNode("multMatrix", name=child + "_parentConstraint_mm")
        cmds.connectAttr(parent + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]")
        # TODO: offset calculation
        # NOTE: offsetParentMatrix is the offset from the _child's_ parent. So the existing offset has to be taken
        # into account as well as the offset from the parent to the child
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{child}.offsetParentMatrix")

        # const = cmds.parentConstraint(parent, child, mo=maintainOffset)[0]

        pivotCtrl = cmds.listConnections(
            parent + ".rotatePivot", type="transform", exactType=True
        )

        if pivotCtrl:
            raise NotImplementedError(
                "This method of parenting does not work with controls that have a custom pivot"
            )

        return mult_matrix

        if pivotCtrl and not cmds.objExists(const + "_offsetVector"):
            pivotCtrl = pivotCtrl[0]
            # create a node to calculate the vector from the pivot to that
            # transform's constraint start location
            offsetVector = cmds.createNode(
                "plusMinusAverage", name=const + "_offsetVector"
            )
            # set the operation to subtract
            cmds.setAttr(offsetVector + ".operation", 2)
            cmds.connectAttr(pivotCtrl + ".translate", offsetVector + ".input3D[1]")
            for i in range(
                len(cmds.parentConstraint(const, query=True, targetList=True))
            ):
                for axis in "xyz":
                    cmds.setAttr(
                        offsetVector + ".input3D[0].input3D{0}".format(axis),
                        cmds.getAttr(
                            const
                            + ".target[{0}].targetOffsetTranslate{1}".format(
                                i, axis.upper()
                            )
                        ),
                    )

                cmds.connectAttr(
                    offsetVector + ".output3D",
                    const + ".target[{0}].targetOffsetTranslate".format(i),
                )

        return const

    def check_contract(self):
        # TODO: Check by attribute types
        return True

        # if not self.contract:
        #     return True
        #
        # nullValues = [v for v in self.contract if not v]
        #
        # if nullValues:
        #     raise RuntimeError(
        #         'Contract for {0} not yet fulfilled.'.format(self.name))
        #
        # print 'Contract for {0} fulfilled'.format(self.modType)
        # return True

    def connect_components(self):
        """Connects the module's compenents to the module"""

        for ctrl in self.components:
            if not cmds.objExists(ctrl.ctrl + ".module"):
                cmds.addAttr(ctrl.ctrl, longName="module", attributeType="message")

            cmds.connectAttr(
                self.node + ".components", ctrl.ctrl + ".module", force=True
            )

    def connect_bind_joints(self):
        """Connects the module's bind joints to their control"""

        for jnt in self.bind_joints:
            if not cmds.objExists(jnt + ".module"):
                cmds.addAttr(jnt, longName="module", attributeType="message")
            else:
                raise RuntimeError("{0} already belongs to a module".format(jnt))

            cmds.connectAttr(self.node + ".bind_joints", jnt + ".module")

    def find_hierarchy_joints(
        self, shortest_distance=False, start_joint=None, end_joint=None, exclude=[]
    ):
        """Expands from a start joint and until it hits excluded joints."""

        if not start_joint:
            start_joint = self.start_joint
        if not end_joint and hasattr(self, "end_joint"):
            end_joint = self.end_joint

        sel = om.MSelectionList()
        bind_joints = []

        if not start_joint:
            raise RuntimeError("Need a start joint.")

        sel.add(start_joint)
        dag = om.MDagPath()
        sel.getDagPath(0, dag)

        it_dag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kJoint)
        it_dag.reset(dag, om.MItDag.kDepthFirst, om.MFn.kJoint)

        while not it_dag.isDone():
            jnt = it_dag.partialPathName()

            if jnt not in exclude:
                if jnt != end_joint:
                    jnt_children = (
                        cmds.listRelatives(
                            jnt, type="joint", children=True, allDescendents=True
                        )
                        or []
                    )
                    if shortest_distance and end_joint not in jnt_children:
                        it_dag.prune()
                    else:
                        bind_joints.append(jnt)
                else:
                    # add control on end joint then prune
                    bind_joints.append(jnt)
                    it_dag.prune()
            else:
                it_dag.prune()

            it_dag.next()

        return bind_joints

    def create_drive_joint(self, jnt, label="Driver", constrain=True):
        driver = cmds.duplicate(
            jnt, parentOnly=True, name=jnt.replace(constants.JOINT_SUFFIX, label)
        )[0]

        jointParent = cmds.listRelatives(jnt, parent=True, type="joint")

        if jointParent:
            driver_parent = jointParent[0].replace(constants.JOINT_SUFFIX, label)
            if cmds.objExists(driver_parent):
                if cmds.listRelatives(driver, parent=True)[0] != driver_parent:
                    cmds.parent(driver, driver_parent, absolute=True)

        if constrain:
            self.parent_constrain(driver, jnt, maintain_offset=False)

            # add a connection for driver and driven joint
            # only add this attribute if it's a direct constraint
            cmds.addAttr(jnt, longName="driver", attributeType="message")
            cmds.addAttr(driver, longName="driven", attributeType="message")
            cmds.connectAttr(driver + ".driven", jnt + ".driver")

        return driver

    def create_drive_joints(self, label="DRIVER", constrain=True):
        drive_joints = []

        log.info(f"Creating drive joints for {self.bind_joints}")

        for joint in self.bind_joints:
            drive_joints.append(
                self.create_drive_joint(joint, label=label, constrain=constrain)
            )

        cmds.parent(drive_joints[0], self.driver_grp)

        return drive_joints

    def make_ik_handle(self, start_joint, end_joint, solver_type, name):

        ik = cmds.ikHandle(
            startJoint=start_joint,
            endEffector=end_joint,
            name=name,
            solver=solver_type,
        )[0]

        grp = cmds.group(empty=True, name=name + "_grp")

        mathUtils.match_transforms(ik, grp)

        cmds.parent(ik, grp)

        return [ik, grp]

    def get_driver(self, joint):

        if "driver" in cmds.listAttr(joint):
            driver = cmds.listConnections(joint + ".driver", source=True)
            if driver:
                return driver[0]
            else:
                raise ValueError("Driver connection lost on {0}".format(joint))
        else:
            raise ValueError("Given joint {0} has no direct driver.".format(joint))

    def blend_chains(self, fk_chain, ik_chain, child_chain, drive_attribute):

        # create the reverse node (name is now more vague)
        reverse = cmds.createNode("reverse", name=child_chain[0] + "_REV")
        cmds.connectAttr(drive_attribute, reverse + ".inputX")
        reverseAttr = reverse + ".outputX"

        for i in range(len(fk_chain)):
            const = cmds.parentConstraint(
                fk_chain[i], ik_chain[i], child_chain[i], maintainOffset=True
            )[0]

            cmds.connectAttr(reverseAttr, "{0}.{1}W0".format(const, fk_chain[i]))
            cmds.connectAttr(drive_attribute, "{0}.{1}W1".format(const, ik_chain[i]))

            # set interpolation type to Shortest
            cmds.setAttr(const + ".interpType", 2)

            self.message_connect(child_chain[i], fk_chain[i], "fkDriver", "driven")
            self.message_connect(child_chain[i], ik_chain[i], "ikDriver", "driven")

        return reverseAttr

        # TODO: add a drive attribute on the module

    def message_connect(self, node_a, node_b, longName_a, longName_b):

        if longName_a not in cmds.listAttr(node_a):
            cmds.addAttr(node_a, longName=longName_a, attributeType="message")
        if longName_b not in cmds.listAttr(node_b):
            cmds.addAttr(node_b, longName=longName_b, attributeType="message")

        cmds.connectAttr(
            "{0}.{1}".format(node_a, longName_a), "{0}.{1}".format(node_b, longName_b)
        )

    def capture_component_defaults(self):
        # get the controls that are in the module
        for component in self.components:
            cmds.addAttr(component.ctrl, longName="defaultValues", dt="string")

            default_values = {}

            for attr in cmds.listAttr(component.ctrl, keyable=True):
                default_values[attr] = cmds.getAttr(
                    "{0}.{1}".format(component.ctrl, attr)
                )

            cmds.setAttr(
                component.ctrl + ".defaultValues",
                json.dumps(default_values),
                type="string",
            )

        # capture defaults for keyable module attributes as well
        cmds.addAttr(self.node, longName="defaultValues", dt="string")

        default_values = {}

        for attr in cmds.listAttr(self.node, keyable=True) or []:
            default_values[attr] = cmds.getAttr("{0}.{1}".format(self.node, attr))

        cmds.setAttr(
            self.node + ".defaultValues", json.dumps(default_values), type="string"
        )

    def find_joint_name(self, node, identifier=None, count=0, suffix="DRIVER"):
        node_split = node.split("_")
        if identifier:
            node_split[0] += identifier
        if isinstance(count, int):
            node_split[1] = str(count).zfill(2)

        jnt_name = "_".join(node_split[0:-1])

        suffix = suffix.replace("_", "")

        jnt_name = jnt_name + "_" + suffix

        return jnt_name

    def setup_align_world(self, component, default_value=0):
        if self.align_world is None:
            return

        const = cmds.orientConstraint(
            constants.BOTTOM_LAYOUT_CONTROL, component.space_grp, mo=1
        )[0]
        cmds.setAttr(const + ".interpType", 2)

        cmds.addAttr(
            component.ctrl,
            longName="followWorld",
            defaultValue=default_value,
            attributeType="bool",
            keyable=True,
        )

        cmds.connectAttr(
            component.ctrl + ".followWorld",
            const + "." + constants.BOTTOM_LAYOUT_CONTROL + "W0",
        )

    def find_twist_joints(self, jnt):
        children = cmds.listRelatives(jnt, type="joint", children=True)

        twist_joints = []

        for c in children:
            if "Twist" in c:
                twist_joints.append(c)

        # will ascend 00 -> 0x
        twist_joints.sort()

        return twist_joints

    @classmethod
    def add_moveable_pivot(cls, ctrl):
        if isinstance(ctrl, shapelib.ControlCurve):
            ctrl = ctrl.ctrl

        # add a new control that represents the pivot for this control
        pivot = shapelib.ControlCurve(
            name=nameUtils.find_control_name(ctrl, identifier="Pivot"),
            shapeType="pivot",
        )
        cmds.parent(pivot.offset_grp, ctrl)
        cmds.connectAttr(
            "{0}.translate".format(pivot.ctrl), "{0}.rotatePivot".format(ctrl)
        )
        cmds.connectAttr(
            "{0}.translate".format(pivot.ctrl), "{0}.scalePivot".format(ctrl)
        )

        parent_constraints = list(
            set(cmds.listConnections(ctrl, type="parentConstraint") or [])
        )

        # At the time of the pivot's creation, it could be that no child modules
        # have been constrained to that control yet.
        for const in parent_constraints:
            # create a node to calculate the vector from the pivot to that
            # transform's constraint start location
            offset_vector = cmds.createNode(
                "plusMinusAverage", name=const + "_offsetVector"
            )
            # set the operation to subtract
            cmds.setAttr(offset_vector + ".operation", 2)
            cmds.connectAttr(pivot.ctrl + ".translate", offset_vector + ".input3D[1]")
            for i in range(
                len(cmds.parentConstraint(const, query=True, targetList=True))
            ):
                for axis in "xyz":
                    cmds.setAttr(
                        offset_vector + ".input3D[0].input3D{0}".format(axis),
                        cmds.getAttr(
                            const
                            + ".target[{0}].targetOffsetTranslate{1}".format(
                                i, axis.upper()
                            )
                        ),
                    )

                cmds.connectAttr(
                    offset_vector + ".output3D",
                    const + ".target[{0}].targetOffsetTranslate".format(i),
                )

        cmds.addAttr(
            ctrl,
            longName="showMoveablePivot",
            attributeType="bool",
            keyable=True,
            defaultValue=False,
        )
        cmds.connectAttr(ctrl + ".showMoveablePivot", pivot.ctrl + ".visibility")

        return pivot

    def build_fk_controls(self, drive_joints, setup_align_world=False):

        components = []

        for i in range(0, len(drive_joints)):
            jnt = drive_joints[i]

            # easy naming override for face controls...
            # TODO: This could be replaced if I ever made a shape swapping
            # system
            if "Driver_" in jnt:
                shape_type_override = "diamond"
            elif "Base_" in jnt:
                shape_type_override = "circle"
            else:
                shape_type_override = "cube"

            ctrl = shapelib.ControlCurve(
                name=nameUtils.find_control_name(jnt, identifier="Fk"),
                shapeType=shape_type_override,
                jnt=jnt,
            )

            components.append(ctrl)

            self.parent_constrain(ctrl.ctrl, jnt, maintain_offset=True)

            if i == 0:
                cmds.parent(ctrl.offset_grp, self.components_grp)
            else:
                parent_joint = cmds.listRelatives(jnt, parent=True, type="joint")[0]

                if cmds.objExists(parent_joint + ".driveCtrl"):
                    parentCtrl = cmds.listConnections(parent_joint + ".driveCtrl")
                else:
                    parentCtrl = None

                if parentCtrl:
                    cmds.parent(ctrl.offset_grp, parentCtrl[0])
                else:
                    cmds.parent(ctrl.offset_grp, components[0].ctrl)

            cmds.addAttr(jnt, longName="driveCtrl", attributeType="message")
            cmds.addAttr(ctrl.ctrl, longName="driveJoint", attributeType="message")
            cmds.connectAttr(ctrl.ctrl + ".driveJoint", jnt + ".driveCtrl")

        if setup_align_world:
            self.setup_align_world(components[0], default_value=self.align_world)

        return components
