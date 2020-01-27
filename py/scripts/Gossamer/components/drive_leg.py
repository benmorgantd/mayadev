import maya.cmds as cmds
import maya.OpenMaya as om
import Gossamer.library.control_curves as control_curves
import Gossamer.modules.module as module


class DriveLeg():
  def __init__(self, joints=None, ikFkLeg_node=None, ik_leg=None, fk_leg=None, blend_control=None):
    """Creates a 3 joint ik/fk blended leg chain.

    :param ik_leg: An IkLeg object used for blending.
    :param fk_leg: An FkLeg object used for blending.
    :type ik_leg: IkLeg
    :type fk_leg: FkLeg
    """

    self.ik_leg = ik_leg
    self.fk_leg = fk_leg
    self.upLeg_twist_ik = None
    self.ikFkLeg_node = ikFkLeg_node
    self.joints = joints
    self.ikFkLeg_node = ikFkLeg_node
    self.side = cmds.getAttr("{0}.side".format(self.ikFkLeg_node))

    if len(self.joints) != 3:
      raise ValueError("Must be passed a 3 joint chain: [upLeg, loLeg, foot]")

    self.pc_upLegs = None
    self.oc_loLegs = None
    self.oc_foot = None
    self.sc_foot = None
    self.switch_cc = None
    self.switch_cc_grp = None
    self.upLeg_cc = None
    self.upLeg_cc_grp = None
    self.blend_constraints = []
    self.upLeg_inv_md = None

    # main methods
    self.setup_joint_constraints()
    self.make_switch_control()
    self.setup_ik_switching()
    self.connect_to_module()

  def setup_joint_constraints(self):
    """Sets up the parent and orient constraints necessary for an ik/fk blending setup and sets their interpolation
    types to "shortest"

    :return: A list containing our new parent and orient constraints.
    :rtype: list
    """

    for i in range(3):

      # delete any existing constraints on the drive joints
      cmds.delete(self.joints[i], constraints=1)

      self.blend_constraints.append(cmds.pointConstraint(self.ik_leg.joints[i], self.fk_leg.joints[i], self.joints[i], mo=1)[0])
      self.blend_constraints.append(cmds.orientConstraint(self.ik_leg.joints[i], self.fk_leg.joints[i], self.joints[i], mo=1)[0])

    for constraint in self.blend_constraints:
      # set each constraint to "shortest" interpolation type
      try:
        cmds.setAttr(constraint + ".interpType", 2)
      except RuntimeError:
        # scale constraints don't have an interp type
        pass

    return self.blend_constraints

  def make_switch_control(self):
      """Creates and orients an ik_fk switch control and locks and hides its keyable attributes.

      :return: None
      """

      self.switch_cc = control_curves.ik_switch_ctrl(name="{0}_leg_ikSwitch_cc".format(self.side), scale=module.SCALE_CONSTANT * 1)
      self.switch_cc_grp = cmds.group(self.switch_cc[0], name="{0}_grp".format(self.switch_cc[0]))
      cmds.delete(cmds.pointConstraint(self.joints[2], self.switch_cc_grp, mo=0))
      cmds.xform(self.switch_cc_grp, t=(0, 0, -1), r=1, ws=1)

      cmds.parent(self.switch_cc_grp, "layout_cc")

      # lock its attributes here
      for attr in cmds.listAttr(self.switch_cc[0], k=1):
          cmds.setAttr(self.switch_cc[0] + "." + attr, lock=1, keyable=0, channelBox=0)

  def setup_ik_switching(self):
      """Sets constraint blending using a reverse node. Also sets up visibility switching.

      :return: None
      """

      cmds.addAttr(self.switch_cc[0], longName="ikFk", defaultValue=0, min=0, max=1, attributeType="float", keyable=1)
      rev = cmds.createNode("reverse", name="{0}_leg_ikSwitch_rev".format(self.side))
      cmds.connectAttr("{0}.ikFk".format(self.switch_cc[0]), "{0}.ix".format(rev))

      for const in self.blend_constraints:
          if "pointConstraint" in const:
            weight_list = cmds.pointConstraint(const, query=1, weightAliasList=1)
            cmds.connectAttr("{0}.outputX".format(rev), "{0}.{1}".format(const, weight_list[0]))
            cmds.connectAttr("{0}.ikFk".format(self.switch_cc[0]), "{0}.{1}".format(const, weight_list[1]))

          elif "orientConstraint" in const:
            weight_list = cmds.orientConstraint(const, query=1, weightAliasList=1)
            cmds.connectAttr("{0}.outputX".format(rev), "{0}.{1}".format(const, weight_list[0]))
            cmds.connectAttr("{0}.ikFk".format(self.switch_cc[0]), "{0}.{1}".format(const, weight_list[1]))

      # do scaling with direct connections
      for i in range(3):
        scale_blend_colors = cmds.createNode("blendColors", name="{0}_scaleBlend".format(self.joints[i]))
        cmds.connectAttr("{0}.scale".format(self.ik_leg.joints[i]), "{0}.color1".format(scale_blend_colors))
        cmds.connectAttr("{0}.scale".format(self.fk_leg.joints[i]), "{0}.color2".format(scale_blend_colors))
        cmds.connectAttr("{0}.outputX".format(rev), "{0}.blender".format(scale_blend_colors))
        cmds.connectAttr("{0}.output".format(scale_blend_colors), "{0}.scale".format(self.joints[i]), force=1)


      # setup visibility switching
      # using "display geometry" as the vis switch makes it so vis switching won't affect child modules
      cmds.connectAttr(self.switch_cc[0] + ".ikFk", self.fk_leg.upLeg_cc[1] + ".v")
      cmds.connectAttr(self.switch_cc[0] + ".ikFk", self.fk_leg.loLeg_cc[1] + ".v")
      cmds.connectAttr(self.switch_cc[0] + ".ikFk", self.fk_leg.foot_cc[1] + ".v")
      cmds.connectAttr(rev + ".outputX", self.ik_leg.ik_cc[1] + ".v")
      cmds.connectAttr(rev + ".outputX", self.ik_leg.pv_cc[1] + ".v")


  def connect_to_module(self):
    cmds.addAttr(self.switch_cc[0], longName="ikSwitch", attributeType="message")
    cmds.addAttr(self.switch_cc[0], longName="module", attributeType="message")
    cmds.addAttr(self.switch_cc_grp, longName="module", attributeType="message")

    cmds.connectAttr("{0}.components".format(self.ikFkLeg_node), "{0}.module".format(self.switch_cc[0]))
    cmds.connectAttr("{0}.components".format(self.ikFkLeg_node), "{0}.module".format(self.switch_cc_grp))

    cmds.connectAttr("{0}.ikSwitch".format(self.ikFkLeg_node), "{0}.ikSwitch".format(self.switch_cc[0]))
