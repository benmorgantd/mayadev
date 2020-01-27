import Gossamer.library.control_curves as control_curves
import maya.cmds as cmds


class IkFoot():
  def __init__(self, foot=None, toe=None, toe_end=None, heel=None, bank_in=None, bank_out=None, side="LF", ik_foot=None, leg_ik_handle=None):
    self.foot = foot
    self.toe = toe
    self.toe_end = toe_end
    self.heel = heel
    self.bank_in = bank_in
    self.bank_out = bank_out
    self.side = side
    self.ik_foot = ik_foot
    self.ikfkswitch_grp = None
    
    self.leg_ik_handle = leg_ik_handle
    self.setup_joints = [self.toe, self.heel, self.bank_in, self.bank_out, self.toe_end, self.toe, self.foot]
    self.reverse_joints = []


  def make_ik_handles(self):
    self.toe_ik = cmds.ikHandle(startJoint=self.foot, endEffector=self.toe, solver="ikSCsolver", name="{0}_toe_scIK".format(self.side))
    self.toeEnd_ik = cmds.ikHandle(startJoint=self.toe, endEffector=self.toe_end, solver="ikSCsolver", name="{0}_toeEnd_scIK".format(self.side))
    return [self.toe_ik[0], self.toeEnd_ik[0]]

  def make_reverse_hierarchy(self):
    # order is ball_swivel, heel, bankIn, bankOut, toe_end, toe, foot

    reverse_hierarchy_names = ["rev_ball_swivel", "rev_heel", "rev_bankIn", "rev_bankOut", "rev_toe_end", "rev_toe", "rev_foot"]
    cmds.select(cl=1)

    ball_swivel = cmds.joint(name="{0}_ball_swivel".format(self.side))
    cmds.parent(ball_swivel, cmds.listRelatives(self.foot, parent=True)[0])
    cmds.delete(cmds.pointConstraint(self.toe, ball_swivel, maintainOffset=False))
    # for ball_swivel, project the toe location onto the xz plane 
    cmds.setAttr(ball_swivel + ".translateY", 0)
    # transfer rotation values to joint orientation
    cmds.makeIdentity(ball_swivel, apply=True, r=True, t=True, n=0, pn=1)
    self.reverse_joints.append(ball_swivel)

    for i in range(1, len(reverse_hierarchy_names)):
      jnt = cmds.joint(name="{0}_{1}".format(self.side, reverse_hierarchy_names[i]))
      cmds.delete(cmds.parentConstraint(self.setup_joints[i], jnt, maintainOffset=False))
      # transfer rotation values to joint orientation
      cmds.makeIdentity(jnt, apply=True, r=True, t=True, n=0, pn=1)
      self.reverse_joints.append(jnt)

    cmds.hide(ball_swivel)
    cmds.select(cl=1)

    # parent ik handles into the reverse hierarchy group
    cmds.parent(self.toe_ik[0], self.reverse_joints[-2])
    cmds.parent(self.toeEnd_ik[0], self.reverse_joints[-3])
    # and orient constrain the end of the reverse chain to the ik foot joint 
    # the other two will automatically follow because of their IK setup
    cmds.orientConstraint(self.reverse_joints[-1], self.foot, mo=1)
    # find the ik foot by looking at its connections via scale
    foot_ik_joint = cmds.listConnections(self.ik_foot + ".scale")[-1]
    # finally, delete the constraints on the ik_foot and instead orient constrain the rig_ik_foot to it
    cmds.delete(cmds.listRelatives(foot_ik_joint, type="orientConstraint"))
    cmds.orientConstraint(self.foot, foot_ik_joint, mo=1)
    cmds.pointConstraint(foot_ik_joint, self.foot, mo=1)
    # and finally, parent the reverse hierarchy under the ik control
    cmds.parent(self.reverse_joints[0], self.ik_foot)
    # we'll also need to delete the point constraint on the leg rpik handle and parent it to the "foot" in the reverse hierarchy
    cmds.parent(self.leg_ik_handle, self.reverse_joints[-1])
    
    for const in cmds.listRelatives(self.leg_ik_handle, type="constraint"):
      if "pointConstraint" in const:
        cmds.delete(const)

    return [self.reverse_joints[0]]

  def make_primary_attr(self):
    try:
      # add enum separator
      cmds.addAttr(self.ik_foot, ln="_", at="enum", k=1, enumName="_:")
      cmds.setAttr(self.ik_foot + "._", l=1)

      # toe_end roll
      cmds.addAttr(self.ik_foot, ln="toeRoll", at="float", k=1)
      cmds.connectAttr(self.ik_foot + ".toeRoll", self.reverse_joints[-3] + ".rz")

      # ball roll
      cmds.addAttr(self.ik_foot, ln="ballRoll", at="float", k=1)
      cmds.connectAttr(self.ik_foot + ".ballRoll", self.reverse_joints[-2] + ".rz")


      multiplier = 1
      if self.side in ["RT", "rt", "r", "R"]:
        multiplier = -1

      cmds.addAttr(self.ik_foot, ln="heelRoll", at="float", k=1)

      mdl_node = cmds.shadingNode("multDoubleLinear", name=self.ik_foot + "_heel_mdl", asUtility=True)
      cmds.connectAttr(self.ik_foot + ".heelRoll", mdl_node + ".input1")
      cmds.setAttr(mdl_node + ".input2", multiplier)

      # heel roll
      cmds.connectAttr(mdl_node + ".output", self.reverse_joints[1] + ".rx")

      # add enum separator
      cmds.addAttr(self.ik_foot, ln="__", at="enum", k=1, enumName="_:")
      cmds.setAttr(self.ik_foot + ".__", l=1)

      # toe_tip swivel
      cmds.addAttr(self.ik_foot, ln="toeSwivel", at="float", k=1)
      cmds.connectAttr(self.ik_foot + ".toeSwivel", self.reverse_joints[-3] + ".ry")

      # ball swivel
      cmds.addAttr(self.ik_foot, ln="ballSwivel", at="float", k=1)

      mdl_node = cmds.shadingNode("multDoubleLinear", name=self.ik_foot + "_ball_swivel_mdl", asUtility=True)
      cmds.connectAttr(self.ik_foot + ".ballSwivel", mdl_node + ".input1")
      cmds.setAttr(mdl_node + ".input2", multiplier)

      cmds.connectAttr(mdl_node + ".output", self.reverse_joints[0] + ".ry")

      # heel swivel
      cmds.addAttr(self.ik_foot, ln="heelSwivel", at="float", k=1)

      mdl_node = cmds.shadingNode("multDoubleLinear", name=self.ik_foot + "_heel_swivel_mdl", asUtility=True)
      cmds.connectAttr(self.ik_foot + ".heelSwivel", mdl_node + ".input1")
      cmds.setAttr(mdl_node + ".input2", multiplier)

      cmds.connectAttr(mdl_node + ".output", self.reverse_joints[1] + ".ry")

      # add enum separator
      cmds.addAttr(self.ik_foot, ln="___", at="enum", k=1, enumName="_:")
      cmds.setAttr(self.ik_foot + ".___", l=1)

      # toe bend
      cmds.addAttr(self.ik_foot, ln="toeBend", at="float", k=1)
      cmds.connectAttr(self.ik_foot + ".toeBend", self.toeEnd_ik[0] + ".ty")

      # ankle break
      cmds.addAttr(self.ik_foot, ln="ankleBreak", at="float", k=1)
      cmds.connectAttr(self.ik_foot + ".ankleBreak", self.reverse_joints[-2] + ".rx")

      # ankle twist
      cmds.addAttr(self.ik_foot, ln="ankleTwist", at="float", k=1)
      cmds.connectAttr(self.ik_foot + ".ankleTwist", self.reverse_joints[-2] + ".ry")


    except RuntimeError:
      pass

  def make_secondary_attr(self):

    multiplier = 1
    if self.side in ["RT", "rt", "r", "R"]:
      multiplier = -1

    # foot bank
    cmds.addAttr(self.ik_foot, longName="footBank", attributeType="float", defaultValue=0, keyable=True)

    mdl_node = cmds.shadingNode("multDoubleLinear", name=self.ik_foot + "_bank_mdl", asUtility=True)
    cmds.connectAttr(self.ik_foot + ".footBank", mdl_node + ".input1")
    cmds.setAttr(mdl_node + ".input2", multiplier)

    cond = cmds.createNode("condition", name=self.side + "_footBank_cond")
    cmds.setAttr(cond + ".operation", 2)
    cmds.setAttr(cond + ".secondTerm", 0)
    cmds.setAttr(cond + ".cfr", 0)
    cmds.setAttr(cond + ".ctg", 0)
    cmds.connectAttr(self.ik_foot + ".footBank", cond + ".firstTerm")
    cmds.connectAttr(mdl_node + ".output", cond + ".ctr")
    cmds.connectAttr(self.ik_foot + ".footBank", cond + ".cfg")
    # red is positive, green is negative. Make sure the bank locators are oriented accordingly
    cmds.connectAttr(cond + ".ocg", self.reverse_joints[2] + ".rx")
    cmds.connectAttr(cond + ".ocr", self.reverse_joints[3] + ".rx")

    """
    # foot peel
    cmds.addAttr(self.ik_foot, longName="footPeel", attributeType="float", defaultValue=0, min=0, keyable=True)
    cmds.addAttr(self.ik_foot, longName="footPeelBreak", attributeType="float", defaultValue=30, keyable=True)

    cond = cmds.createNode("condition", name=self.side + "_footPeel_cond")
    # while foot peel value is less than the break value...
    cmds.setAttr(cond + ".operation", 4)
    cmds.connectAttr(self.ik_foot + ".footPeel", cond + ".firstTerm")
    cmds.connectAttr(self.ik_foot + ".footPeelBreak", cond + ".secondTerm")
    # if true, its value is the foot peel value
    cmds.connectAttr(self.ik_foot + ".footPeel", cond + ".ctr")
    # while less than the green true value should be 0
    cmds.setAttr(cond + ".ctg", 0)
    # if the foot peel is greater than the break value than right  now it'd go back to 0. We need it to ease back down so the foot straightens
    cmds.setAttr(cond + ".cfr", 0)
    cmds.setAttr(cond + ".ctg", 0)
    # cmds.connectAttr(mdl_node + ".output", cond + ".ctr")
    
    # have to subtract the value of the footPeel value after it breaks (use an adl)
    # negate the value of footPeel
    foot_peel_break_negate = cmds.shadingNode("multDoubleLinear", name=self.ik_foot + "_footPeel_break_mdl", asUtility=True)
    cmds.connectAttr(cond + ".ocg", foot_peel_break_negate + ".input1")
    cmds.setAttr(foot_peel_break_negate + ".input2", -1)

    foot_peel_negate = cmds.shadingNode("addDoubleLinear", name=self.ik_foot + "_footPeel_negate_adl", asUtility=True)
    cmds.connectAttr(cond + ".ocg", foot_peel_negate + ".input1")
    cmds.connectAttr(foot_peel_break_negate + ".output", foot_peel_negate + ".input2")

    # make a group for the toe 
    toe_grp = cmds.group(self.reverse_joints[-2], name=self.side + "_footPeel_grp", relative=True)
    cmds.xform(toe_grp, pivots=cmds.xform(self.reverse_joints[-2], q=1, t=1, ws=1), ws=1)
    cmds.connectAttr(cond + ".ocr", toe_grp + ".rz")

    # make a group for the toe_end
    toe_end_grp = cmds.group(self.reverse_joints[-3], name=self.side + "_footPeel_end_grp", relative=True)
    cmds.xform(toe_end_grp, pivots=cmds.xform(self.reverse_joints[-3], q=1, t=1, ws=1), ws=1)
    cmds.connectAttr(foot_peel_negate + ".output", toe_end_grp + ".rz")
    """

  # def setup_ikfk_switch_grp(self):
  #   self.ikfkswitch_grp = cmds.group(empty=True, name=self.ik_foot + "_ikfk_switch_grp")
  #   cmds.delete(cmds.parentConstraint(self.toe, self.ikfkswitch_grp, mo=0))
  #   cmds.parent(self.ikfkswitch_grp, cmds.listRelatives(self.ik_foot, parent=True), absolute=True)
  #   offset_grp = cmds.group(self.ik_foot, name=self.ik_foot + "_ikfk_switch_offset")
  #   cmds.parent(offset_grp, self.ikfkswitch_grp, absolute=True)
  #   cmds.xform(self.ikfkswitch_grp, pivots=cmds.xform(self.toe, query=True, translation=True, worldSpace=True), worldSpace=True)

