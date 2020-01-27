import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Tortoise(Gossamer.creator.Creator):
  """Character creator class for the Tortoise rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Tortoise"):
    super(Tortoise, self).__init__(char_name=char_name)
    
  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("cog", "staff", "layout")
    self.make_SingleJoint(joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow")
    self.make_SingleJoint(joint="pelvis", module_name="Pelvis", side="c", control_shape="Cube")
    self.make_SingleJoint(joint="tail", module_name="Tail", side="c", control_shape="Cylinder")

    # Spine
    self.make_FkChain(joints=["spine1", "chest"], module_name="Spine", side="c")

    # Neck and Head
    self.make_SingleJoint(joint="neck", module_name="Neck", side="c", control_shape="Cylinder")
    self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Sphere")
    self.make_SingleJoint(joint="LF_eye", module_name="LF_eye", side="LF", control_shape="Sphere")
    self.make_SingleJoint(joint="RT_eye", module_name="RT_eye", side="RT", control_shape="Sphere")

    # Clavicles
    self.make_SingleJoint(joint="LF_clavicle", module_name="LF_clavicle", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_clavicle", module_name="RT_clavicle", side="RT", control_shape="Circle")

    # Legs
    self.make_IkFkLeg(joints=["LF_upLeg", "LF_loLeg", "LF_foot"], module_name="LF_Leg", side="LF")
    self.make_IkFkLeg(joints=["RT_upLeg", "RT_loLeg", "RT_foot"], module_name="RT_Leg", side="RT")

    # Arms
    self.make_IkFkArm(joints=["LF_upArm", "LF_loArm", "LF_wrist"], module_name="LF_Arm", side="LF")
    self.make_IkFkArm(joints=["RT_upArm", "RT_loArm", "RT_wrist"], module_name="RT_Arm", side="RT")

    # Feet
    self.make_Foot(joints=["LF_foot", "LF_toe", "LF_toeTip"], locs=["LF_heel", "LF_bankIn_loc", "LF_bankOut_loc"], module_name="LF_Foot", side="LF")
    self.make_Foot(joints=["RT_foot", "RT_toe", "RT_toeTip"], locs=["RT_heel", "RT_bankIn_loc", "RT_bankOut_loc"], module_name="RT_Foot", side="RT")

    # (Fix for foot module fk visibility switching)
    cmds.connectAttr("LF_leg_ikSwitch_cc.ikFk", "LF_toe_fk_ccShape.v")
    cmds.connectAttr("LF_leg_ikSwitch_cc.ikFk", "RT_toe_fk_ccShape.v")

    # heel and toe tip adjustment controls
    self.make_SingleJoint(joint="LF_heel", module_name="LF_heel", side="LF", control_shape="Circle", child_of="pelvis_cc", constrained_to="LF_foot_rig_drive")
    self.make_SingleJoint(joint="RT_heel", module_name="RT_heel", side="RT", control_shape="Circle", child_of="pelvis_cc", constrained_to="RT_foot_rig_drive")

    self.make_SingleJoint(joint="LF_toeTip", module_name="LF_toeTip", side="LF", control_shape="Circle", child_of="pelvis_cc", constrained_to="LF_toe_rig_drive")
    self.make_SingleJoint(joint="RT_toeTip", module_name="RT_toeTip", side="RT", control_shape="Circle", child_of="pelvis_cc", constrained_to="RT_toe_rig_drive")
    
    # props
    staff = self.make_SingleJoint(joint="staff", module_name="Staff", side=None, control_shape="Cylinder", child_of="layout_cc", constrained_to="layout_cc")
    staff.setup_multi_follow(control="staff_cc", targets=["shell", "RT_wrist", "LF_wrist"], default_value=3, module=staff.node)

    self.make_SingleJoint(joint="shell", module_name="Shell", side=None, control_shape="Circle")
    self.make_SingleJoint(joint="armor", module_name="Armor", side=None, control_shape="Circle")
    self.make_SingleJoint(joint="jaw", module_name="Jaw", side="c", control_shape="Cylinder")

    
    # Twist extraction via Quat and scIK extraction depending on where it works better.
    self.make_QuatTwist(module_name="LF_loArm_twist", side="LF", extract_joint="LF_wrist_drive", twist_joints=["LF_loArmTwist_01"], multiplier=.5)
    self.make_QuatTwist(module_name="RT_loArm_twist", side="RT", extract_joint="RT_wrist_drive", twist_joints=["RT_loArmTwist_01"], multiplier=.5)
    
    self.make_QuatTwist(module_name="LF_loLeg_twist", side="LF", extract_joint="LF_foot_drive", twist_joints=["LF_loLegTwist_01"], axis="Y", multiplier=-.5)
    self.make_QuatTwist(module_name="RT_loLeg_twist", side="RT", extract_joint="RT_foot_drive", twist_joints=["RT_loLegTwist_01"], axis="Y", multiplier=.5)

    self.make_QuatTwist(module_name="Neck_twist", side="c", extract_joint="head", twist_joints=["neckTwist_01"], multiplier=.5)
    
    self.make_IkTwist(module_name="LF_upLeg_twist", side="LF", extract_joint="LF_upLeg_drive", start_joint="LF_loLeg_drive", twist_joints=["LF_upLegTwist_01"], ik_parent="pelvis")
    self.make_IkTwist(module_name="RT_upLeg_twist", side="RT", extract_joint="RT_upLeg_drive",  start_joint="RT_loLeg_drive",twist_joints=["RT_upLegTwist_01"], ik_parent="pelvis")

    self.make_IkTwist(module_name="LF_upArm_twist", side="LF", extract_joint="LF_upArm_drive", start_joint="LF_loArm_drive", twist_joints=["LF_upArmTwist_01"], ik_parent="LF_clavicle")
    self.make_IkTwist(module_name="RT_upArm_twist", side="RT", extract_joint="RT_upArm_drive", start_joint="RT_loArm_drive", twist_joints=["RT_upArmTwist_01"], ik_parent="RT_clavicle")
    
    # Fingers
    self.make_Finger(module_name="LF_index", side="LF", joints=["LF_index_1","LF_index_2","LF_index_3","LF_index_4"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_Finger(module_name="LF_mid", side="LF", joints=["LF_mid_1","LF_mid_2","LF_mid_3","LF_mid_4"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_Finger(module_name="LF_thumb", side="LF", joints=["LF_thumb_1","LF_thumb_2","LF_thumb_3"], child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")

    self.make_Finger(module_name="RT_index", side="RT", joints=["RT_index_1","RT_index_2","RT_index_3","RT_index_4"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_Finger(module_name="RT_mid", side="RT", joints=["RT_mid_1","RT_mid_2","RT_mid_3","RT_mid_4"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_Finger(module_name="RT_thumb", side="RT", joints=["RT_thumb_1","RT_thumb_2","RT_thumb_3"], child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")

    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Tortoise_grp")
    cmds.parent("exclude", "rig")

    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.hide("exclude")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("root_cc_grp", name="ctrl")

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      cmds.setAttr(obj + ".sx", l=1)
      cmds.setAttr(obj + ".sy", l=1)
      cmds.setAttr(obj + ".sz", l=1)

    cmds.select(cl=1)

    om.MGlobal.displayInfo("Character rigged in %.3f seconds! :D"%(time.time() - start_time))

