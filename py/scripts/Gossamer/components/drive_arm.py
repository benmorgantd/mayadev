import maya.cmds as cmds
import maya.OpenMaya as om
import Gossamer.library.control_curves as control_curves
import Gossamer.modules.module as module


class DriveArm():
  def __init__(self, joints=None, ikFkArm_node=None, ik_arm=None, fk_arm=None):
    """Creates a 3 joint ik/fk blended arm chain.

    :param ik_arm: An IkArm object used for blending.
    :param fk_arm: An FkArm object used for blending.
    :type ik_arm: IkArm
    :type fk_arm: FkArm
    """

    self.ik_arm = ik_arm
    self.fk_arm = fk_arm
    self.upArm_twist_ik = None
    self.ikFkArm_node = ikFkArm_node
    self.joints = joints
    self.ikFkArm_node = ikFkArm_node
    self.side = cmds.getAttr("{0}.side".format(self.ikFkArm_node))

    if len(self.joints) != 3:
      raise ValueError("Must be passed a 3 joint chain: [upArm, loArm, wrist]")

    self.pc_upArms = None
    self.oc_loArms = None
    self.oc_wrists = None
    self.sc_wrists = None
    self.switch_cc = None
    self.switch_cc_grp = None
    self.shoulder_cc = None
    self.shoulder_cc_grp = None
    self.loArm_bend_joint = None
    self.upArm_bend_joint = None
    self.blend_constraints = []
    self.wrist_bend_joint_upper = None
    self.wrist_bend_joint_lower = None
    self.upArm_ribbon = None
    self.forearm_ribbon = None
    self.upArm_inv_md = None

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

    for i in range(0,3):

      # delete any existing constraints on the drive joints
      cmds.delete(self.joints[i], constraints=1)

      self.blend_constraints.append(cmds.pointConstraint(self.ik_arm.joints[i], self.fk_arm.joints[i], self.joints[i], mo=1)[0])
      self.blend_constraints.append(cmds.orientConstraint(self.ik_arm.joints[i], self.fk_arm.joints[i], self.joints[i], mo=1)[0])

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

      self.switch_cc = control_curves.ik_switch_ctrl(name="{0}_arm_ikSwitch_cc".format(self.side), scale=module.SCALE_CONSTANT * 1)
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

      cmds.addAttr(self.switch_cc[0], longName="ikFk", defaultValue=1, min=0, max=1, attributeType="float", keyable=1)
      rev = cmds.createNode("reverse", name="{0}_arm_ikSwitch_rev".format(self.side))
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
      for i in range(0, 3):
        scale_blend_colors = cmds.createNode("blendColors", name="{0}_scaleBlend".format(self.joints[i]))
        cmds.connectAttr("{0}.scale".format(self.ik_arm.joints[i]), "{0}.color1".format(scale_blend_colors))
        cmds.connectAttr("{0}.scale".format(self.fk_arm.joints[i]), "{0}.color2".format(scale_blend_colors))
        cmds.connectAttr("{0}.outputX".format(rev), "{0}.blender".format(scale_blend_colors))
        cmds.connectAttr("{0}.output".format(scale_blend_colors), "{0}.scale".format(self.joints[i]), force=1)

      # setup visibility switching
      # using "display geometry" as the vis switch makes it so vis switching won't affect child modules
      cmds.connectAttr(self.switch_cc[0] + ".ikFk", self.fk_arm.upArm_cc[1] + ".v")
      cmds.connectAttr(self.switch_cc[0] + ".ikFk", self.fk_arm.loArm_cc[1] + ".v")
      cmds.connectAttr(self.switch_cc[0] + ".ikFk", self.fk_arm.wrist_cc[1] + ".v")
      cmds.connectAttr(rev + ".outputX", self.ik_arm.ik_cc[1] + ".v")
      cmds.connectAttr(rev + ".outputX", self.ik_arm.pv_cc[1] + ".v")

  def connect_to_module(self):
    cmds.addAttr(self.switch_cc[0], longName="ikSwitch", attributeType="message")
    cmds.addAttr(self.switch_cc[0], longName="module", attributeType="message")
    cmds.addAttr(self.switch_cc_grp, longName="module", attributeType="message")

    cmds.connectAttr("{0}.components".format(self.ikFkArm_node), "{0}.module".format(self.switch_cc[0]))
    cmds.connectAttr("{0}.components".format(self.ikFkArm_node), "{0}.module".format(self.switch_cc_grp))

    cmds.connectAttr("{0}.ikSwitch".format(self.ikFkArm_node), "{0}.ikSwitch".format(self.switch_cc[0]))