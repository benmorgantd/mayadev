import maya.cmds as cmds
import maya.OpenMaya as om
import Gossamer.modules.module as module
import Gossamer.library.control_curves as control_curves
import Gossamer.library.pole_vector_finder


class IkLeg():
  def __init__(self, joints=None, ikFkLeg_node=None):
    """Creates a 3 joint rotate plane ik leg chain"""

    if len(joints) != 3:
      raise ValueError("Must be passed a 3 joint chain: [upLeg, loLeg, foot]")

    self.joints = joints

    self.ikFkLeg_node = ikFkLeg_node

    if not self.ikFkLeg_node:
      return

    self.name = cmds.getAttr("{0}.name".format(self.ikFkLeg_node))
    self.side = cmds.getAttr("{0}.side".format(self.ikFkLeg_node))

    self.rp_ik = None
    self.ik_cc = None
    self.ik_cc_grp = None
    # self.upper_ik_cc = None
    # self.upper_ik_cc_grp = None
    self.pv_cc = None
    self.pv_cc_grp = None
    self.control_groups = None
    self.ik_grp = None

    # main build functions
    self.setup_ik_system()
    self.make_control_curves()
    self.set_control_constraints()
    self.set_cc_rot_orders()
    self.lock_control_curve_attr()
    self.setup_pole_vector_switching()
    self.connect_to_module()
    self.organize_components()
    cmds.select(cl=1)

  def setup_ik_system(self):
    """Add the rpIk handle for the ik chain.

    :return: None
    """

    self.rp_ik = cmds.ikHandle(sj=self.joints[0], ee=self.joints[2], n=self.side + "_leg_rpIK", sol="ikRPsolver")
    cmds.addAttr(self.rp_ik[0], attributeType="message", longName="ikHandle")
    cmds.hide(self.rp_ik[0])

  def make_control_curves(self):
    """Create and position control curves.

    :return: None
    """

    # lower ik control
    self.ik_cc = control_curves.cube_ctrl(name="_".join([self.side, "legIK_cc"]), scale=module.SCALE_CONSTANT * 1.25)
    self.ik_cc_grp = cmds.group(self.ik_cc[0], n="_".join([self.ik_cc[0], "grp"]))
    cmds.delete(cmds.parentConstraint(self.joints[2], self.ik_cc_grp, mo=0))

    # pole vector control
    self.pv_cc = control_curves.sphere_ctrl(
    name="_".join([self.side, "legPv_cc"]), scale=module.SCALE_CONSTANT * .5)
    self.pv_cc_grp = cmds.group(self.pv_cc[0], name=self.pv_cc[0] + "_grp")
    cmds.xform(self.pv_cc_grp, t=Gossamer.library.pole_vector_finder.find_pole_vector(self.joints[0], self.joints[1], 
                            self.joints[2], scale_factor=1.5), ws=1)

    cmds.parent(self.pv_cc_grp, "layout_cc")

    # self.control_groups = [self.ik_cc_grp, self.upper_ik_cc_grp, self.pv_cc_grp]
    self.control_groups = [self.ik_cc_grp, self.pv_cc_grp]

  def set_control_constraints(self):
    """Setup constraints for ik controls.

    :return: None
    """

    # lower ik control
    cmds.pointConstraint(self.ik_cc, self.rp_ik[0], mo=1)
    cmds.orientConstraint(self.ik_cc, self.joints[2], mo=1)
    # it's important to only connect control scales with direct connections to avoid double transformations
    cmds.connectAttr("{0}.scale".format(self.ik_cc[0]), "{0}.scale".format(self.joints[2]))

    # upper ik control
    # cmds.pointConstraint(self.upper_ik_cc, self.joints[0], mo=1)
    # cmds.scaleConstraint(self.upper_ik_cc, self.joints[0], mo=1)

    # pole vector control
    cmds.poleVectorConstraint(self.pv_cc[0], self.rp_ik[0])

  def set_cc_rot_orders(self):
    """Set the correct rotation orders for the ik controls

    :return: None
    """

    # cmds.setAttr(self.upper_ik_cc[0] + ".rotateOrder", cmds.getAttr(self.joints[0] + ".rotateOrder"))
    cmds.setAttr(self.ik_cc[0] + ".rotateOrder", cmds.getAttr(self.joints[2] + ".rotateOrder"))

  def lock_control_curve_attr(self):
    """Lock and hide certain attributes on our controls.

    :return: None
    """

    for cc in [self.ik_cc, self.pv_cc]:
      cmds.setAttr(cc[0] + ".v", keyable=0, channelBox=0, lock=1)
      if cc != self.ik_cc:
        cmds.setAttr(cc[0] + ".rx", keyable=0, channelBox=0, lock=1)
        cmds.setAttr(cc[0] + ".ry", keyable=0, channelBox=0, lock=1)
        cmds.setAttr(cc[0] + ".rz", keyable=0, channelBox=0, lock=1)
        cmds.setAttr(cc[0] + ".sx", keyable=0, channelBox=0, lock=0)
        cmds.setAttr(cc[0] + ".sy", keyable=0, channelBox=0, lock=0)
        cmds.setAttr(cc[0] + ".sz", keyable=0, channelBox=0, lock=0)

  def setup_pole_vector_switching(self):
    """Sets up follow switching for the pole vector.

    :return: None
    """

    cmds.addAttr(self.pv_cc[0], longName="followFoot", attributeType="long", min=0, max=1, keyable=1, defaultValue=1)
    space_grp = cmds.group(self.pv_cc[0], relative=1, name="{0}_space_grp".format(self.pv_cc[0]))

    const = cmds.parentConstraint(self.ik_cc[0], space_grp, mo=1)
    cmds.connectAttr("{0}.followFoot".format(self.pv_cc[0]), "{0}.{1}W0".format(const[0], self.ik_cc[0]))

  def connect_to_module(self):
    cmds.addAttr(self.ik_cc[0], longName="ikControl", attributeType="message")
    cmds.addAttr(self.ik_cc[0], longName="module", attributeType="message")
    cmds.addAttr(self.ik_cc_grp, longName="module", attributeType="message")

    cmds.addAttr(self.pv_cc[0], longName="ikPoleVectorControl", attributeType="message")
    cmds.addAttr(self.pv_cc[0], longName="module", attributeType="message")
    cmds.addAttr(self.pv_cc_grp, longName="module", attributeType="message")

    cmds.addAttr(self.rp_ik[0], longName="module", attributeType="message")

    cmds.connectAttr("{0}.components".format(self.ikFkLeg_node), "{0}.module".format(self.ik_cc[0]))
    cmds.connectAttr("{0}.components".format(self.ikFkLeg_node), "{0}.module".format(self.pv_cc[0]))
    cmds.connectAttr("{0}.components".format(self.ikFkLeg_node), "{0}.module".format(self.rp_ik[0]))
    cmds.connectAttr("{0}.components".format(self.ikFkLeg_node), "{0}.module".format(self.ik_cc_grp))
    cmds.connectAttr("{0}.components".format(self.ikFkLeg_node), "{0}.module".format(self.pv_cc_grp))

    cmds.connectAttr("{0}.ikControl".format(self.ikFkLeg_node), "{0}.ikControl".format(self.ik_cc[0]))
    cmds.connectAttr("{0}.ikPoleVectorControl".format(self.ikFkLeg_node), "{0}.ikPoleVectorControl".format(self.pv_cc[0]))
    cmds.connectAttr("{0}.ikHandle".format(self.ikFkLeg_node), "{0}.ikHandle".format(self.rp_ik[0]))

  def organize_components(self):
    self.ik_grp = cmds.group(self.ik_cc_grp, self.rp_ik[0], name=self.name + "_ik_grp")
