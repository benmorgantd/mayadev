import Gossamer.creator
reload(Gossamer.creator)

import Gossamer.modules.character as character
import Gossamer.library.ctrl_cv_data as ctrl_cv_data

import time
import maya.OpenMaya as om
import maya.cmds as cmds


class Posession(Gossamer.creator.Creator):
  """Character creator class for the Posession rig. Requires joint inputs to satisfy module contracts.\n

  Args:
    char_name (str): This character's name.\n
  
  """

  def __init__(self, char_name="Posession"):
    super(Posession, self).__init__(char_name=char_name)

  def build_character(self):
    """References the "building blocks" inherited from the Creator class to create the rig for this specific character."""

    start_time = time.time()

    # CharNode and Root
    self.make_CharNode()
    self.make_Root()

    # COG and pelvis
    cmds.parent("cog", "layout")
    self.make_SingleJoint(joint="cog", module_name="Cog", side="c", control_shape="4-Sided Arrow")
    self.make_SingleJoint(joint="pelvis", module_name="Pelvis", side="c", control_shape="Cube")

    # Spine
    self.make_FkChain(joints=["spine1", "spine2", "chest"], module_name="Spine", side="c")

    # Neck and Head
    self.make_SingleJoint(joint="neck", module_name="Neck", side="c", control_shape="Cylinder")
    self.make_SingleJoint(joint="head", module_name="Head", side="c", control_shape="Cube")

    # Clavicles
    self.make_SingleJoint(joint="LF_clavicle", module_name="LF_clavicle", side="LF", control_shape="Circle")
    self.make_SingleJoint(joint="RT_clavicle", module_name="RT_clavicle", side="RT", control_shape="Circle")

    # Legs
    LF_leg = self.make_IkFkLeg(joints=["LF_upLeg", "LF_loLeg", "LF_foot"], module_name="LF_Leg", side="LF")
    RT_leg = self.make_IkFkLeg(joints=["RT_upLeg", "RT_loLeg", "RT_foot"], module_name="RT_Leg", side="RT")

    # Arms
    LF_arm = self.make_IkFkArm(joints=["LF_upArm", "LF_loArm", "LF_wrist"], module_name="LF_Arm", side="LF")
    RT_arm = self.make_IkFkArm(joints=["RT_upArm", "RT_loArm", "RT_wrist"], module_name="RT_Arm", side="RT")

    # Feet
    self.make_Foot(joints=["LF_foot", "LF_toe", "LF_toeTip"], locs=["LF_heel", "LF_bankIn_loc", "LF_bankOut_loc"], module_name="LF_Foot", side="LF")
    self.make_Foot(joints=["RT_foot", "RT_toe", "RT_toeTip"], locs=["RT_heel", "RT_bankIn_loc", "RT_bankOut_loc"], module_name="RT_Foot", side="RT")

    # (Fix for foot module fk visibility switching)
    cmds.connectAttr("LF_leg_ikSwitch_cc.ikFk", "LF_toe_fk_ccShape.v")
    cmds.connectAttr("RT_leg_ikSwitch_cc.ikFk", "RT_toe_fk_ccShape.v")

    # heel and toe tip adjustment controls
    self.make_SingleJoint(joint="LF_heel", module_name="LF_heel", side="LF", control_shape="Circle", child_of="pelvis_cc", constrained_to="LF_foot_rig_drive")
    self.make_SingleJoint(joint="RT_heel", module_name="RT_heel", side="RT", control_shape="Circle", child_of="pelvis_cc", constrained_to="RT_foot_rig_drive")

    self.make_SingleJoint(joint="LF_toeTip", module_name="LF_toeTip", side="LF", control_shape="Circle", child_of="pelvis_cc", constrained_to="LF_toe_rig_drive")
    self.make_SingleJoint(joint="RT_toeTip", module_name="RT_toeTip", side="RT", control_shape="Circle", child_of="pelvis_cc", constrained_to="RT_toe_rig_drive")

    # Twist extraction via Quat and scIK extraction depending on where it works better.
    self.make_QuatTwist(module_name="LF_loArm_twist", side="LF", extract_joint="LF_wrist_drive", 
                        twist_joints=["LF_loArmTwist_01", "LF_loArmTwist_02"], 
                        limb_module=LF_arm.node)

    self.make_QuatTwist(module_name="RT_loArm_twist", side="RT", extract_joint="RT_wrist_drive",
                        twist_joints=["RT_loArmTwist_01", "RT_loArmTwist_02"],
                        limb_module=RT_arm.node)
    
    self.make_QuatTwist(module_name="LF_loLeg_twist", side="LF", extract_joint="LF_foot_drive", twist_joints=["LF_loLegTwist_01", "LF_loLegTwist_02", "LF_loLegTwist_03"], axis="Y", multiplier=-1)
    self.make_QuatTwist(module_name="RT_loLeg_twist", side="RT", extract_joint="RT_foot_drive", twist_joints=["RT_loLegTwist_01", "RT_loLegTwist_02", "RT_loLegTwist_03"], axis="Y")

    self.make_QuatTwist(module_name="Neck_twist", side="c", extract_joint="head", twist_joints=["neckTwist_01"], multiplier=.5)
    
    self.make_IkTwist(module_name="LF_upLeg_twist", side="LF", extract_joint="LF_upLeg_drive", start_joint="LF_loLeg_drive", twist_joints=["LF_upLegTwist_01", "LF_upLegTwist_02", "LF_upLegTwist_03"], ik_parent="pelvis")
    self.make_IkTwist(module_name="RT_upLeg_twist", side="RT", extract_joint="RT_upLeg_drive",  start_joint="RT_loLeg_drive",twist_joints=["RT_upLegTwist_01", "RT_upLegTwist_02", "RT_upLegTwist_03"], ik_parent="pelvis")

    self.make_IkTwist(module_name="LF_upArm_twist", side="LF", extract_joint="LF_upArm_drive", start_joint="LF_loArm_drive", twist_joints=["LF_upArmTwist_01", "LF_upArmTwist_02", "LF_upArmTwist_03"], ik_parent="LF_clavicle")
    self.make_IkTwist(module_name="RT_upArm_twist", side="RT", extract_joint="RT_upArm_drive", start_joint="RT_loArm_drive", twist_joints=["RT_upArmTwist_01", "RT_upArmTwist_02", "RT_upArmTwist_03"], ik_parent="RT_clavicle")

    # Fingers
    self.make_FkChain(module_name="LF_index", side="LF", joints=["LF_index1","LF_index2","LF_index3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_mid", side="LF", joints=["LF_mid1","LF_mid2","LF_mid3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_ring", side="LF", joints=["LF_ring1","LF_ring2","LF_ring3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_pinkie", side="LF", joints=["LF_pinkie1","LF_pinkie2","LF_pinkie3","LF_pinkie4"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")
    self.make_FkChain(module_name="LF_thumb", side="LF", joints=["LF_thumb1","LF_thumb2","LF_thumb3"], control_shape="Sphere", child_of="LF_clavicle_cc", constrained_to="LF_wrist_drive")

    self.make_FkChain(module_name="RT_index", side="RT", joints=["RT_index1","RT_index2","RT_index3"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_mid", side="RT", joints=["RT_mid1","RT_mid2","RT_mid3",], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_ring", side="RT", joints=["RT_ring1","RT_ring2","RT_ring3"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_pinkie", side="RT", joints=["RT_pinkie1","RT_pinkie2","RT_pinkie3","RT_pinkie4"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")
    self.make_FkChain(module_name="RT_thumb", side="RT", joints=["RT_thumb1","RT_thumb2","RT_thumb3"], control_shape="Sphere", child_of="RT_clavicle_cc", constrained_to="RT_wrist_drive")

    # face
    self.make_SingleJoint(module_name = "Nose", side="c", joint="nose", control_shape="Cube")
    self.make_SingleJoint(module_name = "LF_nostril", side="LF", joint="LF_nostril", control_shape="Cube")
    self.make_SingleJoint(module_name = "RT_nostril", side="RT", joint="RT_nostril", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_mouthOut", joint="LF_mouthOut", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_mouthOut", joint="RT_mouthOut", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="mouthMid", joint="mouthMid", side="c", control_shape="Cube")
    self.make_SingleJoint(module_name="chin", joint="chin", side="c", control_shape="Cube")

    self.make_SingleJoint(module_name="LF_loCheek", joint="LF_loCheek", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_cheekOut", joint="LF_cheekOut", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_cheekIn", joint="LF_cheekIn", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_eye", joint="LF_eye", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_loLid", joint="LF_loLid", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_upLid", joint="LF_upLid", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_browIn", joint="LF_browIn", side="LF", control_shape="Cube")
    self.make_SingleJoint(module_name="LF_browOut", joint="LF_browOut", side="LF", control_shape="Cube")

    self.make_SingleJoint(module_name="RT_loCheek", joint="RT_loCheek", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_cheekOut", joint="RT_cheekOut", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_cheekIn", joint="RT_cheekIn", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_eye", joint="RT_eye", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_loLid", joint="RT_loLid", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_upLid", joint="RT_upLid", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_browIn", joint="RT_browIn", side="RT", control_shape="Cube")
    self.make_SingleJoint(module_name="RT_browOut", joint="RT_browOut", side="RT", control_shape="Cube")


    character.Character.connect_bind_joints("{0}_CharNode".format(self.char_name))
    ctrl_cv_data.set_cv_data(self.char_name)
    character.Character.add_pose("{0}_CharNode".format(self.char_name), "default")

    cmds.parent("geometry", "root", "Posession_grp")
    cmds.parent("exclude", "rig")


    cmds.createDisplayLayer("geometry", name="geo")
    cmds.setAttr("geo.displayType", 2)

    cmds.hide("doNotTouch")
    cmds.hide("exclude")
    cmds.group("root", name="skeleton")
    cmds.hide("skeleton")
    cmds.hide(cmds.ls(type="ikHandle"))

    cmds.createDisplayLayer("rig", name="ctrl", noRecurse=True)

    # lock scale for now
    for obj in cmds.ls("*_cc"):
      cmds.setAttr(obj + ".sx", l=1, cb=0, k=0)
      cmds.setAttr(obj + ".sy", l=1, cb=0, k=0)
      cmds.setAttr(obj + ".sz", l=1, cb=0, k=0)

    cmds.select(cl=1)

    om.MGlobal.displayInfo(self.char_name + " rigged in %.3f seconds! :D"%(time.time() - start_time))