class FkFoot():
  def __init__(self, foot=None, toe=None, toe_end=None, side="LF", fk_foot=None):
    self.foot = foot
    self.toe = toe
    self.toe_end = toe_end
    self.side = side
    self.fk_foot = fk_foot

  def make_control_curves(self):
    self.toe_cc = control_curves.square_ctrl(name=self.side + "_toe_fk_cc")
    self.toe_cc_grp = cmds.group(self.toe_cc[0], n=self.toe_cc[0] + "_grp")
    
    cmds.setAttr(self.toe_cc[0] + ".rotateOrder", cmds.getAttr(self.toe + ".rotateOrder"))
    cmds.delete(cmds.parentConstraint(self.toe, self.toe_cc_grp, mo=0))
    cmds.parentConstraint(self.toe_cc[0], self.toe, mo=1)
    cmds.connectAttr(self.toe_cc[0] + ".scale", self.toe + ".scale")
    
    cmds.select(cl=1)
    cmds.setAttr(self.toe_cc[0] + ".v", lock=1, channelBox=0, keyable=0)

    cmds.parentConstraint(self.fk_foot, self.foot, mo=1)
    
    cmds.parent(self.toe_cc_grp, self.fk_foot)

    return self.toe_cc[0]

class DriveFoot():
  def __init__(self, ik_foot = None, fk_foot=None, drive_foot=None, switch_cc=None, switch_rev=None):
    self.ik_foot = ik_foot
    self.fk_foot = fk_foot
    self.drive_foot = drive_foot
    self.switch_cc = switch_cc
    self.switch_rev = switch_rev

    self.setup_blend()

  def setup_blend(self):
    for i in range(3):
      # setup constraint blending
      const = cmds.parentConstraint(self.ik_foot[i], self.fk_foot[i], self.drive_foot[i], mo=1)[0]
      cmds.setAttr(const + ".interpType", 2)
      weight_list = cmds.parentConstraint(const, query=1, weightAliasList=1)
      cmds.connectAttr("{0}.outputX".format(self.switch_rev), "{0}.{1}".format(const, weight_list[0]))
      cmds.connectAttr("{0}.ikFk".format(self.switch_cc), "{0}.{1}".format(const, weight_list[1]))

      # setup scale blending
      scale_blend_colors = cmds.createNode("blendColors", name="{0}_scaleBlend".format(self.drive_foot[i]))
      cmds.connectAttr("{0}.scale".format(self.ik_foot[i]), "{0}.color1".format(scale_blend_colors))
      cmds.connectAttr("{0}.scale".format(self.fk_foot[i]), "{0}.color2".format(scale_blend_colors))
      cmds.connectAttr("{0}.outputX".format(self.switch_rev), "{0}.blender".format(scale_blend_colors))
      cmds.connectAttr("{0}.output".format(scale_blend_colors), "{0}.scale".format(self.drive_foot[i]), force=1)

    # find the drive leg