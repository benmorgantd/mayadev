import maya.cmds as cmds
import maya.OpenMaya as om
import Gossamer.library.control_curves as control_curves
import Gossamer.modules.module as module

class FkArm():
  def __init__(self, joints=None, ikFkArm_node=None):
    """Creates a 3 joint fk arm chain.

    :param setup_joint: The root of an oriented 3 joint chain that will become our arm joints.
    :param side: A location identifier.
    :param char_name: Character name identifier
    :param module_name: The overall name for the arm.
    :type setup_joint: str
    :type side:  str
    :type char_name: str
    :type module_name: str
    """

    if len(joints) != 3:
      raise ValueError("Must be passed a 3 joint chain: [upArm, loArm, wrist]")

    self.joints = joints

    self.ikFkArm_node = ikFkArm_node

    if not self.ikFkArm_node:
      return

    self.name = cmds.getAttr("{0}.name".format(self.ikFkArm_node))
    self.side = cmds.getAttr("{0}.side".format(self.ikFkArm_node))

    self.upArm_cc = None
    self.loArm_cc = None
    self.wrist_cc = None
    self.upArm_cc_grp = None
    self.loArm_cc_grp = None
    self.wrist_cc_grp = None
    self.controls = []

    # main
    self.make_control_curves()
    self.set_cc_rot_orders()
    self.set_control_constraints()
    # self.make_gimbal_swing()
    self.lock_control_curve_attr()
    self.connect_to_module()

  def make_control_curves(self):
    """Makes and positions the fk control curves.

    :return: None
    """

    # up arm
    self.upArm_cc = control_curves.hex_cylinder_ctrl(name="{0}_cc".format(self.joints[0]), scale=module.SCALE_CONSTANT * .75)
    self.upArm_cc_grp = cmds.group(self.upArm_cc[0], name="{0}_grp".format(self.upArm_cc[0]), relative=1)
    cmds.xform(self.upArm_cc_grp, pivots=cmds.xform(self.upArm_cc[0], q=1, t=1))
    cmds.delete(cmds.parentConstraint(self.joints[0], self.upArm_cc_grp, mo=0))
    cmds.addAttr(self.upArm_cc[0], longName="upArmFk", attributeType="message")

    # lower arm
    self.loArm_cc = control_curves.hex_cylinder_ctrl(name="{0}_cc".format(self.joints[1]), scale=module.SCALE_CONSTANT * .75)
    self.loArm_cc_grp = cmds.group(self.loArm_cc[0], name="{0}_grp".format(self.loArm_cc[0]), relative=1)
    cmds.xform(self.loArm_cc_grp, pivots=cmds.xform(self.loArm_cc[0], q=1, t=1))
    cmds.delete(cmds.parentConstraint(self.joints[1], self.loArm_cc_grp, mo=0))
    cmds.addAttr(self.loArm_cc[0], longName="loArmFk", attributeType="message")

    # wrist
    self.wrist_cc = control_curves.hex_cylinder_ctrl(name="{0}_cc".format(self.joints[2]), scale=module.SCALE_CONSTANT * .5)
    self.wrist_cc_grp = cmds.group(self.wrist_cc[0], name="{0}_grp".format(self.wrist_cc[0]), relative=1)
    cmds.xform(self.wrist_cc_grp, pivots=cmds.xform(self.wrist_cc[0], q=1, t=1))
    cmds.delete(cmds.parentConstraint(self.joints[2], self.wrist_cc_grp, mo=0))
    cmds.addAttr(self.wrist_cc[0], longName="wristFk", attributeType="message")

    # setup hierarchy
    cmds.parent(self.wrist_cc_grp, self.loArm_cc[0])
    cmds.parent(self.loArm_cc_grp, self.upArm_cc[0])

    self.controls = [self.upArm_cc, self.loArm_cc, self.wrist_cc]

  def set_cc_rot_orders(self):
    """Set the rotation orders for the fk controls.

    :return: None
    """

    for i in range(0,3):
      cmds.setAttr("{0}.rotateOrder".format(self.controls[i][0]), cmds.getAttr("{0}.rotateOrder".format(self.joints[i])))

  def set_control_constraints(self):
    """Setup the parent and orient constraints for our control curves.

    :return: None
    """

    for i in range(0,3):
      cmds.pointConstraint(self.controls[i][0], self.joints[i], mo=1)
      cmds.orientConstraint(self.controls[i][0], self.joints[i], mo=1)
      cmds.scaleConstraint(self.controls[i][0], self.joints[i], mo=1)


  def make_gimbal_swing(self):
    """Create a top level group above our upArm_cc_grp that will allow us to swing the control in world X.
    Helps with gimbal issues on the upArm.

    :return: None
    """

    # group the upArm_cc_grp to give us a top level control to avoid gimbal lock
    self.gimbal_grp = cmds.group(self.upArm_cc_grp, n=self.full_name() + "_gimbal_grp", r=1)
    cmds.xform(self.gimbal_grp + ".rotatePivot", t=cmds.xform(self.joints[0], q=1, t=1, ws=1), ws=1)
    cmds.addAttr(self.upArm_cc[0], at="float", ln="Gimbal_Swing", k=1)
    cmds.connectAttr(self.upArm_cc[0] + ".Gimbal_Swing", self.gimbal_grp + ".rx")
    # create a new higher level group so we can parent constraint the gimbal control to the shoulder later on
    self.upArm_top_level_grp = cmds.group(self.gimbal_grp, n=self.full_name() + "_upArmTopLvl_grp", r=1)

  def lock_control_curve_attr(self):
    """Lock and hide certain attributes on our controls.

    :return: None
    """

    for ctrl in [self.upArm_cc, self.loArm_cc, self.wrist_cc]:
      cmds.setAttr(ctrl[0] + ".v", lock=1, channelBox=0, keyable=0)


  def connect_to_module(self):
    for comp in [self.upArm_cc[0], self.upArm_cc_grp, self.loArm_cc[0], self.loArm_cc_grp, self.wrist_cc[0], self.wrist_cc_grp]:
      cmds.addAttr(comp, longName="module", attributeType="message")
      cmds.connectAttr("{0}.components".format(self.ikFkArm_node), "{0}.module".format(comp))

    cmds.connectAttr("{0}.upArmFk".format(self.ikFkArm_node), "{0}.upArmFk".format(self.controls[0][0]))
    cmds.connectAttr("{0}.loArmFk".format(self.ikFkArm_node), "{0}.loArmFk".format(self.controls[1][0]))
    cmds.connectAttr("{0}.wristFk".format(self.ikFkArm_node), "{0}.wristFk".format(self.controls[2][0]))